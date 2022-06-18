import datetime
import random
import numpy as np


class HealthParameterModel:
    def __init__(self):
        self.config = {
            "vac_selection": (0.10, 0.00, 0.90),
            "vac1_branch": (
                0.7,
                0.3,
                0.0,
                0.0,
            ),  # no_adv_no_eff, no_adv_eff, adv_no_eff, adv_eff
            "vac2_branch": (
                0.7,
                0.3,
                0.0,
                0.0,
            ),  # no_adv_no_eff, no_adv_eff, adv_no_eff, adv_eff
            "vac1": (1, 30),
            "vac2": (28, 35),
            "vac1_eff": (7, 14),
            "vac2_eff": (3, 7),
            "vac1_adv_end": (7, 14),
            "vac2_adv_end": (3, 7),
            "vac1_adv_end_and_eff": (7, 14),
            "vac2_adv_end_and_eff": (3, 7),
            "fever": (2, 6),
        }
        self.start_time = datetime.datetime.strptime(
            "2021-07-01 00:00:00",
            "%Y-%m-%d %H:%M:%S",
        )
        self.end_time = datetime.datetime.strptime(
            "2022-01-01 00:00:00",
            "%Y-%m-%d %H:%M:%S",
        )
        self.config_name = "simple_model_{}_{}_eff1_{}_eff2_{}_vacdist_{}".format(
            self.start_time.strftime("%B"),
            self.end_time.strftime("%B"),
            "_".join(
                map(lambda v: "{:.0f}".format(v * 10), self.config["vac1_branch"])
            ),
            "_".join(
                map(lambda v: "{:.0f}".format(v * 10), self.config["vac2_branch"])
            ),
            "_".join(
                map(lambda v: "{:.0f}".format(v * 10), self.config["vac_selection"])
            ),
        )

    def rand_wait_time(self, param):
        min_hour = 24 * param[0]
        max_hour = 24 * param[1]
        if min_hour == max_hour:
            wait_time = max_hour
        else:
            wait_time = np.random.randint(min_hour, max_hour)
        return datetime.timedelta(hours=wait_time)

    def branch_prob(self, sm_name, ev_name, current_time, parameter):
        if ev_name == "vac_selection":
            tmp_config = self.config[ev_name]
            tmp_param = tmp_config
            return random.choices(
                ["select_no_vac", "select_1_vac", "select_2_vac"],
                k=1,
                weights=tmp_param,
            )[0]
        if ev_name == "vac1_branch":
            tmp_config = self.config[ev_name]
            tmp_param = tmp_config
            return random.choices(
                [
                    "vac1_no_adv_no_eff_path",
                    "vac1_no_adv_eff_path",
                    "vac1_adv_no_eff_path",
                    "vac1_adv_eff_path",
                ],
                k=1,
                weights=tmp_param,
            )[0]
        if ev_name == "vac2_branch":
            tmp_config = self.config[ev_name]
            tmp_param = tmp_config
            return random.choices(
                [
                    "vac2_no_adv_no_eff_path",
                    "vac2_no_adv_eff_path",
                    "vac2_adv_no_eff_path",
                    "vac2_adv_eff_path",
                ],
                k=1,
                weights=tmp_param,
            )[0]

    def timer_interval(self, sm_name, ev_name, current_time, parameter):
        if ev_name in [
            "vac1",
            "vac2",
            "vac1_eff",
            "vac2_eff",
            "vac1_adv_end",
            "vac2_adv_end",
            "vac1_adv_end_and_eff",
            "vac2_adv_end_and_eff",
            "fever",
        ]:
            tmp_config = self.config[ev_name]
            tmp_param = tmp_config
            return self.rand_wait_time(tmp_param)

        return datetime.timedelta(days=1)

    def prob_cause(self, sm_name, ev_name, current_time, parameter):
        # StochasticEvent
        if ev_name == "infect_c19":
            return (
                parameter["infection_immune_adjust_c19"]
                * parameter["infection_ratio_c19"]
                * parameter["infection_base_rate_c19"]
            )
        return 0

    def update_infection_immune_adjust_c19(self, parameter):
        if parameter["vac1adv"] == "adv" or parameter["vac2adv"] == "adv":
            parameter["infection_immune_adjust_c19"] = 2.0
            return
        if parameter["vac1eff"] == "eff" or parameter["vac2eff"] == "eff":
            parameter["infection_immune_adjust_c19"] = 0.0
            return
        parameter["infection_immune_adjust_c19"] = 1.0

    def set_parameter(self, sm_name, state_name, current_time, parameter):
        if state_name == "select_no_vac":
            parameter["select_vac"] = 0
        if state_name == "select_1_vac":
            parameter["select_vac"] = 1
        if state_name == "select_2_vac":
            parameter["select_vac"] = 2

        if sm_name in ["sm_vac1_eff", "sm_vac2_eff"]:
            if sm_name == "sm_vac1_eff":
                prefix = "vac1"
            if sm_name == "sm_vac2_eff":
                prefix = "vac2"
            if state_name == "{}_no_adv_no_eff_path".format(prefix):
                parameter["{}adv".format(prefix)] = "none"
                parameter["{}eff".format(prefix)] = "none"
                self.update_infection_immune_adjust_c19(parameter)
            if state_name == "{}_no_adv_eff_path".format(prefix):
                parameter["{}adv".format(prefix)] = "none"
                parameter["{}eff".format(prefix)] = "none"
                self.update_infection_immune_adjust_c19(parameter)
            if state_name == "{}_adv_no_eff_path".format(prefix):
                parameter["{}adv".format(prefix)] = "adv"
                parameter["{}eff".format(prefix)] = "none"
                self.update_infection_immune_adjust_c19(parameter)
            if state_name == "{}_adv_eff_path".format(prefix):
                parameter["{}adv".format(prefix)] = "adv"
                parameter["{}eff".format(prefix)] = "none"
                self.update_infection_immune_adjust_c19(parameter)
            if state_name == "{}_eff".format(prefix):
                parameter["{}adv".format(prefix)] = "none"
                parameter["{}eff".format(prefix)] = "eff"
                self.update_infection_immune_adjust_c19(parameter)
            if state_name == "{}_adv_end".format(prefix):
                parameter["{}adv".format(prefix)] = "none"
                parameter["{}eff".format(prefix)] = "none"
                self.update_infection_immune_adjust_c19(parameter)
            if state_name == "{}_adv_end_and_eff".format(prefix):
                parameter["{}adv".format(prefix)] = "none"
                parameter["{}eff".format(prefix)] = "eff"
                self.update_infection_immune_adjust_c19(parameter)

    def init_parameter(self, parameter):
        parameter.clear()
        parameter["infection_immune_adjust_c19"] = 1.0
        parameter["infection_ratio_c19"] = 1.0
        parameter["infection_base_rate_c19"] = 0.0
        parameter["vac1adv"] = "none"
        parameter["vac1eff"] = "none"
        parameter["vac2adv"] = "none"
        parameter["vac2eff"] = "none"
