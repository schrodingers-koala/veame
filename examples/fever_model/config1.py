import datetime
import random
import numpy as np


class HealthParameterModel:
    def __init__(self):
        self.config = {
            "sm_cold": (
                "cold",
                # (P(cure), P(worse), (min_cure_days, max_cure_days), (min_worse_days, max_worse_days))
                (0, 0, (0, 0), (0, 0)),  # 0 "none",
                (0.500, 0.500, (1, 2), (1, 3)),  # 1 "subclinical",
                (0.700, 0.300, (1, 2), (2, 3)),  # 2 "mild",
                (0.998, 0.002, (2, 5), (5, 10)),  # 3 "moderate",
                (0.998, 0.002, (2, 5), (5, 10)),  # 4 "severe",
                (0, 0, (0, 0), (0, 0)),  # 5 "death"
            ),
            "sm_vacadv": (
                "vacadv",
                # (P(cure), P(worse), (min_cure_days, max_cure_days), (min_worse_days, max_worse_days))
                (0, 0, (0, 0), (0, 0)),  # 0 "none",
                (0.100, 0.900, (1, 5), (1, 10)),  # 1 "subclinical",
                (0.700, 0.300, (1, 5), (1, 10)),  # 2 "mild",
                (0.999, 0.001, (2, 5), (5, 10)),  # 3 "moderate",
                (0.970, 0.030, (2, 10), (5, 20)),  # 4 "severe",
                (0, 0, (0, 0), (0, 0)),  # 5 "death"
            ),
            "sm_c19": (
                "c19",
                # (P(cure), P(worse), (min_cure_days, max_cure_days), (min_worse_days, max_worse_days))
                (0, 0, (0, 0), (0, 0)),  # 0 "none",
                (0.100, 0.900, (1, 2), (2, 4)),  # 1 "subclinical",
                (0.200, 0.500, (1, 2), (2, 4)),  # 2 "mild",
                (0.300, 0.300, (2, 4), (3, 6)),  # 3 "moderate",
                (0.400, 0.100, (2, 4), (3, 6)),  # 4 "severe",
                (0, 0, (0, 0), (0, 0)),  # 5 "death"
            ),
            "sm_sick": (
                "sick",
                # (P(cure), P(worse), (min_cure_days, max_cure_days), (min_worse_days, max_worse_days))
                (0, 0, (0, 0), (0, 0)),  # 0 "none",
                (0, 0, (0, 0), (0, 0)),  # 1 "subclinical",
                (0.000, 1.000, (100, 200), (100, 200)),  # 2 "mild",
                (0.500, 0.500, (100, 200), (100, 200)),  # 3 "moderate",
                (1.000, 0.000, (100, 200), (100, 200)),  # 4 "severe",
                (0, 0, (0, 0), (0, 0)),  # 5 "death"
            ),
            "type_vac_branch": (0.5, 0.5),  # P(vaccine), P(placebo)
            "get_vac_branch": (0, 0, 1),  # P(get_vac_0), P(get_vac_1), P(get_vac_2)
            "PCR_reception_branch": (
                # P(accept), P(reject)
                (1.0, 0.0),  # no vac adv
                (0.1, 0.9),  # vac adv
            ),
            "sm_pcr": (
                # (P(pos.|infect), P(neg.|infect), P(pos.|not infect), P(neg.|not infect))
                (0.8000, 0.2000, 0.2000, 0.8000),  # no vac adv
                (0.8000, 0.2000, 0.2000, 0.8000),  # vac adv
            ),
            "sm_vac1adv": (
                0.10,
                0.50,
                0.40,
            ),  # (P(none), P(fever), P(fever & sick_worse))
            "sm_vac1eff": (0.80, 0.20),  # (P(no_effect), P(effect))
            "sm_vac2adv": (
                0.10,
                0.50,
                0.40,
            ),  # (P(none), P(fever), P(fever & sick_worse))
            "sm_vac2eff": (0.80, 0.20),  # (P(no_effect), P(effect))
            "vac1eff_no_effect": (7, 14),  # (min_days, max_days)
            "vac1eff_effect": (7, 14),
            "vac2eff_no_effect": (3, 7),
            "vac2eff_effect": (3, 7),
            "vac1adv_none": (1, 1),
            "vac1adv_fever": (1, 2),
            "vac1adv_fever_before_worse": (1, 2),
            "vac1adv_worse": (1, 30),
            "vac2adv_none": (1, 1),
            "vac2adv_fever": (1, 2),
            "vac2adv_fever_before_worse": (1, 2),
            "vac2adv_worse": (1, 30),
            "vac1_req": (1, 14),
            "vac1": (1, 1),
            "vac2_req": (14, 28),
            "vac2": (1, 1),
        }

    def rand_wait_time(self, param):
        min_hour = 24 * param[0]
        max_hour = 24 * param[1]
        if min_hour == max_hour:
            wait_time = max_hour
        else:
            wait_time = np.random.randint(min_hour, max_hour)
        return datetime.timedelta(hours=wait_time)

    def branch_prob(self, sm_name, ev_name, current_time, parameter):
        if ev_name == "type_vac_branch":
            tmp_config = self.config[ev_name]
            tmp_param = tmp_config
            return random.choices(
                ["vaccine", "placebo"],
                k=1,
                weights=tmp_param,
            )[0]
        if ev_name == "get_vac_branch":
            tmp_config = self.config[ev_name]
            tmp_param = tmp_config
            return random.choices(
                ["get_vac_0", "get_vac_1", "get_vac_2"],
                k=1,
                weights=tmp_param,
            )[0]
        if ev_name == "PCR_reception_branch":
            tmp_config = self.config[ev_name]
            tmp_param = tmp_config
            if parameter["vacadv_val"] > 0.0:
                tmp_param = tmp_config[1]  # vacadv
            else:
                tmp_param = tmp_config[0]  # normal
            weights = (tmp_param[0], tmp_param[1])  # (P(accept), P(reject))
            return random.choices(
                ["PCR_accept", "PCR_reject"],
                k=1,
                weights=weights,
            )[0]
        if sm_name == "sm_vac1adv":
            if parameter["vac_type"] == "placebo":
                return "vac1adv_none_path"
            tmp_config = self.config[sm_name]
            tmp_param = tmp_config
            return random.choices(
                ["vac1adv_none_path", "vac1adv_fever_path", "vac1adv_worse_path"],
                k=1,
                weights=tmp_param[0:3],
            )[0]
        if sm_name == "sm_vac1eff":
            if parameter["vac_type"] == "placebo":
                return "vac1eff_no_effect_path"
            tmp_config = self.config[sm_name]
            tmp_param = tmp_config
            return random.choices(
                ["vac1eff_no_effect_path", "vac1eff_effect_path"],
                k=1,
                weights=tmp_param[0:2],
            )[0]
        if sm_name == "sm_vac2adv":
            if parameter["vac_type"] == "placebo":
                return "vac2adv_none_path"
            tmp_config = self.config[sm_name]
            tmp_param = tmp_config
            return random.choices(
                ["vac2adv_none_path", "vac2adv_fever_path", "vac2adv_worse_path"],
                k=1,
                weights=tmp_param[0:3],
            )[0]
        if sm_name == "sm_vac2eff":
            if parameter["vac_type"] == "placebo":
                return "vac2eff_no_effect_path"
            tmp_config = self.config[sm_name]
            tmp_param = tmp_config
            return random.choices(
                ["vac2eff_no_effect_path", "vac2eff_effect_path"],
                k=1,
                weights=tmp_param[0:2],
            )[0]
        if sm_name in ["sm_cold", "sm_vacadv", "sm_c19"]:
            tmp_config = self.config[sm_name]
            prefix = tmp_config[0]
            val = parameter[prefix + "_val"]
            tmp_param = tmp_config[val + 1]
            curing_status = parameter[prefix + "_curing_status"]
            if curing_status:
                return prefix + "_cure"
            if ev_name == prefix + "_change_branch":
                return random.choices(
                    [prefix + "_cure", prefix + "_worse"],
                    k=1,
                    weights=tmp_param[0:2],
                )[0]
        if sm_name == "sm_sick":
            tmp_config = self.config[sm_name]
            prefix = tmp_config[0]
            val = parameter[prefix + "_val"]
            tmp_param = tmp_config[val + 1]
            if ev_name == prefix + "_change_branch":
                return random.choices(
                    [prefix + "_cure", prefix + "_worse"],
                    k=1,
                    weights=tmp_param[0:2],
                )[0]
        if sm_name == "sm_pcr":
            tmp_config = self.config[sm_name]

            if ev_name == "PCR_result_branch":
                if parameter["vacadv_val"] > 0.0:
                    tmp_param = tmp_config[1]  # vacadv
                else:
                    tmp_param = tmp_config[0]  # normal
                if parameter["c19_val"] > 0.0:
                    weights = (
                        tmp_param[0],
                        tmp_param[1],
                    )  # (P(pos.|infect), P(neg.|infect))
                else:
                    weights = (
                        tmp_param[2],
                        tmp_param[3],
                    )  # (P(pos.|not infect), P(neg.|not infect))
                return random.choices(
                    ["PCR_positive", "PCR_negative"],
                    k=1,
                    weights=weights,
                )[0]

    def timer_interval(self, sm_name, ev_name, current_time, parameter):
        if sm_name in ["sm_cold", "sm_vacadv", "sm_c19", "sm_sick"]:
            tmp_config = self.config[sm_name]
            prefix = tmp_config[0]
            val = parameter[prefix + "_val"]
            tmp_param = tmp_config[val + 1]
            if ev_name == prefix + "_cure_end":
                return self.rand_wait_time(tmp_param[2])
            if ev_name == prefix + "_worse_end":
                return self.rand_wait_time(tmp_param[3])
        if sm_name == "sm_pcr":
            return datetime.timedelta(days=1)

        if ev_name in [
            "vac1eff_no_effect",
            "vac1eff_effect",
            "vac2eff_no_effect",
            "vac2eff_effect",
            "vac1adv_none",
            "vac1adv_fever",
            "vac1adv_fever_before_worse",
            "vac1adv_worse",
            "vac2adv_none",
            "vac2adv_fever",
            "vac2adv_fever_before_worse",
            "vac2adv_worse",
            "vac1_req",
            "vac1",
            "vac2_req",
            "vac2",
        ]:
            tmp_param = self.config[ev_name]
            return self.rand_wait_time(tmp_param)

        # otherwise
        return datetime.timedelta(days=1)

    def prob_cause(self, sm_name, ev_name, current_time, parameter):
        if sm_name == "sm_c19" and ev_name == "infect_c19":
            return (
                parameter["infection_immune_adjust_c19"]
                * parameter["infection_ratio_c19"]
                * parameter["infection_base_rate_c19"]
            )
        if sm_name == "sm_cold" and ev_name == "infect_cold":
            return parameter["infection_base_rate_cold"]
        return 0

    def update_infection_immune_adjust_c19(self, parameter):
        if (
            parameter["vac1adv_immune_status"] == "worse"
            or parameter["vac2adv_immune_status"] == "worse"
        ):
            parameter["infection_immune_adjust_c19"] = 2.0
            return
        if parameter["vac1eff"] == "effect" or parameter["vac2eff"] == "effect":
            parameter["infection_immune_adjust_c19"] = 0.0
            return
        parameter["infection_immune_adjust_c19"] = 1.0

    def set_parameter(self, sm_name, state_name, current_time, parameter):
        if sm_name == "sm_feversum" and state_name == "feversum_0":
            parameter["pcr_request_received"] = False
        if sm_name == "sm_pcr" and state_name == "PCR_reception_branch":
            parameter["pcr_request_received"] = True

        # vac1adv
        if sm_name == "sm_vac1adv" and state_name == "vac1adv_vac":
            if parameter["vac_type"] == "vaccine":
                parameter["vac1adv_immune_status"] = "worse"
                self.update_infection_immune_adjust_c19(parameter)
        if sm_name == "sm_vac1adv" and state_name == "vac1adv_none":
            parameter["vac1adv"] = "none"
        if sm_name == "sm_vac1adv" and state_name == "vac1adv_fever":
            if parameter["vac_type"] == "vaccine":
                parameter["vac1adv"] = "fever"
                # fever_val = cold_val + c19_val + vacadv_val
                # vacadv_val = 0 (no adv), >=1 (adv)
                # fever_val = 0, 1 (no fever), 2 (fever)
                if parameter["vacadv_val"] < 2:
                    parameter["vacadv_val"] += 1
                    parameter["vacadv_curing_status"] = False
        if sm_name == "sm_vac1adv" and state_name == "vac1adv_fever_before_worse":
            if parameter["vac_type"] == "vaccine":
                parameter["vac1adv"] = "worse"
                # fever_val = cold_val + c19_val + vacadv_val
                # vacadv_val = 0 (no adv), >=1 (adv)
                # fever_val = 0, 1 (no fever), 2 (fever)
                if parameter["vacadv_val"] < 2:
                    parameter["vacadv_val"] += 1
                    parameter["vacadv_curing_status"] = False
        if sm_name == "sm_vac1adv" and state_name == "vac1adv_worse":
            if parameter["vac_type"] == "vaccine" and parameter["sick_val"] > 0:
                parameter["sick_val"] += 1

        # vac2adv
        if sm_name == "sm_vac2adv" and state_name == "vac2adv_vac":
            if parameter["vac_type"] == "vaccine":
                parameter["vac2adv_immune_status"] = "worse"
                self.update_infection_immune_adjust_c19(parameter)
        if sm_name == "sm_vac2adv" and state_name == "vac2adv_none":
            if parameter["vac_type"] == "vaccine":
                parameter["vac2adv"] = "none"
        if sm_name == "sm_vac2adv" and state_name == "vac2adv_fever":
            if parameter["vac_type"] == "vaccine":
                parameter["vac2adv"] = "fever"
                # fever_val = cold_val + c19_val + vacadv_val
                # vacadv_val = 0 (no adv), >=1 (adv)
                # fever_val = 0, 1 (no fever), 2 (fever)
                if parameter["vacadv_val"] < 2:
                    parameter["vacadv_val"] += 1
                    parameter["vacadv_curing_status"] = False
        if sm_name == "sm_vac2adv" and state_name == "vac2adv_fever_before_worse":
            if parameter["vac_type"] == "vaccine":
                parameter["vac2adv"] = "worse"
                # fever_val = cold_val + c19_val + vacadv_val
                # vacadv_val = 0 (no adv), >=1 (adv)
                # fever_val = 0, 1 (no fever), 2 (fever)
                if parameter["vacadv_val"] < 2:
                    parameter["vacadv_val"] += 1
                    parameter["vacadv_curing_status"] = False
        if sm_name == "sm_vac2adv" and state_name == "vac2adv_worse":
            if parameter["vac_type"] == "vaccine" and parameter["sick_val"] > 0:
                parameter["sick_val"] += 1

        # vac1eff
        if sm_name == "sm_vac1eff" and state_name == "vac1eff_no_effect":
            parameter["vac1eff"] = "no_effect"
            parameter["vac1adv_immune_status"] = "normal"
            self.update_infection_immune_adjust_c19(parameter)
        if sm_name == "sm_vac1eff" and state_name == "vac1eff_effect":
            if parameter["vac_type"] == "vaccine":
                parameter["vac1eff"] = "effect"
                parameter["vac1adv_immune_status"] = "normal"
                self.update_infection_immune_adjust_c19(parameter)

        # vac2eff
        if sm_name == "sm_vac2eff" and state_name == "vac2eff_no_effect":
            parameter["vac2eff"] = "no_effect"
            parameter["vac2adv_immune_status"] = "normal"
            self.update_infection_immune_adjust_c19(parameter)
        if sm_name == "sm_vac2eff" and state_name == "vac2eff_effect":
            if parameter["vac_type"] == "vaccine":
                parameter["vac2eff"] = "effect"
                parameter["vac2adv_immune_status"] = "normal"
                self.update_infection_immune_adjust_c19(parameter)

    def init_parameter(self, parameter):
        parameter.clear()
        parameter["cold_val"] = 0
        parameter["c19_val"] = 0
        parameter["vacadv_val"] = 0
        parameter["sick_val"] = 0
        parameter["cold_curing_status"] = False
        parameter["vacadv_curing_status"] = False
        parameter["c19_curing_status"] = False
        parameter["pcr_request_received"] = False
        parameter["infection_immune_adjust_c19"] = 1.0
        parameter["infection_ratio_c19"] = 1.0
        parameter["infection_base_rate_c19"] = 0.001
        parameter["infection_base_rate_cold"] = 0
        parameter["vac1adv_immune_status"] = "none"
        parameter["vac2adv_immune_status"] = "none"
        parameter["vac1eff"] = "none"
        parameter["vac2eff"] = "none"
