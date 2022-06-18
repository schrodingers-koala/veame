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


class VACEffSim:
    def make_sm(self, hpm, ves):
        state_machines = []

        # VACModel
        vac_model = VACModel("sm_vac", 2, hpm, ves)
        sm_vac = vac_model.make_state_machine()
        state_machines.append(sm_vac)

        # PCRModel
        pcr_model = PCRModel("sm_pcr", hpm, ves)
        sm_pcr = pcr_model.make_state_machine()
        state_machines.append(sm_pcr)
        sm_pcr("PCR_reception_branch").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_pcr", state_name="PCR_reception_branch": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )

        # VACADVModel 1
        vac1adv_model = VACADVModel("sm_vac1adv", "vac1adv", 1, hpm, ves)
        sm_vac1adv = vac1adv_model.make_state_machine()
        state_machines.append(sm_vac1adv)
        sm_vac1adv("vac1adv_vac").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac1adv", state_name="vac1adv_vac": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )
        sm_vac1adv("vac1adv_none").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac1adv", state_name="vac1adv_none": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )
        sm_vac1adv("vac1adv_fever").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac1adv", state_name="vac1adv_fever": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )
        sm_vac1adv("vac1adv_fever_before_worse").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac1adv", state_name="vac1adv_fever_before_worse": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )
        sm_vac1adv("vac1adv_worse").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac1adv", state_name="vac1adv_worse": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )

        # VACADVModel 2
        vac2adv_model = VACADVModel("sm_vac2adv", "vac2adv", 2, hpm, ves)
        sm_vac2adv = vac2adv_model.make_state_machine()
        state_machines.append(sm_vac2adv)
        sm_vac2adv("vac2adv_vac").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac2adv", state_name="vac2adv_vac": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )
        sm_vac2adv("vac2adv_none").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac2adv", state_name="vac2adv_none": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )
        sm_vac2adv("vac2adv_fever").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac2adv", state_name="vac2adv_fever": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )
        sm_vac2adv("vac2adv_fever_before_worse").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac2adv", state_name="vac2adv_fever_before_worse": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )
        sm_vac2adv("vac2adv_worse").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac2adv", state_name="vac2adv_worse": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )

        # VACEffModel 1
        vac1eff_model = VACEffModel("sm_vac1eff", "vac1eff", 1, hpm, ves)
        sm_vac1eff = vac1eff_model.make_state_machine()
        state_machines.append(sm_vac1eff)
        sm_vac1eff("vac1eff_no_effect").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac1eff", state_name="vac1eff_no_effect": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )
        sm_vac1eff("vac1eff_effect").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac1eff", state_name="vac1eff_effect": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )

        # VACEffModel 2
        vac2eff_model = VACEffModel("sm_vac2eff", "vac2eff", 2, hpm, ves)
        sm_vac2eff = vac2eff_model.make_state_machine()
        state_machines.append(sm_vac2eff)
        sm_vac2eff("vac2eff_no_effect").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac2eff", state_name="vac2eff_no_effect": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )
        sm_vac2eff("vac2eff_effect").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_vac2eff", state_name="vac2eff_effect": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )

        # SickModel (cold)
        sick_level = ["none", "subclinical", "mild", "moderate", "severe", "death"]
        cold_model = SickModel("sm_cold", "cold", sick_level, hpm, ves)
        sm_cold = cold_model.make_state_machine()
        state_machines.append(sm_cold)
        trg_cold = sm_cold.add_transition("cold_cured", "cold_worse_end", "infect_cold")
        ev_cold_infect = StochasticEvent(
            "infect_cold",
            sm_cold("cold_cured"),
            probability_func=lambda current_time, parameter, sm_name="sm_cold", ev_name="infect_cold": hpm.prob_cause(
                sm_name, ev_name, current_time, parameter
            ),
            event_type=EventType.EDGE,
        )
        trg_cold.set_event(ev_cold_infect)

        # SickModel (vacadv)
        vacadv_model = SickModel("sm_vacadv", "vacadv", sick_level, hpm, ves)
        sm_vacadv = vacadv_model.make_state_machine()
        state_machines.append(sm_vacadv)

        # SickModel (c19)
        c19_model = SickModel("sm_c19", "c19", sick_level, hpm, ves)
        sm_c19 = c19_model.make_state_machine()
        state_machines.append(sm_c19)
        trg_c19 = sm_c19.add_transition("c19_cured", "c19_worse_end", "infect_c19")
        ev_c19_infect = StochasticEvent(
            "infect_c19",
            sm_c19("c19_cured"),
            probability_func=lambda current_time, parameter, sm_name="sm_c19", ev_name="infect_c19": hpm.prob_cause(
                sm_name, ev_name, current_time, parameter
            ),
            event_type=EventType.EDGE,
        )
        trg_c19.set_event(ev_c19_infect)

        # SickModel (sick)
        sick_model = SickModel("sm_sick", "sick", sick_level, hpm, ves)
        sm_sick = sick_model.make_state_machine()
        state_machines.append(sm_sick)

        # SickSumModel (fever)
        fever_level = ["no_fever", "subclinical", "fever"]
        sick_list = ["cold", "c19", "vacadv"]
        feversum_model = SickSumModel(
            "sm_feversum", "feversum", len(fever_level), sick_list, None
        )

        def calc_fever_value(parameter, sick_list):
            val = 0
            for sick_name in sick_list:
                sick_val = parameter.get("{}_val".format(sick_name))
                if sick_val is not None:
                    val += sick_val
            return val

        feversum_model.set_calc_sick_value(calc_fever_value)
        sm_feversum = feversum_model.make_state_machine()
        state_machines.append(sm_feversum)
        ves["fever"] = StateEvent(
            "on_fever",
            sm_feversum("feversum_2"),
        )

        # update parameter to reset "pcr_request_received"
        sm_feversum("feversum_0").set_update_parameter_func(
            lambda current_time, parameter, sm_name="sm_feversum", state_name="feversum_0": hpm.set_parameter(
                sm_name, state_name, current_time, parameter
            )
        )

        # SickSumModel (total)
        sick_level = ["none", "subclinical", "mild", "moderate", "severe", "death"]
        sick_list = ["cold", "c19", "vacadv", "sick"]
        sicksum_model = SickSumModel(
            "sm_sicksum", "sicksum", len(sick_level), sick_list, None
        )
        sm_sicksum = sicksum_model.make_state_machine()
        state_machines.append(sm_sicksum)

        # set PCR_request event
        pe_pcr_request_not_received = ParameterEvent(
            "pcr_request_not_received", ("pcr_request_received", False)
        )
        ves["PCR_request"] = ves["fever"] & pe_pcr_request_not_received

        return state_machines

    def init_sm_sim(self, request):
        # parameter
        hpm = request[0]
        time_and_parameters = request[1]
        # init VirtualEventSet
        ves = VirtualEventSet()
        # make state machies
        state_machines = self.make_sm(hpm, ves)

        # events defined in VACModel
        ves["vac1_cancel"] = ves["fever"] | ves["on_PCR_positive"]
        ves["vac1_check"] = ~ves["vac1_cancel"]
        ves["vac1_reset"] = ves["vac1_check"]  # reset cancel
        ves["vac2_cancel"] = ves["vac1_cancel"]
        ves["vac2_check"] = ves["vac1_check"]
        ves["vac2_reset"] = ves["vac1_reset"]  # reset cancel

        # ParameterUpdater
        pu = ParameterUpdater(
            "updater",
            time_and_parameters,
        )

        # set virtual events
        ves.set(raise_error_flag=False)
        ves.modify_event_name(raise_error_flag=False)

        # set person
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
        if task_name == "draw_event_network":
            model_check_gui = ModelCheckGUI(person)
            model_check_gui.draw_event_network(detail_flag=False, show=True)
            quit()

        health_parameter = person.health_parameter
        hpm.init_parameter(health_parameter)

        # init sim
        sim.init()
        if task_name == "init_check":
            model_check_gui = ModelCheckGUI(person)
            model_check_gui.print_event_func_table()
            quit()

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

        # make event data set
        event_data_set = EventDataSet(IdManager(), [person.event_log])
        print(person.event_log)

        # check log
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
