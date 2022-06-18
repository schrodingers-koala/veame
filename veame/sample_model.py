from .common import EventType
from .common import smpl_log
from .statemachine import StateMachine
from .statemachine import Trigger
from .event import StochasticEvent
from .event import TimerEvent
from .event import RandomEvent
from .event import DummyEvent
from .event import ParameterEvent
from .event import StateEvent


class SickModel:
    """
    Model of sick.
    SickModel uses following health parameters.
    - <prefix>_val
    - <prefix>_status
    - <prefix>_curing_status

    SickModel uses following functions defined in parameter_model.
    - function which returns a choice selected randomly for a RandomEvent named "<prefix>_change_branch".
      Choices are "<prefix>_cure" and "<prefix>_worse".
    - function which returns the wait time for a TimerEvent named "<prefix>_cure_end".
    - function which returns the wait time for a TimerEvent named "<prefix>_worse_end".

    Constructor options
    -------------------
    name : str
        name of state machine.
    prefix : str
        prefix of parameter.
    state_name_list: list
        list of symptom levels.
    parameter_model : HealthParameterModel
    ves : VirtualEventSet

    Examples
    --------
    >>> sick_level = ["none", "subclinical", "mild", "moderate", "severe", "death"]
    >>> cold_model = SickModel("sm_cold", "cold", sick_level, hpm, ves)
    >>> sm_cold = cold_model.make_state_machine()
    >>> state_machines.append(sm_cold)
    """

    def __init__(self, name, prefix, state_name_list, parameter_model, ves):
        self.name = name
        self.prefix = prefix
        self.state_name_list = state_name_list
        self.parameter_model = parameter_model
        self.val_name = "{}_val".format(self.prefix)
        self.status_name = "{}_status".format(self.prefix)
        self.curing_status_name = "{}_curing_status".format(self.prefix)
        self.max_val = len(state_name_list) - 1
        self.ves = ves

    def make_state_machine(self):
        sm = StateMachine(self.name)

        ev1a_name = "{}_not_cured".format(self.prefix)
        ev1b_name = "{}_drop".format(self.prefix)
        ev1c_name = "{}_cured".format(self.prefix)
        branch_name = "{}_change_branch".format(self.prefix)
        ev2a_name = "{}_cure".format(self.prefix)
        ev2b_name = "{}_worse".format(self.prefix)
        ev3a_name = "{}_cure_end".format(self.prefix)
        ev3b_name = "{}_worse_end".format(self.prefix)

        trg1a = sm.add_transition("start", branch_name, ev1a_name)
        trg1b = sm.add_transition("start", "drop", ev1b_name)
        trg1c = sm.add_transition("start", ev1c_name, ev1c_name)
        trg2a = sm.add_transition(branch_name, ev2a_name, ev2a_name)
        trg2b = sm.add_transition(branch_name, ev2b_name, ev2b_name)
        trg3a = sm.add_transition(ev2a_name, ev3a_name, ev3a_name)
        trg3b = sm.add_transition(ev2b_name, ev3b_name, ev3b_name)

        def correct_irregular_val(current_time, parameter):
            val = parameter[self.val_name]
            if val < 0:
                val = 0
            parameter[self.status_name] = self.state_name_list[val]
            parameter[self.val_name] = val
            if val == 0:
                parameter[self.curing_status_name] = False

        sm("start").set_update_parameter_func(correct_irregular_val)

        sm(ev1c_name).set_update_parameter_func(correct_irregular_val)

        def cure_update_val(current_time, parameter):
            parameter[self.val_name] -= 1
            parameter[self.curing_status_name] = True

        sm(ev3a_name).set_update_parameter_func(cure_update_val)

        def worse_update_val(current_time, parameter):
            parameter[self.val_name] += 1
            parameter[self.curing_status_name] = False

        sm(ev3b_name).set_update_parameter_func(worse_update_val)

        def choice_drop(current_time, parameter):
            val = parameter[self.val_name]
            if val == 0:
                return ev1c_name
            if val < self.max_val:
                return ev1a_name
            return ev1b_name

        ev1_name = "{}_drop_branch".format(self.prefix)
        ev1 = RandomEvent(
            ev1_name,
            choice_drop,
            sm("start"),
        )

        ev2_name = branch_name
        ev2 = RandomEvent(
            ev2_name,
            None,
            sm(branch_name),
        )
        ev2.set_name_and_probability_func(
            lambda current_time, parameter, sm_name=self.name, ev_name=ev2_name: self.parameter_model.branch_prob(
                sm_name, ev_name, current_time, parameter
            )
        )

        ev3a = TimerEvent(
            ev3a_name,
            start_state_or_event=sm(ev2a_name),
            interval=lambda current_time, parameter, sm_name=self.name, ev_name=ev3a_name: self.parameter_model.timer_interval(
                sm_name, ev_name, current_time, parameter
            ),
        )

        ev3b = TimerEvent(
            ev3b_name,
            start_state_or_event=sm(ev2b_name),
            interval=lambda current_time, parameter, sm_name=self.name, ev_name=ev3b_name: self.parameter_model.timer_interval(
                sm_name, ev_name, current_time, parameter
            ),
        )

        trg1a.set_event(ev1.event(ev1a_name))
        trg1b.set_event(ev1.event(ev1b_name))
        trg1c.set_event(ev1.event(ev1c_name))
        trg2a.set_event(ev2.event(ev2a_name))
        trg2b.set_event(ev2.event(ev2b_name))
        trg3a.set_event(ev3a)
        trg3b.set_event(ev3b)

        ev_reset_name = "{}_change".format(self.val_name)
        ev_reset = ParameterEvent(ev_reset_name, self.val_name)
        sm.set_reset_event(ev_reset)

        return sm


