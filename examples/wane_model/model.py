import os, sys
import pickle
import datetime
from tqdm import tqdm
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

# import veame
from veame import *

logging.basicConfig(level=logging.INFO)

# set level
tool_log.setLevel(logging.WARNING)
sim_log.setLevel(logging.WARNING)
smpl_log.setLevel(logging.WARNING)


def wrap_func(sm_name, tag_name, hpm_func):
    return lambda current_time, parameter, sm_name=sm_name, tag_name=tag_name: hpm_func(
        sm_name, tag_name, current_time, parameter
    )


def make_statemachine_VAC(ves, hpm):
    # StateMachine
    sm = StateMachine("sm_vac")
    trg1a = sm.add_transition("start", "select_no_vac", "select_no_vac")
    trg1b = sm.add_transition("start", "select_1_vac", "select_1_vac")
    trg1c = sm.add_transition("start", "select_2_vac", "select_2_vac")
    trg2 = Trigger("init_vac_end")
    sm.add_transition("select_no_vac", "init_vac_end", trg2)
    sm.add_transition("select_1_vac", "init_vac_end", trg2)
    sm.add_transition("select_2_vac", "init_vac_end", trg2)
    trg3a = sm.add_transition("init_vac_end", "get_vac1", "vac1")
    trg3b = sm.add_transition("init_vac_end", "vac0_out", "vac0_out")
    trg4a = sm.add_transition("get_vac1", "get_vac2", "vac2")
    trg4b = sm.add_transition("get_vac1", "vac1_out", "vac1_out")

    # RandomEvent
    ev_dose_selection = RandomEvent("vac_selection", None, sm("start"))
    ev_dose_selection.set_name_and_probability_func(
        wrap_func(sm.name, ev_dose_selection.name, hpm.branch_prob)
    )
    ev_dose_selection_no_vac = ev_dose_selection.event("select_no_vac")
    ev_dose_selection_1_vac = ev_dose_selection.event("select_1_vac")
    ev_dose_selection_2_vac = ev_dose_selection.event("select_2_vac")
    trg1a.set_event(ev_dose_selection_no_vac)
    trg1b.set_event(ev_dose_selection_1_vac)
    trg1c.set_event(ev_dose_selection_2_vac)

    # DummyEvent
    ev_dummy = DummyEvent("init_vac_end")
    trg2.set_event(ev_dummy)

    # TimerEvent
    ev_vac1 = TimerEvent(
        "vac1",
        start_state_or_event=sm("init_vac_end"),
    )
    ev_vac1.set_interval(wrap_func(sm.name, ev_vac1.name, hpm.timer_interval))
    ev_vac2 = TimerEvent(
        "vac2",
        start_state_or_event=sm("get_vac1"),
    )
    ev_vac2.set_interval(wrap_func(sm.name, ev_vac2.name, hpm.timer_interval))

    sm("select_no_vac").set_update_parameter_func(
        wrap_func(sm.name, "select_no_vac", hpm.set_parameter)
    )
    sm("select_1_vac").set_update_parameter_func(
        wrap_func(sm.name, "select_1_vac", hpm.set_parameter)
    )
    sm("select_2_vac").set_update_parameter_func(
        wrap_func(sm.name, "select_2_vac", hpm.set_parameter)
    )

    ev_vac0_out = ParameterEvent("vac0_out", ("select_vac", 0))
    ev_vac1_out = ParameterEvent("vac1_out", ("select_vac", 1))
    ves["ev_get_vac1"] = StateEvent("get_vac1", sm("get_vac1"))
    ves["ev_get_vac2"] = StateEvent("get_vac2", sm("get_vac2"))

    trg3a.set_event(ev_vac1)
    trg3b.set_event(ves["ev_infect_c19"] | ev_vac0_out)
    trg4a.set_event(ev_vac2)
    trg4b.set_event(ves["ev_infect_c19"] | ev_vac1_out)

    return sm


