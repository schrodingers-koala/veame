import os, sys
import pathlib
import argparse
import logging
import importlib
import pickle
import datetime
from tqdm import tqdm
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

# import veame
from veame import *

logging.basicConfig(level=logging.INFO)


def load_module(module_file_path, path_type=None):
    if path_type == "same":
        current_dir = os.path.dirname(__file__)
        module_file_abs_path = os.path.join(current_dir, module_file_path)
        if not os.path.isfile(module_file_abs_path):
            raise FileNotFoundError("{} is not found".format(module_file_abs_path))
        module_file = os.path.basename(module_file_path)
        module_file_no_ext = module_file.split(".")[0]
    else:
        p = pathlib.Path(module_file_path)
        module_file_abs_path = p.resolve()
        if not os.path.isfile(module_file_abs_path):
            raise FileNotFoundError(
                "{} (abs path {}) is not found".format(
                    module_file_path, module_file_abs_path
                )
            )
        module_dir_path = os.path.dirname(module_file_abs_path)
        module_file = os.path.basename(module_file_abs_path)
        module_file_no_ext = module_file.split(".")[0]
        if not module_dir_path in sys.path:
            sys.path.append(module_dir_path)

    try:
        module = importlib.import_module(module_file_no_ext)
    except Exception as e:
        raise ImportError("error")
    print("{} is loaded".format(module_file_path))
    return module


def wrap_func(sm_name, tag_name, hpm_func):
    return lambda current_time, parameter, sm_name=sm_name, tag_name=tag_name: hpm_func(
        sm_name, tag_name, current_time, parameter
    )


# vaccinization model
def make_statemachine_VAC(ves, hpm):
    # StateMachine
    sm = StateMachine("sm_vac")
    trg1a = sm.add_transition("start", "select_no_vac", "select_no_vac")
    trg1b = sm.add_transition("start", "select_1_vac", "select_1_vac")
    trg1c = sm.add_transition("start", "select_2_vac", "select_2_vac")
    trg2 = Trigger("init_end")
    sm.add_transition("select_no_vac", "init_end", trg2)
    sm.add_transition("select_1_vac", "init_end", trg2)
    sm.add_transition("select_2_vac", "init_end", trg2)
    trg3a = sm.add_transition("init_end", "get_vac1", "vac1")
    trg3b = sm.add_transition("init_end", "vac0_out", "vac0_out")
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
    ev_dummy = DummyEvent("ev_init_end")
    trg2.set_event(ev_dummy)

    # TimerEvent
    ev_vac1 = TimerEvent(
        "vac1",
        start_state_or_event=sm("init_end"),
    )
    ev_vac1.set_interval(wrap_func(sm.name, ev_vac1.name, hpm.timer_interval))
    ev_vac2 = TimerEvent(
        "vac2",
        start_state_or_event=sm("get_vac1"),
    )
    ev_vac2.set_interval(wrap_func(sm.name, ev_vac2.name, hpm.timer_interval))

    # set update parameter func
    sm("select_no_vac").set_update_parameter_func(
        wrap_func(sm.name, "select_no_vac", hpm.set_parameter)
    )
    sm("select_1_vac").set_update_parameter_func(
        wrap_func(sm.name, "select_1_vac", hpm.set_parameter)
    )
    sm("select_2_vac").set_update_parameter_func(
        wrap_func(sm.name, "select_2_vac", hpm.set_parameter)
    )

    # ParameterEvent
    ev_vac0_out = ParameterEvent("vac0_out", ("select_vac", 0))
    ev_vac1_out = ParameterEvent("vac1_out", ("select_vac", 1))

    # StateEvent
    ves["ev_get_vac1"] = StateEvent("get_vac1", sm("get_vac1"))
    ves["ev_get_vac2"] = StateEvent("get_vac2", sm("get_vac2"))

    # set event
    trg3a.set_event(ev_vac1)
    trg3b.set_event(ves["ev_infect_c19"] | ev_vac0_out)
    trg4a.set_event(ev_vac2)
    trg4b.set_event(ves["ev_infect_c19"] | ev_vac1_out)

    return sm