class VACModel:
    """
    Model of vaccination.
    VACModel uses following health parameters.
    - vac_type
    - vac_get

    VACModel uses following functions defined in parameter_model.
    - function which returns a choice selected randomly for a RandomEvent named "type_vac_branch".
      Choices are "vaccine" and "placebo".
    - function which returns a choice selected randomly for a RandomEvent named "get_vac_branch".
    - function which returns the wait time for a TimerEvent named "vac<N>_req".
    - function which returns the wait time for a TimerEvent named "vac<N>".

    VACModel provides following event.
    - ves["vac<N>"]

    VACModel uses following events.
    - ves["vac<N>_check"]
    - ves["vac<N>_cancel"]
    - ves["vac<N>_reset"]

    Constructor options
    -------------------
    name : str
        name of state machine.
    vac_num : int
        maximum number of vaccine doeses.
    parameter_model: HealthParameterModel
    ves : VirtualEventSet

    Examples
    --------
    >>> vac_model = VACModel("sm_vac", 2, hpm, ves)
    >>> sm_vac = vac_model.make_state_machine()
    >>> state_machines.append(sm_vac)
    """

    def __init__(self, name, vac_num, parameter_model, ves):
        self.name = name
        self.vac_num = vac_num
        self.parameter_model = parameter_model
        self.ves = ves

    def set_vac_type(self, vac_type, current_time, parameter):
        parameter["vac_type"] = vac_type

    def set_vac_get(self, vac_i, current_time, parameter):
        parameter["vac_get"] = vac_i

    def make_state_machine(self):
        sm = StateMachine(self.name)

        # RandomEvent
        ev1_name = "type_vac_branch"
        ev1 = RandomEvent(ev1_name, None, sm("start"))
        ev1.set_name_and_probability_func(
            lambda current_time, parameter, sm_name=self.name, ev_name=ev1_name: self.parameter_model.branch_prob(
                sm_name, ev_name, current_time, parameter
            )
        )
        for vac_type in ["vaccine", "placebo"]:
            state_name1 = "start"
            state_name2 = vac_type
            trg1 = Trigger(state_name2)
            sm.add_transition(state_name1, state_name2, trg1)
            ev1child_name = "{}".format(state_name2)
            ev1child = ev1.event(ev1child_name)
            trg1.set_event(ev1child)
            sm(state_name2).set_update_parameter_func(
                lambda current_time, parameter, vac_type=vac_type: self.set_vac_type(
                    vac_type, current_time, parameter
                )
            )
        state_name3 = "select_get_vac"
        trg3 = Trigger(state_name3)
        ev3 = DummyEvent("{}".format(state_name3))
        for vac_type in ["vaccine", "placebo"]:
            state_name2 = vac_type
            sm.add_transition(state_name2, state_name3, trg3)
            trg3.set_event(ev3)

        # RandomEvent
        ev2_name = "get_vac_branch"
        ev2 = RandomEvent(ev2_name, None, sm("select_get_vac"))
        ev2.set_name_and_probability_func(
            lambda current_time, parameter, sm_name=self.name, ev_name=ev2_name: self.parameter_model.branch_prob(
                sm_name, ev_name, current_time, parameter
            )
        )
        for vac_i in range(self.vac_num + 1):
            state_name1 = "select_get_vac"
            state_name2 = "get_vac_{}".format(vac_i)
            trg2 = Trigger(state_name2)
            sm.add_transition(state_name1, state_name2, trg2)
            ev2child_name = "{}".format(state_name2)
            ev2child = ev2.event(ev2child_name)
            trg2.set_event(ev2child)
            sm(state_name2).set_update_parameter_func(
                lambda current_time, parameter, vac_i=vac_i: self.set_vac_get(
                    vac_i, current_time, parameter
                )
            )
        state_name3 = "init_end"
        trg3 = Trigger(state_name3)
        ev3 = DummyEvent("{}".format(state_name3))
        for vac_i in range(self.vac_num + 1):
            state_name2 = "get_vac_{}".format(vac_i)
            sm.add_transition(state_name2, state_name3, trg3)
            trg3.set_event(ev3)

        # 1: init_end/vacN-1_after -(ev_vacN_req)----> vacN_req
        # 2: vacN_req              -(ev_vacN)--------> vacN_after
        # 3:                       -(ev_vacN_cancel)-> vacN_cancel
        # 4: vacN_cancel           -(ev_vacN_reset)--> init_end/vacN-1_after
        for vac_i in range(self.vac_num):
            if vac_i == 0:
                state_name0 = "init_end"
            else:
                state_name0 = "vac{}_after".format(vac_i)
            state_name1a = "vac{}_ready".format(vac_i + 1)
            state_name1b = "vac{}_out".format(vac_i)
            state_name2 = "vac{}_check".format(vac_i + 1)
            state_name3 = "vac{}_req".format(vac_i + 1)
            state_name4a = "vac{}_after".format(vac_i + 1)
            state_name4b = "vac{}_cancel".format(vac_i + 1)

            trg1a = Trigger(state_name1a)
            trg1b = Trigger(state_name1b)
            trg2 = Trigger(state_name2)
            trg3 = Trigger(state_name3)
            trg4a = Trigger(state_name4a)
            trg4b = Trigger(state_name4b)
            trg4c = Trigger("vac{}_reset".format(vac_i + 1))
            sm.add_transition(state_name0, state_name1a, trg1a)
            sm.add_transition(state_name0, state_name1b, trg1b)
            sm.add_transition(state_name1a, state_name2, trg2)
            sm.add_transition(state_name2, state_name3, trg3)
            sm.add_transition(state_name3, state_name4a, trg4a)
            sm.add_transition(state_name3, state_name4b, trg4b)
            sm.add_transition(state_name4b, state_name1a, trg4c)

            # ev_vacN_ready
            ev1a = ParameterEvent(
                "{}".format(state_name1a),
                lambda parameter, vac_i=vac_i: parameter["vac_get"] > vac_i,
            )
            trg1a.set_event(ev1a)
            # ev_vacN_out
            ev1b = ParameterEvent(
                "{}".format(state_name1b),
                lambda parameter, vac_i=vac_i: parameter["vac_get"] <= vac_i,
            )
            trg1b.set_event(ev1b)
            # ev_vacN_check
            trg2.set_event(self.ves["vac{}_check".format(vac_i + 1)])
            # ev_vacN_req
            ev3_name = "{}".format(state_name3)
            ev3 = TimerEvent(
                ev3_name,
                start_state_or_event=sm(state_name1a),
                interval=lambda current_time, parameter, sm_name=self.name, ev_name=ev3_name: self.parameter_model.timer_interval(
                    sm_name, ev_name, current_time, parameter
                ),
            )
            trg3.set_event(ev3)
            # ev_vacN
            ev3a_name = "vac{}".format(vac_i + 1)
            self.ves[ev3a_name] = StateEvent(
                ev3a_name,
                sm(state_name4a),
            )
            ev4a = TimerEvent(
                "{}_timer".format(ev3a_name),
                start_state_or_event=sm(state_name3),
                interval=lambda current_time, parameter, sm_name=self.name, ev_name=ev3a_name: self.parameter_model.timer_interval(
                    sm_name, ev_name, current_time, parameter
                ),
            )
            trg4a.set_event(ev4a)
            trg4b.set_event(self.ves["vac{}_cancel".format(vac_i + 1)])
            trg4c.set_event(self.ves["vac{}_reset".format(vac_i + 1)])

        return sm