def make_statemachine_infect(ves, hpm):
    # StateMachine
    sm = StateMachine("sm_infect")
    trg1 = sm.add_transition("start", "infect_c19", "infect_c19")
    trg2 = sm.add_transition("infect_c19", "PCR_positive", "PCR_positive")

    # StochasticEvent
    ves["ev_infect_c19"] = StochasticEvent(
        "infect_c19",
        start_state_or_event=sm("start"),
        probability_func=lambda current_time, parameter: parameter[
            "infection_immune_adjust_c19"
        ]
        * parameter["infection_ratio_c19"]
        * parameter["infection_base_rate_c19"],
    )
    ev_dummy = DummyEvent("PCR_positive", event_raise=True)
    trg1.set_event(ves["ev_infect_c19"])
    trg2.set_event(ev_dummy)
    return sm


def make_statemachine_vacNeff(prefix, ves, hpm):
    # StateMachine
    sm = StateMachine("sm_{}_eff".format(prefix))

    trg1 = sm.add_transition("start", "{}_branch".format(prefix), prefix)
    trg2a = sm.add_transition(
        "{}_branch".format(prefix),
        "{}_no_adv_no_eff_path".format(prefix),
        "{}_no_adv_no_eff_path".format(prefix),
    )
    trg2b = sm.add_transition(
        "{}_branch".format(prefix),
        "{}_no_adv_eff_path".format(prefix),
        "{}_no_adv_eff_path".format(prefix),
    )
    trg2c = sm.add_transition(
        "{}_branch".format(prefix),
        "{}_adv_no_eff_path".format(prefix),
        "{}_adv_no_eff_path".format(prefix),
    )
    trg2d = sm.add_transition(
        "{}_branch".format(prefix),
        "{}_adv_eff_path".format(prefix),
        "{}_adv_eff_path".format(prefix),
    )
    trg3b = sm.add_transition(
        "{}_no_adv_eff_path".format(prefix),
        "{}_eff".format(prefix),
        "{}_eff".format(prefix),
    )
    trg3c = sm.add_transition(
        "{}_adv_no_eff_path".format(prefix),
        "{}_adv_end".format(prefix),
        "{}_adv_end".format(prefix),
    )
    trg3d = sm.add_transition(
        "{}_adv_eff_path".format(prefix),
        "{}_adv_end_and_eff".format(prefix),
        "{}_adv_end_and_eff".format(prefix),
    )

    # RandomEvent
    ev_vacN_eff_branch = RandomEvent(
        "{}_branch".format(prefix), None, sm("{}_branch".format(prefix))
    )
    ev_vacN_eff_branch.set_name_and_probability_func(
        wrap_func(sm.name, ev_vacN_eff_branch.name, hpm.branch_prob)
    )
    ev_no_adv_no_eff = ev_vacN_eff_branch.event("{}_no_adv_no_eff_path".format(prefix))
    ev_no_adv_eff = ev_vacN_eff_branch.event("{}_no_adv_eff_path".format(prefix))
    ev_adv_no_eff = ev_vacN_eff_branch.event("{}_adv_no_eff_path".format(prefix))
    ev_adv_eff = ev_vacN_eff_branch.event("{}_adv_eff_path".format(prefix))

    # TimerEvent
    ev_eff = TimerEvent(
        "{}_eff".format(prefix),
        start_state_or_event=sm("{}_no_adv_eff_path".format(prefix)),
    )
    ev_eff.set_interval(wrap_func(sm.name, ev_eff.name, hpm.timer_interval))
    ev_adv_end = TimerEvent(
        "{}_adv_end".format(prefix),
        start_state_or_event=sm("{}_adv_no_eff_path".format(prefix)),
    )
    ev_adv_end.set_interval(wrap_func(sm.name, ev_adv_end.name, hpm.timer_interval))
    ev_adv_end_and_eff = TimerEvent(
        "{}_adv_end_and_eff".format(prefix),
        start_state_or_event=sm("{}_adv_eff_path".format(prefix)),
    )
    ev_adv_end_and_eff.set_interval(
        wrap_func(sm.name, ev_adv_end_and_eff.name, hpm.timer_interval)
    )

    trg1.set_event(ves["ev_get_{}".format(prefix)])
    trg2a.set_event(ev_no_adv_no_eff)
    trg2b.set_event(ev_no_adv_eff)
    trg2c.set_event(ev_adv_no_eff)
    trg2d.set_event(ev_adv_eff)
    trg3b.set_event(ev_eff)
    trg3c.set_event(ev_adv_end)
    trg3d.set_event(ev_adv_end_and_eff)

    sm("{}_no_adv_no_eff_path".format(prefix)).set_update_parameter_func(
        wrap_func(sm.name, "{}_no_adv_no_eff_path".format(prefix), hpm.set_parameter)
    )
    sm("{}_no_adv_eff_path".format(prefix)).set_update_parameter_func(
        wrap_func(sm.name, "{}_no_adv_eff_path".format(prefix), hpm.set_parameter)
    )
    sm("{}_adv_no_eff_path".format(prefix)).set_update_parameter_func(
        wrap_func(sm.name, "{}_adv_no_eff_path".format(prefix), hpm.set_parameter)
    )
    sm("{}_adv_eff_path".format(prefix)).set_update_parameter_func(
        wrap_func(sm.name, "{}_adv_eff_path".format(prefix), hpm.set_parameter)
    )
    sm("{}_eff".format(prefix)).set_update_parameter_func(
        wrap_func(sm.name, "{}_eff".format(prefix), hpm.set_parameter)
    )
    sm("{}_adv_end".format(prefix)).set_update_parameter_func(
        wrap_func(sm.name, "{}_adv_end".format(prefix), hpm.set_parameter)
    )
    sm("{}_adv_end_and_eff".format(prefix)).set_update_parameter_func(
        wrap_func(sm.name, "{}_adv_end_and_eff".format(prefix), hpm.set_parameter)
    )

    return sm


