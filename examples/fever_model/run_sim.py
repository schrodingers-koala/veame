import os, sys
import pathlib
import argparse
import logging
import importlib

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


def run_sim(vaceffsim, sim_parameter, task_name, log_filename, count_n):
    param = sim_parameter[0]
    if task_name == "sim":
        vaceffsim.sim(count_n, log_filename, *param)
    else:
        vaceffsim.test(task_name, *param)


# parser
choices = [
    "draw_event_network",
    "init_check",
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

# check input
if task_name == "sim" and log_filename is None:
    print("please set log_filename")
    parser.print_help()
    sys.exit()

# load
hpm_module = load_module(config_path, "same")
hpm = hpm_module.HealthParameterModel()
vaceffsim_module = load_module("model.py", "same")
vaceffsim = vaceffsim_module.VACEffSim()

# set parameter
sim_parameter = [
    (
        [
            hpm,
            {
                # config for parameter setup
                # "yyyy-MM-dd HH:mm:ss": {<parameter>: <value>},
            },
        ],
        [
            # config of data_set_log_checks
        ],
    ),
]

# run
run_sim(vaceffsim, sim_parameter, task_name, log_filename, count_n)