class PCRModel:
    """
    Model of PCR test.

    PCRModel uses following functions defined in parameter_model.
    - function which returns a choice selected randomly for a RandomEvent named "PCR_reception_branch".
      Choices are "PCR_accept" and "PCR_reject".
    - function which returns a choice selected randomly for a RandomEvent named "PCR_result_branch".
      Choices are "PCR_positive" and "PCR_negative".
    - function which returns the wait time for a TimerEvent named "PCR_check".
    - function which returns the wait time for a TimerEvent named "PCR_result".

    PCRModel provides following event.
    - ves["on_PCR_positive"]

    PCRModel uses following event.
    - ves["PCR_request"]

    Constructor options
    -------------------
    name : str
        name of state machine.
    parameter_model: HealthParameterModel
    ves : VirtualEventSet

    Examples
    --------
    >>> pcr_model = PCRModel("sm_pcr", hpm, ves)
    >>> sm_pcr = pcr_model.make_state_machine()
    >>> state_machines.append(sm_pcr)
    """

    def __init__(self, name, parameter_model, ves):
        self.name = name
        self.parameter_model = parameter_model
        self.ves = ves

    def make_state_machine(self):
        sm = StateMachine(self.name)

        trg1 = Trigger("PCR_request")
        trg2 = Trigger("PCR_request_received")
        trg3a = Trigger("PCR_accept")
        trg3b = Trigger("PCR_reject")
        trg4 = Trigger("PCR_check")
        trg5 = Trigger("PCR_result")
        trg6a = Trigger("PCR_positive")
        trg6b = Trigger("PCR_negative")
        sm.add_transition("start", "PCR_request", trg1)
        sm.add_transition("PCR_request", "PCR_reception_branch", trg2)
        sm.add_transition("PCR_reception_branch", "PCR_accept", trg3a)
        sm.add_transition("PCR_reception_branch", "start", trg3b)
        sm.add_transition("PCR_accept", "PCR_check", trg4)
        sm.add_transition("PCR_check", "PCR_result", trg5)
        sm.add_transition("PCR_result", "PCR_positive", trg6a)
        sm.add_transition("PCR_result", "start", trg6b)
        trg1.set_event(self.ves["PCR_request"])
        # DummyEvent
        ev2 = DummyEvent("PCR_request_received")
        trg2.set_event(ev2)
        # RandomEvent
        ev3_name = "PCR_reception_branch"
        ev3 = RandomEvent(
            ev3_name,
            None,
            sm("PCR_reception_branch"),
        )
        ev3a = ev3.event("PCR_accept")
        ev3b = ev3.event("PCR_reject")
        ev3.set_name_and_probability_func(
            lambda current_time, parameter, sm_name=self.name, ev_name=ev3_name: self.parameter_model.branch_prob(
                sm_name, ev_name, current_time, parameter
            )
        )
        trg3a.set_event(ev3a)
        trg3b.set_event(ev3b)
        # TimerEvent
        ev4_name = "PCR_check"
        ev4 = TimerEvent(
            ev4_name,
            start_state_or_event=sm("PCR_request"),
            interval=lambda current_time, parameter, sm_name=self.name, ev_name=ev4_name: self.parameter_model.timer_interval(
                sm_name, ev_name, current_time, parameter
            ),
        )
        trg4.set_event(ev4)
        # TimerEvent
        ev5_name = "PCR_result"
        ev5 = TimerEvent(
            ev5_name,
            start_state_or_event=sm("PCR_check"),
            interval=lambda current_time, parameter, sm_name=self.name, ev_name=ev5_name: self.parameter_model.timer_interval(
                sm_name, ev_name, current_time, parameter
            ),
        )
        trg5.set_event(ev5)
        # RandomEvent
        ev6_name = "PCR_result_branch"
        ev6 = RandomEvent(
            ev6_name,
            None,
            sm("PCR_check"),
        )
        ev6a = ev6.event("PCR_positive")
        ev6b = ev6.event("PCR_negative")
        ev6.set_name_and_probability_func(
            lambda current_time, parameter, sm_name=self.name, ev_name=ev6_name: self.parameter_model.branch_prob(
                sm_name, ev_name, current_time, parameter
            )
        )
        trg6a.set_event(ev6a)
        trg6b.set_event(ev6b)

        ev_on_PCR_positive = StateEvent(
            "on_PCR_positive",
            sm("PCR_positive"),
            EventType.LEVEL,
        )
        self.ves["on_PCR_positive"] = ev_on_PCR_positive

        return sm