def make_statemachine_vaceff_status(ves, hpm):
    # StateMachine
    sm = StateMachine("sm_vaceffstatus")
    trg1 = sm.add_transition("start", "no_vaceff", "init_vaceff_end")
    trg2 = sm.add_transition("no_vaceff", "vaceff", "vaceff")
    trg3 = sm.add_transition("vaceff", "no_vaceff", "no_vaceff")

    ev_dummy = DummyEvent("init_vaceff_end")
    ev_vaceff = ParameterEvent("vaceff", ("infection_immune_adjust_c19", 0))
    ev_no_vaceff = ParameterEvent("vaceff", ("infection_immune_adjust_c19", 2.0))
    trg1.set_event(ev_dummy)
    trg2.set_event(ev_vaceff)
    trg3.set_event(ev_no_vaceff)

    return sm


def make_statemachine_vac_imm_log(ves, hpm):
    # StateMachine
    sm = StateMachine("sm_vacimmlog")
    trg1 = sm.add_transition("start", "vacimmlog", "vacimmlog")

    ev_dummy = DummyEvent("vacimmlog", ["infection_immune_adjust_c19"])
    ev_vacimm_change = ParameterEvent("vacimm_change", "infection_immune_adjust_c19")
    trg1.set_event(ev_dummy)
    sm.set_reset_event(ev_vacimm_change)

    return sm