# infection model
def make_statemachine_infect(ves, hpm):
    # StateMachine
    sm = StateMachine("sm_infect")
    trg1 = sm.add_transition("start", "infect_c19", "infect_c19")
    trg2 = sm.add_transition("infect_c19", "fever", "fever")
    trg3 = sm.add_transition("fever", "PCR_positive", "PCR_positive")

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
    trg1.set_event(ves["ev_infect_c19"])

    # TimerEvent
    ev_fever = TimerEvent(
        "fever",
        start_state_or_event=sm("infect_c19"),
    )
    ev_fever.set_interval(wrap_func(sm.name, ev_fever.name, hpm.timer_interval))
    trg2.set_event(ev_fever)

    # DummyEvent to log PCR_positive
    ev_dummy = DummyEvent("PCR_positive", event_raise=True)
    trg3.set_event(ev_dummy)
    return sm


# vaccine effect model
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

    # set event
    trg1.set_event(ves["ev_get_{}".format(prefix)])
    trg2a.set_event(ev_no_adv_no_eff)
    trg2b.set_event(ev_no_adv_eff)
    trg2c.set_event(ev_adv_no_eff)
    trg2d.set_event(ev_adv_eff)
    trg3b.set_event(ev_eff)
    trg3c.set_event(ev_adv_end)
    trg3d.set_event(ev_adv_end_and_eff)

    # set update parameter func
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


class TestVACEffModel:
    def make_sm(self, hpm, ves):
        # make state machie
        state_machines = []

        # set up state machines
        state_machines.append(make_statemachine_VAC(ves, hpm))
        state_machines.append(make_statemachine_infect(ves, hpm))
        state_machines.append(make_statemachine_vacNeff("vac1", ves, hpm))
        state_machines.append(make_statemachine_vacNeff("vac2", ves, hpm))

        return state_machines

    def init_sm_sim(self, request):
        # parameter
        hpm = request[0]
        pu_data = request[1]

        # init VirtualEventSet
        ves = VirtualEventSet()

        # make state machines
        state_machines = self.make_sm(hpm, ves)

        # set virtual events
        ves.set(raise_error_flag=False)
        ves.modify_event_name(raise_error_flag=False)

        # ParameterUpdater
        pu = ParameterUpdater(
            "confirmed_case",
            pu_data,
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
        sim = Simulation(hpm.start_time, hpm.end_time)
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


def run_sim(vaceffsim, sim_parameter, task_name, log_filename, count_n):
    param = sim_parameter[0]
    request = param[0]
    hpm = request[0]
    if log_filename is None:
        log_filename = "{}_{}.dat".format(hpm.config_name, count_n)
    if task_name == "sim":
        vaceffsim.sim(count_n, log_filename, *param)
    else:
        vaceffsim.test(task_name, *param)


# set level
tool_log.setLevel(logging.WARNING)
sim_log.setLevel(logging.WARNING)
smpl_log.setLevel(logging.WARNING)

choices = [
    "draw_event_network",
    "init_check",
    "draw_network",
    "report_html",
    "report_md",
    "model_check",
    "sim",
]
parser = argparse.ArgumentParser(description="run simulation.")
parser.add_argument(
    "--task", required=True, type=str, choices=choices, help="task name"
)
parser.add_argument("--config", required=True, type=str, help="path of config py")
parser.add_argument("--output", type=str, default=None, help="event data file")
parser.add_argument("--count", type=int, default=1000, help="simulation counts")

# args
args = parser.parse_args()
task_name = args.task
log_filename = args.output
count_n = args.count
config_path = args.config

# load
hpm_module = load_module(config_path, "same")
hpm = hpm_module.HealthParameterModel()
vaceffsim = TestVACEffModel()

# read incidence rate
current_dir = os.path.dirname(__file__)
input_csv = os.path.join(current_dir, "san_francisco.csv")
df = pd.read_csv(input_csv, index_col=[0])
pu_data = {}
pu_key = [
    datetime.datetime.strptime(x, "%Y-%m-%d").strftime("%Y-%m-%d %H:%M:%S")
    for x in df.index
]
if hpm.pandemic_start_time is not None:
    zero_index = df.loc[df.index < hpm.pandemic_start_time.strftime("%Y-%m-%d")].index
    df.loc[zero_index, "San Francisco"] = 0
pu_value = df["San Francisco"]
population = 900000.0
adj_value = 1.0 / (1.0 - 0.85)
for key, value in zip(pu_key, pu_value):
    pu_data[key] = {"infection_base_rate_c19": value / population * adj_value}

# set parameter
sim_parameter = [
    (
        [
            hpm,
            pu_data,
        ],
        [
            # config of data_set_log_checks
        ],
    ),
]

# run simulation
run_sim(vaceffsim, sim_parameter, task_name, log_filename, count_n)