class VACADVModel:
    """
    Model of vaccine adverse effect.

    VACADVModel uses following functions defined in parameter_model.
    - function which returns a choice selected randomly for a RandomEvent named "<prefix>_vac_branch".
    - function which returns the wait time for a TimerEvent named "<prefix>_none".
    - function which returns the wait time for a TimerEvent named "<prefix>_fever".
    - function which returns the wait time for a TimerEvent named "<prefix>_fever_before_worse".
    - function which returns the wait time for a TimerEvent named "<prefix>_worse".

    VACADVModel uses following event.
    - ves["vac<N>"]

    Constructor options
    -------------------
    name : str
        name of state machine.
    prefix : str
        prefix of parameter.
    vac_n : int
        n-th vaccine dose.
    parameter_model: HealthParameterModel
    ves : VirtualEventSet

    Examples
    --------
    >>> vac1adv_model = VACADVModel("sm_vac1adv", "vac1adv", 1, hpm, ves)
    >>> sm_vac1adv = vac1adv_model.make_state_machine()
    >>> state_machines.append(sm_vac1adv)
    """

    def __init__(self, name, prefix, vac_n, parameter_model, ves):
        self.name = name
        self.prefix = prefix
        self.vac_n = vac_n
        self.parameter_model = parameter_model
        self.ves = ves

    def make_state_machine(self):
        sm = StateMachine(self.name)

        state_name1 = "start"
        state_name2 = "{}_vac".format(self.prefix)
        state_name3a = "{}_none_path".format(self.prefix)
        state_name3b = "{}_fever_path".format(self.prefix)
        state_name3c = "{}_worse_path".format(self.prefix)
        state_name4a = "{}_none".format(self.prefix)
        state_name4b = "{}_fever".format(self.prefix)
        state_name4c = "{}_fever_before_worse".format(self.prefix)
        state_name5c = "{}_worse".format(self.prefix)

        trg2 = Trigger(state_name2)
        trg3a = Trigger(state_name3a)
        trg3b = Trigger(state_name3b)
        trg3c = Trigger(state_name3c)
        trg4a = Trigger(state_name4a)
        trg4b = Trigger(state_name4b)
        trg4c = Trigger(state_name4c)
        trg5c = Trigger(state_name5c)
        sm.add_transition(state_name1, state_name2, trg2)
        sm.add_transition(state_name2, state_name3a, trg3a)
        sm.add_transition(state_name2, state_name3b, trg3b)
        sm.add_transition(state_name2, state_name3c, trg3c)
        sm.add_transition(state_name3a, state_name4a, trg4a)
        sm.add_transition(state_name3b, state_name4b, trg4b)
        sm.add_transition(state_name3c, state_name4c, trg4c)
        sm.add_transition(state_name4c, state_name5c, trg5c)

        #
        trg2.set_event(self.ves["vac{}".format(self.vac_n)])

        # Random Event
        ev3_name = "{}_vac_branch".format(self.prefix)
        ev3 = RandomEvent(
            ev3_name,
            lambda current_time, parameter, sm_name=self.name, ev_name=ev3_name: self.parameter_model.branch_prob(
                sm_name, ev_name, current_time, parameter
            ),
            sm(state_name2),
        )
        ev3a = ev3.event("{}_none_path".format(self.prefix))
        ev3b = ev3.event("{}_fever_path".format(self.prefix))
        ev3c = ev3.event("{}_worse_path".format(self.prefix))
        trg3a.set_event(ev3a)
        trg3b.set_event(ev3b)
        trg3c.set_event(ev3c)

        # TimerEvent
        ev4a_name = "{}_none".format(self.prefix)
        ev4a = TimerEvent(
            ev4a_name,
            start_state_or_event=sm(state_name3a),
            interval=lambda current_time, parameter, sm_name=self.name, ev_name=ev4a_name: self.parameter_model.timer_interval(
                sm_name, ev_name, current_time, parameter
            ),
        )
        trg4a.set_event(ev4a)

        # TimerEvent
        ev4b_name = "{}_fever".format(self.prefix)
        ev4b = TimerEvent(
            ev4b_name,
            start_state_or_event=sm(state_name3b),
            interval=lambda current_time, parameter, sm_name=self.name, ev_name=ev4b_name: self.parameter_model.timer_interval(
                sm_name, ev_name, current_time, parameter
            ),
        )
        trg4b.set_event(ev4b)

        # TimerEvent
        ev4c_name = "{}_fever_before_worse".format(self.prefix)
        ev4c = TimerEvent(
            ev4c_name,
            start_state_or_event=sm(state_name3c),
            interval=lambda current_time, parameter, sm_name=self.name, ev_name=ev4c_name: self.parameter_model.timer_interval(
                sm_name, ev_name, current_time, parameter
            ),
        )
        trg4c.set_event(ev4c)

        # TimerEvent
        ev5c_name = "{}_worse".format(self.prefix)
        ev5c = TimerEvent(
            ev5c_name,
            start_state_or_event=sm(state_name4c),
            interval=lambda current_time, parameter, sm_name=self.name, ev_name=ev5c_name: self.parameter_model.timer_interval(
                sm_name, ev_name, current_time, parameter
            ),
        )
        trg5c.set_event(ev5c)

        return sm


