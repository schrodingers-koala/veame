import datetime
import random
import numpy as np


class HealthParameterModel:
    def __init__(self):
        self.config = {
            # no vac, vac1, vac2, vac3
            "vac_selection": (0.10, 0.00, 0.00, 0.90),
            # no_adv_no_eff, no_adv_eff, adv_no_eff, adv_eff
            "vac1_c19_dl_branch": (0.7, 0.3, 0.0, 0.0),
            "vac2_c19_dl_branch": (0.7, 0.3, 0.0, 0.0),
            "vac3_c19_dl_branch": (1.0, 0.0, 0.0, 0.0),
            "vac1_c19_om_branch": (0.9, 0.1, 0.0, 0.0),
            "vac2_c19_om_branch": (0.9, 0.1, 0.0, 0.0),
            "vac3_c19_om_branch": (0.6, 0.4, 0.0, 0.0),
            "vac1": (1, 30),
            "vac2": (28, 112),
            "vac3": (1, 84),
            "dummy_vac1": (1, 30),
            "dummy_vac2": (28, 112),
            "dummy_vac3": (1, 84),
            "vac3_shift": datetime.datetime.strptime(
                "2021-10-01 00:00:00",
                "%Y-%m-%d %H:%M:%S",
            ),
            "vac1_c19_dl_eff": (7, 14),
            "vac2_c19_dl_eff": (3, 7),
            "vac3_c19_dl_eff": (3, 7),
            "vac1_c19_dl_adv_end": (7, 14),
            "vac2_c19_dl_adv_end": (3, 7),
            "vac3_c19_dl_adv_end": (3, 7),
            "vac1_c19_dl_adv_end_and_eff": (7, 14),
            "vac2_c19_dl_adv_end_and_eff": (3, 7),
            "vac3_c19_dl_adv_end_and_eff": (3, 7),
            "vac1_c19_om_eff": (7, 14),
            "vac2_c19_om_eff": (3, 7),
            "vac3_c19_om_eff": (3, 7),
            "vac1_c19_om_adv_end": (7, 14),
            "vac2_c19_om_adv_end": (3, 7),
            "vac3_c19_om_adv_end": (3, 7),
            "vac1_c19_om_adv_end_and_eff": (7, 14),
            "vac2_c19_om_adv_end_and_eff": (3, 7),
            "vac3_c19_om_adv_end_and_eff": (3, 7),
            "fever_dl": (2, 6),
            "fever_om": (2, 6),
        }
        self.start_time = datetime.datetime.strptime(
            "2021-02-01 00:00:00",
            "%Y-%m-%d %H:%M:%S",
        )
        self.end_time = datetime.datetime.strptime(
            "2022-02-01 00:00:00",
            "%Y-%m-%d %H:%M:%S",
        )
        self.config_name = "simple_model_3d_{}_{}_eff1_dl_{}_om_{}_eff2_dl_{}_om_{}_eff3_dl_{}_om_{}_vacdist_{}".format(
            self.start_time.strftime("%B"),
            self.end_time.strftime("%B"),
            "".join(
                map(
                    lambda v: "{:.0f}".format(v * 10),
                    self.config["vac1_c19_dl_branch"],
                )
            ),
            "".join(
                map(
                    lambda v: "{:.0f}".format(v * 10),
                    self.config["vac1_c19_om_branch"],
                )
            ),
            "".join(
                map(
                    lambda v: "{:.0f}".format(v * 10),
                    self.config["vac2_c19_dl_branch"],
                )
            ),
            "".join(
                map(
                    lambda v: "{:.0f}".format(v * 10),
                    self.config["vac2_c19_om_branch"],
                )
            ),
            "".join(
                map(
                    lambda v: "{:.0f}".format(v * 10),
                    self.config["vac3_c19_dl_branch"],
                )
            ),
            "".join(
                map(
                    lambda v: "{:.0f}".format(v * 10),
                    self.config["vac3_c19_om_branch"],
                )
            ),
            "".join(
                map(lambda v: "{:.0f}".format(v * 10), self.config["vac_selection"])
            ),
        )
        self.pandemic_start_time = None

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
                ["select_no_vac", "select_1_vac", "select_2_vac", "select_3_vac"],
                k=1,
                weights=tmp_param,
            )[0]

        if ev_name in [
            "vac1_c19_dl_branch",
            "vac1_c19_om_branch",
            "vac2_c19_dl_branch",
            "vac2_c19_om_branch",
            "vac3_c19_dl_branch",
            "vac3_c19_om_branch",
        ]:
            tmp_config = self.config[ev_name]
            tmp_param = tmp_config
            return random.choices(
                [
                    ev_name[0:-7] + "_no_adv_no_eff_path",
                    ev_name[0:-7] + "_no_adv_eff_path",
                    ev_name[0:-7] + "_adv_no_eff_path",
                    ev_name[0:-7] + "_adv_eff_path",
                ],
                k=1,
                weights=tmp_param,
            )[0]

    def timer_interval(self, sm_name, ev_name, current_time, parameter):
        if ev_name in [
            "vac1",
            "vac2",
            "dummy_vac1",
            "dummy_vac2",
            "vac1_c19_dl_eff",
            "vac2_c19_dl_eff",
            "vac3_c19_dl_eff",
            "vac1_c19_dl_adv_end",
            "vac2_c19_dl_adv_end",
            "vac3_c19_dl_adv_end",
            "vac1_c19_dl_adv_end_and_eff",
            "vac2_c19_dl_adv_end_and_eff",
            "vac3_c19_dl_adv_end_and_eff",
            "vac1_c19_om_eff",
            "vac2_c19_om_eff",
            "vac3_c19_om_eff",
            "vac1_c19_om_adv_end",
            "vac2_c19_om_adv_end",
            "vac3_c19_om_adv_end",
            "vac1_c19_om_adv_end_and_eff",
            "vac2_c19_om_adv_end_and_eff",
            "vac3_c19_om_adv_end_and_eff",
            "fever_dl",
            "fever_om",
        ]:
            tmp_config = self.config[ev_name]
            tmp_param = tmp_config
            return self.rand_wait_time(tmp_param)

        if ev_name in ["vac3", "dummy_vac3"]:
            tmp_config = self.config[ev_name]
            tmp_param = tmp_config
            target_time = self.config["vac3_shift"] + self.rand_wait_time(tmp_param)
            return target_time - current_time

        return datetime.timedelta(days=1)

    def update_infection_immune_adjust_c19_dl(self, parameter):
        if (
            parameter["vac1_c19_dladv"] == "adv"
            or parameter["vac2_c19_dladv"] == "adv"
            or parameter["vac3_c19_dladv"] == "adv"
        ):
            parameter["infection_immune_adjust_c19_dl"] = 2.0
            return
        if (
            parameter["vac1_c19_dleff"] == "eff"
            or parameter["vac2_c19_dleff"] == "eff"
            or parameter["vac3_c19_dleff"] == "eff"
        ):
            parameter["infection_immune_adjust_c19_dl"] = 0.0
            return
        parameter["infection_immune_adjust_c19_dl"] = 1.0

    def update_infection_immune_adjust_c19_om(self, parameter):
        if (
            parameter["vac1_c19_omadv"] == "adv"
            or parameter["vac2_c19_omadv"] == "adv"
            or parameter["vac3_c19_omadv"] == "adv"
        ):
            parameter["infection_immune_adjust_c19_om"] = 2.0
            return
        if (
            parameter["vac1_c19_omeff"] == "eff"
            or parameter["vac2_c19_omeff"] == "eff"
            or parameter["vac3_c19_omeff"] == "eff"
        ) and (
            parameter["vac1_c19_dleff"] == "eff"
            or parameter["vac2_c19_dleff"] == "eff"
            or parameter["vac3_c19_dleff"] == "eff"
        ):
            parameter["infection_immune_adjust_c19_om"] = 0.0
            return
        parameter["infection_immune_adjust_c19_om"] = 1.0

    def set_parameter(self, sm_name, state_name, current_time, parameter):
        if state_name == "select_no_vac":
            parameter["select_vac"] = 0
        if state_name == "select_1_vac":
            parameter["select_vac"] = 1
        if state_name == "select_2_vac":
            parameter["select_vac"] = 2

        if sm_name in [
            "sm_vac1_c19_dl_eff",
            "sm_vac2_c19_dl_eff",
            "sm_vac3_c19_dl_eff",
            "sm_vac1_c19_om_eff",
            "sm_vac2_c19_om_eff",
            "sm_vac3_c19_om_eff",
        ]:
            prefix = sm_name[3:-4]
            if state_name == "{}_no_adv_no_eff_path".format(prefix):
                parameter["{}adv".format(prefix)] = "none"
                parameter["{}eff".format(prefix)] = "none"
            if state_name == "{}_no_adv_eff_path".format(prefix):
                parameter["{}adv".format(prefix)] = "none"
                parameter["{}eff".format(prefix)] = "none"
            if state_name == "{}_adv_no_eff_path".format(prefix):
                parameter["{}adv".format(prefix)] = "adv"
                parameter["{}eff".format(prefix)] = "none"
            if state_name == "{}_adv_eff_path".format(prefix):
                parameter["{}adv".format(prefix)] = "adv"
                parameter["{}eff".format(prefix)] = "none"
            if state_name == "{}_eff".format(prefix):
                parameter["{}adv".format(prefix)] = "none"
                parameter["{}eff".format(prefix)] = "eff"
            if state_name == "{}_adv_end".format(prefix):
                parameter["{}adv".format(prefix)] = "none"
                parameter["{}eff".format(prefix)] = "none"
            if state_name == "{}_adv_end_and_eff".format(prefix):
                parameter["{}adv".format(prefix)] = "none"
                parameter["{}eff".format(prefix)] = "eff"
            self.update_infection_immune_adjust_c19_dl(parameter)
            self.update_infection_immune_adjust_c19_om(parameter)

    def init_parameter(self, parameter):
        parameter.clear()
        parameter["infection_immune_adjust_c19_dl"] = 1.0
        parameter["infection_ratio_c19_dl"] = 1.0
        parameter["infection_base_rate_c19_dl"] = 0.0
        parameter["infection_immune_adjust_c19_om"] = 1.0
        parameter["infection_ratio_c19_om"] = 1.0
        parameter["infection_base_rate_c19_om"] = 0.0
        parameter["vac1_c19_dladv"] = "none"
        parameter["vac1_c19_dleff"] = "none"
        parameter["vac2_c19_dladv"] = "none"
        parameter["vac2_c19_dleff"] = "none"
        parameter["vac3_c19_dladv"] = "none"
        parameter["vac3_c19_dleff"] = "none"
        parameter["vac1_c19_omadv"] = "none"
        parameter["vac1_c19_omeff"] = "none"
        parameter["vac2_c19_omadv"] = "none"
        parameter["vac2_c19_omeff"] = "none"
        parameter["vac3_c19_omadv"] = "none"
        parameter["vac3_c19_omeff"] = "none"