class VACEffSim:
    def make_sm(self, hpm, ves):
        # make state machies
        state_machines = []
        state_machines.append(make_statemachine_VAC(ves, hpm))
        state_machines.append(make_statemachine_infect(ves, hpm))
        state_machines.append(make_statemachine_vacNeff("vac1", ves, hpm))
        state_machines.append(make_statemachine_vacNeff("vac2", ves, hpm))
        state_machines.append(make_statemachine_vaceff_status(ves, hpm))
        # state_machines.append(make_statemachine_vac_imm_log(ves, hpm))

        return state_machines

    def init_sm_sim(self, request):
        # parameter
        hpm = request[0]
        # init VirtualEventSet
        ves = VirtualEventSet()
        # make state machines
        state_machines = self.make_sm(hpm, ves)

        # set virtual events
        ves.set(raise_error_flag=False)
        ves.modify_event_name(raise_error_flag=False)

        time_and_parameters = hpm.get_time_and_parameters()
        sm_vaceffstatus = state_machines[4]
        pu = ParameterUpdater(
            "vac_wane",
            time_and_parameters,
            state_for_activate=sm_vaceffstatus("vaceff"),
            state_for_deactivate=sm_vaceffstatus("no_vaceff"),
        )

        parameter_updaters = [pu]
        health_parameter = {}
        person = Person(
            "template",
            state_machines,
            parameter_updaters,
            health_parameter,
        )
        # set simulation
        start_time = datetime.datetime.strptime(
            "2021-06-01 00:00:00", "%Y-%m-%d %H:%M:%S"
        )
        end_time = datetime.datetime.strptime(
            "2021-09-01 00:00:00", "%Y-%m-%d %H:%M:%S"
        )
        sim = Simulation(start_time, end_time)
        sim.add_person(person)
        # simulation variables
        return sim, person, hpm

    def test(
        self,
        task_name,
        request,
        data_set_log_checks,
    ):
        # make simulation variables
        sim, person, hpm = self.init_sm_sim(request)
        sim.set_detail_logging_flag(True)
        sim.fix_event_name()
        if task_name == "draw_event_network":
            model_check_gui = ModelCheckGUI(person)
            model_check_gui.draw_event_network(detail_flag=False, show=True)
            quit()

        if task_name == "init_check":
            model_check_gui = ModelCheckGUI(person)
            model_check_gui.print_event_func_table()
            model_check_gui.print_update_parameter_func_table()
            quit()

        if task_name == "draw_network":
            model_check_gui = ModelCheckGUI(person)
            model_check_gui.show()
            quit()

        health_parameter = person.health_parameter
        hpm.init_parameter(health_parameter)

        # init sim
        sim.init()
        if task_name in ["report_html", "report_md"]:
            model_report = ModelReport(person)
            current_dir = os.path.dirname(__file__)
            report_dir = os.path.join(current_dir, "report")
            os.makedirs(report_dir, exist_ok=True)
            if task_name == "report_html":
                model_report.make_report(report_dir, format="html")
            if task_name == "report_md":
                model_report.make_report(report_dir, format="md")
            quit()

        # run simulation
        sim.run_simulation()

        # event data
        event_data_set = EventDataSet(IdManager(), [person.event_log])
        print(person.event_log)
        print(health_parameter)

        # check EventLog
        for data_set_log_check in data_set_log_checks:
            check_event = data_set_log_check[0]
            data_set_num = data_set_log_check[1]
            print("check_event = {}".format(check_event.name))
            parameter_event_data_set, _ = event_data_set.get_event_data_set(check_event)
            assert parameter_event_data_set.size() == data_set_num

        if task_name == "model_check":
            model_check_gui = ModelCheckGUI(person)
            model_check_gui.show()
            quit()

    def sim(
        self,
        count_n,
        log_filename,
        request,
        data_set_log_checks,
    ):
        # make simulation variables
        sim, person, hpm = self.init_sm_sim(request)
        sim.set_detail_logging_flag(False)
        # init replay logger
        sim.set_replay_logger()
        # event log
        total_person_event_data_list = []
        for count in tqdm(
            range(count_n), disable=os.environ.get("JENKINS_HOME") is not None
        ):
            health_parameter = person.health_parameter
            hpm.init_parameter(health_parameter)
            person.name = "person{}".format(count)
            # clear replay logger
            sim.set_replay_logger_log()
            # init sim
            sim.init()
            # run simulation
            try:
                sim.run_simulation()
            except ValueError:
                person_event_data_list = sim.get_person_event_data_list()
                total_person_event_data_list.extend(person_event_data_list)
                sim.save_replay_logger("dump.dat")
                break
            person_event_data_list = sim.get_person_event_data_list()
            total_person_event_data_list.extend(person_event_data_list)

        fout = open(log_filename, "wb")
        pickle.dump(total_person_event_data_list, fout)
        fout.close()