class VACEffModel:
    """
    Model of vaccine effect.

    VACEffModel uses following functions defined in parameter_model.
    - function which returns a choice selected randomly for a RandomEvent named "<prefix>_vac_branch".
    - function which returns the wait time for a TimerEvent named "<prefix>_no_effect".
    - function which returns the wait time for a TimerEvent named "<prefix>_effect".

    VACEffModel uses following event.
    - ves["vac<N>"]

    Constructor options
    -------------------
    name : str
        name of state machine.
    prefix : str
        prefix of parameter.
    vac_n : int
        n-th vaccine dose.
    parameter_model: HealthParameterModel
    ves : VirtualEventSet

    Examples
    --------
    >>> vac1eff_model = VACEffModel("sm_vac1eff", "vac1eff", 1, hpm, ves)
    >>> sm_vac1eff = vac1eff_model.make_state_machine()
    >>> state_machines.append(sm_vac1eff)
    """

    def __init__(self, name, prefix, vac_n, parameter_model, ves):
        self.name = name
        self.prefix = prefix
        self.vac_n = vac_n
        self.parameter_model = parameter_model
        self.ves = ves

    def make_state_machine(self):
        sm = StateMachine(self.name)

        state_name1 = "start"
        state_name2 = "{}_vac".format(self.prefix)
        state_name3a = "{}_no_effect_path".format(self.prefix)
        state_name4a = "{}_no_effect".format(self.prefix)
        state_name3b = "{}_effect_path".format(self.prefix)
        state_name4b = "{}_effect".format(self.prefix)

        trg2 = Trigger(state_name2)
        trg3a = Trigger(state_name3a)
        trg3b = Trigger(state_name3b)
        trg4a = Trigger(state_name4a)
        trg4b = Trigger(state_name4b)
        sm.add_transition(state_name1, state_name2, trg2)
        sm.add_transition(state_name2, state_name3a, trg3a)
        sm.add_transition(state_name2, state_name3b, trg3b)
        sm.add_transition(state_name3a, state_name4a, trg4a)
        sm.add_transition(state_name3b, state_name4b, trg4b)

        #
        trg2.set_event(self.ves["vac{}".format(self.vac_n)])

        # Random Event
        ev3_name = "{}_vac_branch".format(self.prefix)
        ev3 = RandomEvent(
            ev3_name,
            lambda current_time, parameter, sm_name=self.name, ev_name=ev3_name: self.parameter_model.branch_prob(
                sm_name, ev_name, current_time, parameter
            ),
            sm(state_name2),
        )
        ev3a = ev3.event("{}_no_effect_path".format(self.prefix))
        ev3b = ev3.event("{}_effect_path".format(self.prefix))
        trg3a.set_event(ev3a)
        trg3b.set_event(ev3b)

        # TimerEvent
        ev4a_name = "{}_no_effect".format(self.prefix)
        ev4a = TimerEvent(
            ev4a_name,
            start_state_or_event=sm(state_name3a),
            interval=lambda current_time, parameter, sm_name=self.name, ev_name=ev4a_name: self.parameter_model.timer_interval(
                sm_name, ev_name, current_time, parameter
            ),
        )
        trg4a.set_event(ev4a)

        # TimerEvent
        ev4b_name = "{}_effect".format(self.prefix)
        ev4b = TimerEvent(
            ev4b_name,
            start_state_or_event=sm(state_name3b),
            interval=lambda current_time, parameter, sm_name=self.name, ev_name=ev4b_name: self.parameter_model.timer_interval(
                sm_name, ev_name, current_time, parameter
            ),
        )
        trg4b.set_event(ev4b)

        return sm


class SickSumModel:
    """
    Summation of SickModels.

    SickModel uses following health parameters.
    - <sick_name>_val where <sick_name> is on sick_list.
    - <prefix>_status
    - <prefix>_value

    By default, <prefix>_value is the maximum value among <sick_name>_vals.

    Constructor options
    -------------------
    name : str
        name of state machine.
    prefix : str
        prefix of parameter.
    level_num : int
        maximum level of symptom.
    sick_list: list
        list of sick.
    ves : VirtualEventSet

    Examples
    --------
    >>> fever_level = ["no_fever", "subclinical", "fever"]
    >>> sick_list = ["cold", "c19", "vacadv"]
    >>> feversum_model = SickSumModel(
            "sm_feversum", "feversum", len(fever_level), sick_list, None
        )
    # example of set_calc_sick_value
    >>> fever_level = ["no_fever", "subclinical", "fever"]
    >>> sick_list = ["cold", "c19", "vacadv"]
    >>> feversum_model = SickSumModel(
            "sm_feversum", "feversum", len(fever_level), sick_list, None
        )
    >>> def calc_fever_value(parameter, sick_list):
            val = 0
            for sick_name in sick_list:
                sick_val = parameter.get("{}_val".format(sick_name))
                if sick_val is not None:
                    val += sick_val
            return val
    >>> feversum_model.set_calc_sick_value(calc_fever_value)
    >>> sm_feversum = feversum_model.make_state_machine()
    """

    def __init__(self, name, prefix, level_num, sick_list, ves):
        self.name = name
        self.prefix = prefix
        self.level_num = level_num
        self.sick_list = sick_list
        self.ves = ves
        self.calc_sick_value = self.calc_sick_max_value

    def calc_sick_max_value(self, parameter, sick_list):
        max_val = 0
        smpl_log.info("parameter={}, sick_list={}".format(parameter, sick_list))
        for sick_name in sick_list:
            sick_val = parameter.get("{}_val".format(sick_name))
            if sick_val is not None and sick_val > max_val:
                max_val = sick_val
        return max_val

    def set_calc_sick_value(self, calc_sick_value):
        self.calc_sick_value = calc_sick_value

    def make_state_machine(self):
        """
        Make a state machine.

        Returns:
            StateMachine : state machine of SickModel
        """
        sm = StateMachine(self.name)

        def set_parameter(prefix, state_name, val, current_time, parameter):
            parameter["{}_status".format(prefix)] = state_name
            parameter["{}_val".format(prefix)] = val

        for level in range(self.level_num):
            if level == 0:
                state_name1 = "start"
                state_name2 = "{}_{}".format(self.prefix, level)
                trg1a_name = "{}_up_to_{}".format(self.prefix, level)
                trg1a = Trigger(trg1a_name)
                sm.add_transition(state_name1, state_name2, trg1a)
                sm(state_name2).set_update_parameter_func(
                    lambda current_time, parameter, prefix=self.prefix, state_name=state_name2, val=level: set_parameter(
                        prefix, state_name, val, current_time, parameter
                    )
                )
                ev1a = ParameterEvent(
                    trg1a_name,
                    lambda parameter, level=-1: self.calc_sick_value(
                        parameter, self.sick_list
                    )
                    > level,
                )
                trg1a.set_event(ev1a)
            else:
                state_name1 = "{}_{}".format(self.prefix, level - 1)
                state_name2 = "{}_{}".format(self.prefix, level)
                trg1a_name = "{}_up_to_{}".format(self.prefix, level)
                trg1b_name = "{}_down_to_{}".format(self.prefix, level - 1)
                trg1a = Trigger(trg1a_name)
                trg1b = Trigger(trg1b_name)
                sm.add_transition(state_name1, state_name2, trg1a)
                sm.add_transition(state_name2, state_name1, trg1b)
                sm(state_name2).set_update_parameter_func(
                    lambda current_time, parameter, prefix=self.prefix, state_name=state_name2, val=level: set_parameter(
                        prefix, state_name, val, current_time, parameter
                    )
                )
                ev1a = ParameterEvent(
                    trg1a_name,
                    lambda parameter, level=level: self.calc_sick_value(
                        parameter, self.sick_list
                    )
                    >= level,
                )
                ev1b = ParameterEvent(
                    trg1b_name,
                    lambda parameter, level=level: self.calc_sick_value(
                        parameter, self.sick_list
                    )
                    < level,
                )
                trg1a.set_event(ev1a)
                trg1b.set_event(ev1b)

        return sm
