import copy
import datetime
from dateutil import relativedelta
import dill

from .common import NotifyCase
from .common import NotifyType
from .common import LogStore
from .common import LogStoreFlag
from .common import sim_log
from .common import tool_log
from .statemachine import State
from .event_base import EdgeOnceEvent, ResettableEvent
from .event_base import Event
from .event import ParameterUpdater
from .event import StochasticEvent
from .event import ParameterEvent
from .event import ScheduleEvent
from .event import DatetimeParam


class ReplayLogger:
    def __init__(self):
        self.sim = None
        self.replay_log = []
        self.is_replay = False
        self.log_index = 0

    def set_sim(self, sim):
        self.sim = sim

    def set_log(self):
        self.is_replay = False
        self.replay_log.clear()

    def set_replay(self):
        self.is_replay = True
        self.log_index = 0

    def save(self, filename):
        if self.sim is None:
            tool_log.warning("sim is not set")
        fout = open(filename, "wb")
        dill.dump([self.sim, self.replay_log], fout)
        fout.close()

    def load(self, filename):
        fin = open(filename, "rb")
        data = dill.load(fin)
        self.sim = data[0]
        self.replay_log = data[1]
        fin.close()
        self.set_replay()

    def set_parameter(self, src, dst):
        dst.update(src)

    def check_log(self, request_info, log_info1, log_info2):
        if log_info1 != request_info or log_info2 != request_info:
            raise ValueError(
                "ReplayLogger: request({}) doesn't match logs({},{})".format(
                    request_info, log_info1, log_info2
                )
            )

    def logging_parameter(self, log_target, func, current_time, parameter):
        if self.is_replay:
            sim_log.info(
                "current_time={}, logging_parameter replay, target={} ({})".format(
                    current_time, log_target.name, log_target
                )
            )
            current_log = self.replay_log[self.log_index]
            self.log_index = self.log_index + 1
            current_log_msg = self.replay_log[self.log_index]
            self.log_index = self.log_index + 1
            if isinstance(log_target, State):
                state = log_target
                state_name1 = current_log[0]
                state_name2 = current_log_msg[0]
                self.check_log(state.name, state_name1, state_name2)
            elif isinstance(log_target, Person):
                person = None  # dummy
                person_name1 = current_log[0]
                person_name2 = current_log_msg[0]
                self.check_log(person, person_name1, person_name2)
            elif isinstance(log_target, ParameterUpdater):
                parameter_updater = log_target
                parameter_updater_name1 = current_log[0]
                parameter_updater_name2 = current_log_msg[0]
                self.check_log(
                    parameter_updater.name,
                    parameter_updater_name1,
                    parameter_updater_name2,
                )
            log_parameter = current_log[1]
            self.set_parameter(log_parameter, parameter)
            log_msg = current_log_msg[1]
            return log_msg
        else:
            sim_log.info(
                "current_time={}, logging_parameter log, target={} ({})".format(
                    current_time, log_target.name, log_target
                )
            )
            event_log_msg = None
            if func is not None:
                event_log_msg = func(current_time, parameter)  # update parameter
            log_parameter = parameter
            if isinstance(log_target, State):
                state = log_target
                self.replay_log.append([state.name, copy.copy(log_parameter)])
                self.replay_log.append([state.name, copy.copy(event_log_msg)])
            elif isinstance(log_target, Person):
                person = None  # dummy
                self.replay_log.append([person, copy.copy(log_parameter)])
                self.replay_log.append([person, copy.copy(event_log_msg)])
            elif isinstance(log_target, ParameterUpdater):
                parameter_updater = log_target
                self.replay_log.append(
                    [parameter_updater.name, copy.copy(log_parameter)]
                )
                self.replay_log.append(
                    [parameter_updater.name, copy.copy(event_log_msg)]
                )
            return event_log_msg

    def logging_function(self, event, func, *args):
        if self.is_replay:
            sim_log.info(
                "logging_function replay, event={} ({})".format(event.name, event)
            )
            current_log = self.replay_log[self.log_index]
            event_name = current_log[0]
            if event_name != event.name:
                raise ValueError(
                    "ReplayLogger: request({}) doesn't match logs({})".format(
                        event.name, event_name
                    )
                )
            log_parameter = current_log[1]
            self.log_index = self.log_index + 1
            return log_parameter
        else:
            sim_log.info(
                "logging_function log, event={} ({})".format(event.name, event)
            )
            if func is None:
                log_parameter = args[0]
                self.replay_log.append([event.name, copy.copy(log_parameter)])
                return log_parameter
            else:
                log_parameter = func(*args)
                self.replay_log.append([event.name, copy.copy(log_parameter)])
                return log_parameter


class Person:
    """
    Object of simulation. Person has state machines, health parameter,
    parameter updaters and event log.

    Constructor options
    -------------------
    name : str
        name of person.
    state_machines : list
        list of StateMachine.
    parameter_updaters: list
        list of ParameterUpdater.
    health_parameter : dict
        parameter of person.

    Examples
    --------
    >>> state_machines = make_statemachines()
    >>> pu = ParameterUpdater(
            "updater",
            time_and_parameters,
        )
    >>> parameter_updaters = [pu]
    >>> health_parameter = {"status": "normal"}
    >>> person = Person(
            "name1",
            state_machines,
            parameter_updaters,
            health_parameter,
        )
    """

    def __init__(
        self,
        name,
        state_machines,
        parameter_updaters,
        health_parameter,
    ):
        self.name = name
        self.state_machines = state_machines
        self.parameter_updaters = parameter_updaters
        self.health_parameter = health_parameter
        self.log_store = LogStore(state_machines, health_parameter)
        self.clear()
        self.current_time = None
        self.replay_logger = None
        self.arbitrators_dict = None

    def _set_replay_logger(
        self, replay_logger
    ):  # replay_logger must be set before init
        self.replay_logger = replay_logger
        for state_machine in self.state_machines:
            trigger_event_list = state_machine.get_trigger_event_list()
            for event in trigger_event_list:
                event._set_replay_logger(replay_logger)
            for _, state in state_machine.state_dict.items():
                state._set_replay_logger(replay_logger)
        for parameter_updater in self.parameter_updaters:
            parameter_updater._set_replay_logger(replay_logger)

    def _set_log_store(self):
        for state_machine in self.state_machines:
            trigger_event_list = state_machine.get_trigger_event_list()
            for event in trigger_event_list:
                event._set_log_store(self.log_store)
            for _, state in state_machine.state_dict.items():
                state._set_log_store(self.log_store)
        for parameter_updater in self.parameter_updaters:
            parameter_updater._set_log_store(self.log_store)

    def set_detail_logging_flag(self, detail_logging_flag):
        self.log_store.set_detail_logging_flag(detail_logging_flag)

    def set_arbitrators_dict(self, arbitrators_dict):
        self.arbitrators_dict = arbitrators_dict

    def clear(self):
        self.event_log = {}
        self.next_event_log = []
        self.raise_event = []
        self.change_state = []
        self.every_period_update_event_list = []
        self.loop_check_state = []
        self.state_machine_value_changed_event_list = []
        self.next_trigger = {}
        self.log_store.clear()
        for state_machine in self.state_machines:
            state_machine._init_state()
        self.parameter_events = []
        self.edge_once_events = []
        self.parameter_updated = False
        self.health_parameter_init = None

    def finish(self):
        pass

    def print_loop_info(self, state):
        for loop_state in self.loop_check_state:
            sim_log.info(
                "state machine is looping (state={}) {}".format(
                    state.name, loop_state.name
                )
            )

    def update_state_parameter_updater_change(self):
        for from_state in self.change_state:
            for _, info in from_state.parameter_updater_for_notify.items():
                parameter_updater = info[0]
                notify_case = info[1]
                if notify_case == NotifyCase.ACTIVATE:
                    sim_log.info(
                        "parameter updater {} is activated".format(
                            parameter_updater.name
                        )
                    )
                    parameter_updater._activate(self.current_time)
                elif notify_case == NotifyCase.DEACTIVATE:
                    sim_log.info(
                        "parameter updater {} is deactivated".format(
                            parameter_updater.name
                        )
                    )
                    parameter_updater._deactivate()

    def update_state_event_parameters_init(self):
        total_event_set = set()
        for state_machine in self.state_machines:
            trigger_event_list = state_machine.get_trigger_event_list()
            for event in trigger_event_list:
                event._get_node_event(total_event_set)
        for event in total_event_set:
            if (
                isinstance(event, ResettableEvent)
                and hasattr(event, "active")
                and hasattr(event, "start_state_or_event")
                and event.start_state_or_event is None
            ):
                event._update_event_parameter_change(
                    self.current_time, self.health_parameter
                )

    def update_state_event_parameters_stop(self):
        for from_state in self.change_state:
            for _, event in from_state.event_for_notify_stop.items():
                event._update_event_parameter_stop(
                    self.current_time, self.health_parameter
                )
        for from_event in self.raise_event:
            for _, event in from_event.event_for_notify_stop.items():
                event._update_event_parameter_stop(
                    self.current_time, self.health_parameter
                )

    def update_state_event_parameters_change(self):
        for from_state in self.change_state:
            for _, event in from_state.event_for_notify_change.items():
                event._update_event_parameter_change(
                    self.current_time, self.health_parameter
                )
        for from_event in self.raise_event:
            for _, event in from_event.event_for_notify_change.items():
                event._update_event_parameter_change(
                    self.current_time, self.health_parameter
                )
        for from_state in self.change_state:
            for (
                arbitrator_name,
                arbitrator_request,
            ) in from_state.arbitrator_for_notify.items():
                arbitrator = self.arbitrators_dict[arbitrator_name]
                arbitrator.request(arbitrator_request, self)

    def update_state_event_parameters_next(self):
        for event in self.every_period_update_event_list:
            sim_log.info(
                "current_time={}, _update_event_parameter_next({})".format(
                    self.current_time, event.name
                )
            )
            event._update_event_parameter_next(
                self.current_time, self.health_parameter, next_time_step=True
            )

    def edge_once_event_reset(self):
        for edge_once_event in self.edge_once_events:
            edge_once_event._is_event_raise_main(
                self.current_time, self.health_parameter, None, False
            )

    def parameter_event_reset_if_changes(self, updated=False):
        if updated or self.parameter_updated:
            for parameter_event in self.parameter_events:
                parameter_event._reset_if_changes(
                    self.current_time, self.health_parameter
                )
        self.parameter_updated = False

    def update_state_parameters(self):
        self.next_event_log.clear()
        updated = False
        for from_state in self.change_state:
            log_msg, res = from_state._update_parameter(
                self.current_time, self.health_parameter
            )
            sim_log.info(
                "update_state_parameters: state={}, update result={} ".format(
                    from_state.name, res
                )
            )
            if res:
                updated = True
            if log_msg is not None:
                self.next_event_log.append(log_msg)
            self.log_store.update(self.current_time, LogStoreFlag.PARAMETER)
        if len(self.next_event_log) > 0:
            event_log = self.event_log.get(self.current_time)
            if event_log is None:
                self.event_log[self.current_time] = copy.copy(self.next_event_log)
            else:
                self.event_log[self.current_time].extend(copy.copy(self.next_event_log))
        self.parameter_event_reset_if_changes(updated)

    def fix_event_name(self):
        for state_machine in self.state_machines:
            trigger_event_list = state_machine.get_trigger_event_list()
            for event in trigger_event_list:
                event._fix_name()

    def init_event(self):
        total_event_set = set()
        for state_machine in self.state_machines:
            trigger_event_list = state_machine.get_trigger_event_list()
            for event in trigger_event_list:
                event._get_node_event(total_event_set)
            for event in trigger_event_list:
                event._fix_name()
            for event in trigger_event_list:
                event.check()
            for event in trigger_event_list:
                event._set_start_time(self.current_time)
                event._set_state_machine_list(self.state_machines)
            for _, state in state_machine.state_dict.items():
                state.event_for_notify.clear()
        for event in total_event_set:
            event._init()
        for event in total_event_set:
            if not isinstance(event, ResettableEvent):
                continue
            event_to_notify = event._get_event_to_notify()
            start_state_or_event = event_to_notify.start_state_or_event
            if isinstance(start_state_or_event, State):
                sim_log.debug(
                    "set_event_for_notify state({}) -> event({})".format(
                        start_state_or_event.name, event_to_notify.name
                    )
                )
                start_state_or_event._set_event_for_notify(
                    event_to_notify, type=event_to_notify.notify_type
                )
            stop_state_or_event = event_to_notify.stop_state_or_event
            if isinstance(stop_state_or_event, State):
                sim_log.debug(
                    "set_event_for_notify state({}) -> event({})".format(
                        stop_state_or_event.name, event_to_notify.name
                    )
                )
                stop_state_or_event._set_event_for_notify(
                    event_to_notify, type=NotifyType.STOP_ON_CHANGE_STATE
                )
        for event in total_event_set:
            event.event_for_notify_change.clear()
            event.event_for_notify_stop.clear()
        for event in total_event_set:
            if not isinstance(event, ResettableEvent):
                continue
            event_to_notify = event._get_event_to_notify()
            start_state_or_event = event_to_notify.start_state_or_event
            if isinstance(start_state_or_event, Event):
                from_event = start_state_or_event
                sim_log.debug(
                    "set_event_for_notify_change event({}) -> event({})".format(
                        from_event.name, event_to_notify.name
                    )
                )
                from_event._set_event_for_notify_change(event_to_notify)
            stop_state_or_event = event_to_notify.stop_state_or_event
            if isinstance(stop_state_or_event, Event):
                from_event = stop_state_or_event
                sim_log.debug(
                    "set_event_for_notify_change event({}) -> event({})".format(
                        from_event.name, event_to_notify.name
                    )
                )
                from_event._set_event_for_notify_stop(event_to_notify)
        for event in total_event_set:
            if isinstance(event, StochasticEvent):
                sim_log.debug(
                    "every_period_update_event_list append StochasticEvent({})".format(
                        event.name
                    )
                )
                self.every_period_update_event_list.append(event)
            if isinstance(event, ParameterEvent):
                sim_log.debug(
                    "parameter_events append ParameterEvent({})".format(event.name)
                )
                self.parameter_events.append(event)
            if isinstance(event, EdgeOnceEvent):
                sim_log.debug(
                    "edge_once_events append EdgeOnceEvent({})".format(event.name)
                )
                self.edge_once_events.append(event)

    def init_parameter_updater(self, current_time):
        for parameter_updater in self.parameter_updaters:
            parameter_updater._init(current_time)
        for parameter_updater in self.parameter_updaters:
            states_for_activate = parameter_updater.states_for_activate
            if isinstance(states_for_activate, list):
                for state_for_activate in states_for_activate:
                    if not isinstance(state_for_activate, State):
                        continue
                    sim_log.info(
                        "set_parameter_updater_for_notify activate state({}) -> parameter updater({})".format(
                            state_for_activate.name, parameter_updater.name
                        )
                    )
                    state_for_activate._set_parameter_updater_for_notify(
                        parameter_updater, NotifyCase.ACTIVATE
                    )
            states_for_deactivate = parameter_updater.states_for_deactivate
            if isinstance(states_for_deactivate, list):
                for state_for_deactivate in states_for_deactivate:
                    if not isinstance(state_for_deactivate, State):
                        continue
                    sim_log.info(
                        "set_parameter_updater_for_notify deactivate state({}) -> parameter updater({})".format(
                            state_for_deactivate.name, parameter_updater.name
                        )
                    )
                    state_for_deactivate._set_parameter_updater_for_notify(
                        parameter_updater, NotifyCase.DEACTIVATE
                    )

    def _init(self, start_time):
        self.current_time = start_time
        self.health_parameter_init = copy.copy(self.health_parameter)
        if self.replay_logger is not None:
            self.replay_logger.logging_parameter(
                self,
                None,
                self.current_time,
                self.health_parameter,
            )
        for state_machine in self.state_machines:
            state_machine._set_trigger_dict()
        self.init_event()
        self.init_parameter_updater(self.current_time)
        for state_machine in self.state_machines:
            state_name = state_machine.current_state_name
            state = state_machine.state_dict[state_name]
            state.last_trans_time = self.current_time
            self.change_state.append(state)
        self.update_state_parameter_updater_change()
        self._update_parameter()
        self.update_state_parameters()
        self.update_state_event_parameters_init()
        self.update_state_event_parameters_change()
        self.update_state_event_parameters_next()
        self._set_log_store()
        self.log_store.update(
            self.current_time, LogStoreFlag.INIT
        )  # log state and parameter
        for state_machine_i, state_machine in enumerate(self.state_machines):
            trigger_event_list = state_machine.get_trigger_event_list()
            for event_i, event in enumerate(trigger_event_list):
                append_flag = (
                    state_machine_i == len(self.state_machines) - 1
                    and event_i == len(trigger_event_list) - 1
                )
                self.log_store.update_detail_event(
                    self.current_time, event, None, append_flag
                )
        # initialize variables used for updating state machine
        self.raise_event.clear()
        self.change_state.clear()
        self.next_trigger.clear()

    def _init_state_machine_value(self):
        for event in self.state_machine_value_changed_event_list:
            event._init_state_machine_value()
        self.state_machine_value_changed_event_list.clear()

    def update_event(self, state_machine):
        state_name_before = state_machine.current_state_name
        state_before = state_machine.state_dict[state_name_before]
        event = state_machine.reset_event
        if (
            event is not None
            and state_name_before != "start"
            and state_name_before != "drop"
        ):
            if event._is_event_raise(
                self.current_time, self.health_parameter, state_machine
            ):
                trigger_name = "reset"
                sim_log.info(
                    "current_time={}, trigger name={}, statemachine name={}, current_state={}".format(
                        self.current_time,
                        trigger_name,
                        state_machine.name,
                        state_machine.current_state_name,
                    )
                )
                self.next_event_log.append(event.event_log_name)
                if self.next_trigger.get(trigger_name) is None:
                    self.next_trigger[trigger_name] = [state_machine]
                else:
                    self.next_trigger[trigger_name].append(state_machine)
                self.raise_event.append(event)
        event = state_machine.drop_event
        if event is not None and state_name_before != "drop":
            if event._is_event_raise(
                self.current_time, self.health_parameter, state_machine
            ):
                trigger_name = "drop"
                sim_log.info(
                    "current_time={}, trigger name={}, statemachine name={}, current_state={}".format(
                        self.current_time,
                        trigger_name,
                        state_machine.name,
                        state_machine.current_state_name,
                    )
                )
                self.next_event_log.append(event.event_log_name)
                if self.next_trigger.get(trigger_name) is None:
                    self.next_trigger[trigger_name] = [state_machine]
                else:
                    self.next_trigger[trigger_name].append(state_machine)
                self.raise_event.append(event)
        for _, trigger in state_before.next.items():
            if not hasattr(trigger, "event"):
                continue
            event = trigger.event
            if event._is_event_raise(
                self.current_time, self.health_parameter, state_machine
            ):
                sim_log.info(
                    "current_time={}, trigger name={}, statemachine name={}, current_state={}".format(
                        self.current_time,
                        trigger.name,
                        state_machine.name,
                        state_machine.current_state_name,
                    )
                )
                self.next_event_log.append(event.event_log_name)
                if self.next_trigger.get(trigger.name) is None:
                    self.next_trigger[trigger.name] = [state_machine]
                else:
                    self.next_trigger[trigger.name].append(state_machine)
                self.raise_event.append(event)

    def update_events(self):
        self.next_trigger.clear()
        self.next_event_log.clear()
        for state_machine in self.state_machines:
            self.update_event(state_machine)
        if len(self.next_event_log) > 0:
            event_log = self.event_log.get(self.current_time)
            if event_log is None:
                self.event_log[self.current_time] = copy.copy(self.next_event_log)
            else:
                self.event_log[self.current_time].extend(copy.copy(self.next_event_log))

    def update_state_machine(self, state_machine, next_trigger):
        is_change = False
        state_name_before = state_machine.current_state_name
        next_trigger_statemachine_list = []
        next_trigger_list = []
        for (
            trigger_name,
            trigger_state_machine_list,
        ) in next_trigger.items():
            for trigger_state_machine in trigger_state_machine_list:
                # for debug
                next_trigger_statemachine_list.append(trigger_state_machine.name)
            if state_machine in trigger_state_machine_list:
                next_trigger_list.append(trigger_name)

        if len(next_trigger_list) > 1:
            sim_log.warning(
                "current_time={}, state_machine_name={}, multiple trigger={}".format(
                    self.current_time, state_machine.name, next_trigger_list
                )
            )
            sim_log.warning(
                "multiple trigger: event_log={}".format(self.event_log),
            )
            raise ValueError("multiple trigger")

        if len(next_trigger_list) >= 1:
            trigger_name = next_trigger_list[0]
            # transition
            if state_machine._next_state(trigger_name):
                state = state_machine.state_dict[state_machine.current_state_name]
                trigger = state_machine.get_trigger(trigger_name)
                trigger.event._update_state_machine_value(
                    self.current_time, self.health_parameter, state_machine, True
                )
                self.state_machine_value_changed_event_list.append(trigger.event)
                state.last_trans_time = self.current_time
                is_change = True  # state change
                self.change_state.append(state)
                if state in self.loop_check_state:
                    self.print_loop_info(state)
                    raise ValueError(
                        "state machine is looping (state={})".format(state.name)
                    )
                self.loop_check_state.append(state)
                state_name_after = state_machine.current_state_name
                sim_log.debug(
                    "current_time={}, state_machine_name={}, next_trigger[{}]={}, state_name_before={}, state_name_after={}".format(
                        self.current_time,
                        state_machine.name,
                        trigger_name,
                        next_trigger_statemachine_list,
                        state_name_before,
                        state_name_after,
                    )
                )
                self.log_store.update(
                    self.current_time, LogStoreFlag.STATE
                )  # log state
        return is_change

    def update_state_machines(self):
        is_change = False
        self.update_events()
        for state_machine in self.state_machines:
            if self.update_state_machine(state_machine, self.next_trigger):
                is_change = True  # state change
        self.update_state_parameter_updater_change()
        self.update_state_parameters()
        self.update_state_event_parameters_stop()
        self.update_state_event_parameters_change()
        # initialize variables used for updating state machine
        self.raise_event.clear()
        self.change_state.clear()
        self.next_trigger.clear()
        return is_change

    def _update_parameter(self):
        updated = False
        for parameter_updater in self.parameter_updaters:
            if parameter_updater._update_parameter(
                self.current_time, self.health_parameter
            ):
                updated = True
        if updated:
            self.parameter_updated = True

    def update(self, next_time):
        self.edge_once_event_reset()
        self._update_parameter()
        self.parameter_event_reset_if_changes()
        self._init_state_machine_value()
        # clear loop info
        self.loop_check_state.clear()
        while self.update_state_machines():
            pass
        self.update_state_event_parameters_next()

    def get_next_time_of_raise_event(self):
        def calc_next_time(next_time, next_time_total):
            if isinstance(next_time, datetime.datetime):
                if next_time < self.current_time:
                    raise ValueError("next_time must be < current_time")
                if next_time_total is None or next_time < next_time_total:
                    return next_time
            return next_time_total

        next_time_total = None
        for state_machine in self.state_machines:
            trigger_event_list = state_machine._get_next_trigger_event_list()
            for event in trigger_event_list:
                next_time = event._get_event_raise_time(
                    self.current_time, self.health_parameter, state_machine
                )
                sim_log.debug("event({}), next_time={}".format(event.name, next_time))
                next_time_total = calc_next_time(next_time, next_time_total)
        sim_log.debug("next_time_total={} (state machine)".format(next_time_total))

        for event in self.every_period_update_event_list:
            next_time = event._get_event_raise_time(
                self.current_time, self.health_parameter, state_machine
            )
            sim_log.info(
                "event = {}, next_time = {}, active = {}".format(
                    event.name, next_time, event.active
                )
            )
            next_time_total = calc_next_time(next_time, next_time_total)
        sim_log.debug("next_time_total={} (event)".format(next_time_total))

        for parameter_updater in self.parameter_updaters:
            next_time = parameter_updater._get_update_time(self.current_time)
            next_time_total = calc_next_time(next_time, next_time_total)
        sim_log.debug("next_time_total={} (parameter updater)".format(next_time_total))

        return next_time_total

    def goto_next_time_period(self, next_time):
        self.current_time = next_time

    def save(self, filename):
        fout = open(filename, "wb")
        dill.dump(self, fout)
        fout.close()

    def load(self, filename):
        fin = open(filename, "rb")
        person = dill.load(fin)
        fin.close()
        return person


class ArbitratorRequest:
    """
    Request sent to Arbitrator by State.
    Arbitrator reads messages from ArbitratorRequests,
    selects and raises events speficied by ArbitratorRequests.

    Constructor options
    -------------------
    name : str
        name of arbitrator request.
    arbitrator_name : str
        name of arbitrator.
    message: str
        message to arbitrator.
    event : dict
        event raised by arbitrator.

    Examples
    --------
    >>> req_vac1 = ArbitratorRequest("req_vac1", "VACCenter1", "req_vac1", ev_vac1)
    >>> sm("step1").set_arbitrator_for_notify(req_vac1)
    """

    def __init__(self, name, arbitrator_name, message, event):
        self.name = name
        self.arbitrator_name = arbitrator_name
        self.message = message
        self.set_event(event)
        self.person = None

    def set_person(self, person):
        self.person = person

    def set_schedule_event_time(self, current_time, time):
        if self.schedule_event is None:
            return
        self.schedule_event._set_time(current_time, time)

    def set_event(self, event):
        if hasattr(event, "_add_arbitrator_for_set_event"):
            # for virtual event
            event._add_arbitrator_for_set_event(self)
            self.schedule_event = event
            return
        if not isinstance(event, ScheduleEvent):
            raise ValueError("class is not {}".format(ScheduleEvent.__name__))
        self.schedule_event = event


class PeriodicTimeTable:
    def __init__(self, offset, interval):
        self.offset = offset
        self.interval = interval

    def _init(self):
        self.next_time = None

    def _calc_update_time(self, current_time, active, start_time, last_time):
        if self.next_time is None:
            self.next_time = start_time + self.offset
        if self.next_time > current_time:
            return self.next_time
        if self.next_time == current_time:
            if last_time == current_time:
                self.next_time = self.next_time + self.interval
                return self.next_time
            else:
                return self.next_time
        if self.next_time < current_time:
            self.next_time = self.next_time + self.interval
            return self.next_time


class Arbitrator:
    """
    Arbitrator of requests from Persons.
    Arbitrator processes following tasks every specified time period.
    - reads messages from ArbitratorRequests.
    - selects events and raises events speficied by ArbitratorRequests.

    Time period must be set in one of following two ways.
    - offset and interval
    - timetable

    Constructor options
    -------------------
    name : str
        name of arbitrator.
    arbitrator_func : callable
        function for selecting events.
    offset: str
        off set of time period.
    interval : dict
        interval of time period.
    timetable :
        dict : for example,
            {
                "2021-06-01 00:00:00": None,
                "2021-06-10 00:00:00": None,
            }

    Examples
    --------
    >>> def vac1_wait_time_func(current_time, requests_list, results_dict, statistics):
            for request in requests_list:
                req_person = request.person
                vac1_wait_time = arb_parameters[req_person.name] * 24
                results_dict[request] = current_time + datetime.timedelta(
                    hours=vac1_wait_time
                )
    >>> VACCenter1 = Arbitrator(
            "VACCenter1",
            vac1_wait_time_func,
            offset=datetime.timedelta(hours=8),  # offset (at 8 a.m.)
            interval=datetime.timedelta(hours=24),  # interval (daily)
        )
    >>> req_vac1 = ArbitratorRequest("req_vac1", "VACCenter1", "req_vac1", ev_vac1)
    >>> sm("step1").set_arbitrator_for_notify(req_vac1)
    """

    def __init__(
        self, name, arbitrator_func, offset=None, interval=None, timetable=None
    ):
        self.name = name
        self.arbitrator_func = arbitrator_func
        datetime_param = DatetimeParam()
        if datetime_param.read_timetable(timetable):
            self.time_param = datetime_param
        elif offset is not None and interval is not None:
            self.time_param = PeriodicTimeTable(offset, interval)
        else:
            raise ValueError("timetable or (offset, interval) must be set")
        self.requests_list = []
        self.clear()
        self.statistics_data = dict()
        self.statistics = dict()
        self.results_dict = dict()
        self.replay_logger = None

    def _self_set_replay_logger(self, replay_logger):
        self.replay_logger = replay_logger

    def clear(self):
        self.start_time = None
        self.current_time = None
        self.finished = False
        self.last_arbitrate_time = None
        self.next_arbitrate_time = None
        self.requests_list.clear()

    def _init(self, start_time):
        self.clear()
        self.start_time = start_time
        self.current_time = start_time
        self.time_param._init()

    def get_next_time_of_raise_event(self):
        if self.finished == True:
            return None
        if (
            self.next_arbitrate_time is not None
            and self.current_time < self.next_arbitrate_time
        ):
            return self.next_arbitrate_time
        # calculate next_arbitrate_time
        if self.replay_logger is None:
            self.next_arbitrate_time = self.time_param._calc_update_time(
                self.current_time, True, self.start_time, self.last_arbitrate_time
            )
        else:
            sim_log.info(
                "current_time={}, ParameterUpdater, logging_function".format(
                    self.current_time
                )
            )
            self.next_arbitrate_time = self.replay_logger.logging_function(
                self,
                self.time_param._calc_update_time,
                self.current_time,
                True,
                self.start_time,
                self.last_arbitrate_time,
            )
        if self.next_arbitrate_time is None:
            self.finished = True

        sim_log.info("next_arbitrate_time={}".format(self.next_arbitrate_time))
        return self.next_arbitrate_time

    def is_arbitrate_raise(self, current_time):
        if self.finished == True:
            return False
        if self.next_arbitrate_time is None:
            self.get_next_time_of_raise_event()
        if current_time >= self.next_arbitrate_time:
            if self.last_arbitrate_time == current_time:
                return False
            else:
                self.last_arbitrate_time = current_time
                return True
        else:
            return False

    def update_statistics(self, current_time):
        # update statistics daily
        stat_start_time = current_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cases = 0
        for stat_date, stat_case in self.statistics_data.items():
            if stat_date >= stat_start_time:
                cases += stat_case
        self.statistics["daily"] = cases
        # update statistics weekly
        stat_start_time = stat_start_time + relativedelta.relativedelta(weeks=-1)
        cases = 0
        for stat_date, stat_case in self.statistics_data.items():
            if stat_date >= stat_start_time:
                cases += stat_case
        self.statistics["weekly"] = cases
        # update statistics monthly
        stat_start_time = stat_start_time + relativedelta.relativedelta(months=-1)
        cases = 0
        for stat_date, stat_case in self.statistics_data.items():
            if stat_date >= stat_start_time:
                cases += stat_case
        self.statistics["monthly"] = cases

    def update_statistics_data(self, current_time, cases):
        current_cases = self.statistics_data.get(current_time)
        current_cases = cases + current_cases if current_cases is not None else cases
        self.statistics_data[current_time] = current_cases

    def arbitrator_process(self, current_time, requests_list):
        # clear
        self.results_dict.clear()
        # update result
        self.update_statistics(current_time)
        self.arbitrator_func(
            current_time, requests_list, self.results_dict, self.statistics
        )
        # make result list
        for request in list(self.results_dict.keys()):
            self.results_dict[requests_list.index(request)] = self.results_dict.pop(
                request
            )
        # update statistics
        self.update_statistics_data(current_time, len(self.results_dict))
        return self.results_dict

    def update(self, next_time, change_person_set):
        if not self.is_arbitrate_raise(self.current_time):
            return False
        sim_log.debug("arbitrator({}) raise at {}".format(self.name, self.current_time))
        # get results from arbitrator_process
        if self.replay_logger is None:
            self.results_dict = self.arbitrator_process(
                self.current_time, self.requests_list
            )
        else:
            self.results_dict = self.replay_logger.logging_function(
                self, self.arbitrator_process, self.current_time, self.requests_list
            )
        # set SchedulerEvent
        is_change = False
        request_delete_list = []
        for index, result in self.results_dict.items():
            request = self.requests_list[index]
            request_delete_list.append(request)
            request.set_schedule_event_time(self.current_time, result)
            change_person_set.add(request.person)
            is_change = True  # event parameter updated
        # update request_list
        for request in request_delete_list:
            self.requests_list.remove(request)
        return is_change

    def goto_next_time_period(self, next_time):
        self.current_time = next_time

    def request(self, arbitrator_request, person):
        arbitrator_request.set_person(person)
        self.requests_list.append(arbitrator_request)


class Simulation:
    """
    Simulation of Persons and Arbitrators.
    Simulation uses following configurations.
    - start_time
    - end_time
    - Persons
    - Arbitrators (optional)

    Constructor options
    -------------------
    start_time : datetime
        start time of simulation.
    end_time : datetime
        end time of simulation.

    Examples
    --------
    >>> parameter_updaters = [pu]
        health_parameter = {}
        person = Person(
            "template",
            state_machines,
            parameter_updaters,
            health_parameter,
        )
    >>> start_time = datetime.datetime.strptime(
            "2021-06-01 00:00:00", "%Y-%m-%d %H:%M:%S"
        )
    >>> end_time = datetime.datetime.strptime(
            "2021-09-01 00:00:00", "%Y-%m-%d %H:%M:%S"
        )
    >>> sim = Simulation(start_time, end_time)
    >>> sim.add_person(person)
    """

    def __init__(self, start_time, end_time):
        self.population = []  # list of Person
        self.arbitrators = []  # list of Arbitrator
        self.arbitrators_dict = {}
        self.start_time = start_time
        self.end_time = end_time
        self.current_time = copy.copy(self.start_time)
        self.replay_logger = None
        self.next_time_dict = dict()

    def add_person(self, person):
        """
        add person to list.

        Constructor options
        -------------------
        person : Person

        Examples
        --------
        >>> sim = Simulation(start_time, end_time)
        >>> sim.add_person(person)
        """

        # duplication unchecked
        self.population.append(person)

    def add_arbitrator(self, arbitrator):
        """
        add arbitrator to list.

        Constructor options
        -------------------
        arbitrator : Arbitrator

        Examples
        --------
        >>> VACCenter1 = Arbitrator(
            "VACCenter1",
            vac1_wait_time_func,
            offset=datetime.timedelta(hours=8),  # offset (at 8 a.m.)
            interval=datetime.timedelta(hours=24),  # interval (daily)
        )
        >>> sim = Simulation(start_time, end_time)
        >>> sim.add_arbitrator(VACCenter1)
        """

        # duplication unchecked
        self.arbitrators.append(arbitrator)

    def set_replay_logger(
        self,
    ):  # replay_logger must be set after add_person and add_arbitrator before init of Simulation
        if self.replay_logger is None:
            self.replay_logger = ReplayLogger()
        self.replay_logger.set_sim(self)
        for person in self.population:
            person._set_replay_logger(self.replay_logger)
        for arbitrator in self.arbitrators:
            arbitrator._self_set_replay_logger(self.replay_logger)

    def set_replay_logger_log(self):
        if self.replay_logger is None:
            raise ValueError("replay_logger is not set")
        self.replay_logger.set_log()

    def set_replay_logger_replay(self):
        if self.replay_logger is None:
            raise ValueError("replay_logger is not set")
        self.replay_logger.set_replay()

    def load_replay_logger(
        self, filename
    ):  # replay_logger must be loaded before simulation starts
        if self.replay_logger is None:
            raise ValueError("replay_logger is not set")
        # load replay info and switch to replay mode
        self.replay_logger.load(filename)

    def save_replay_logger(self, filename):
        if self.replay_logger is None:
            raise ValueError("replay_logger is not set")
        self.replay_logger.save(filename)

    def set_detail_logging_flag(self, flag):
        for person in self.population:
            person.set_detail_logging_flag(flag)

    def get_person_event_data_list(self):
        person_event_data_list = []
        for person in self.population:
            person_event_data = {
                "event_data": copy.copy(person.event_log),
                "health_parameter_init": copy.copy(person.health_parameter_init),
                "health_parameter_last": copy.copy(person.health_parameter),
                "person_data": {
                    "name": person.name,
                    "sim_start_time": copy.copy(self.start_time),
                    "sim_end_time": copy.copy(self.end_time),
                },
            }
            person_event_data_list.append(person_event_data)
        return person_event_data_list

    def fix_event_name(self):
        for person in self.population:
            person.fix_event_name()

    def init(self):
        # replay_logger doesn't load start_time and end_time
        self.current_time = copy.copy(self.start_time)
        self.arbitrators_dict.clear()
        for arbitrator in self.arbitrators:
            self.arbitrators_dict[arbitrator.name] = arbitrator
        for person in self.population:
            person.clear()
            person._init(self.start_time)
            person.set_arbitrators_dict(self.arbitrators_dict)
        for arbitrator in self.arbitrators:
            arbitrator.clear()
            arbitrator._init(self.start_time)

    def _get_next_time(self):
        def calc_next_time(next_time, next_time_total):
            if isinstance(next_time, datetime.datetime):
                if next_time < self.current_time:
                    raise ValueError("next_time must be < current_time")
                if next_time_total is None or next_time < next_time_total:
                    return next_time
            return next_time_total

        next_time_total = None
        for person in self.population:
            if self.next_time_dict[person] == "update":
                next_time = person.get_next_time_of_raise_event()
                self.next_time_dict[person] = next_time
            else:
                next_time = self.next_time_dict[person]
            next_time_total = calc_next_time(next_time, next_time_total)

        for arbitrator in self.arbitrators:
            next_time = arbitrator.get_next_time_of_raise_event()
            self.next_time_dict[arbitrator] = next_time
            next_time_total = calc_next_time(next_time, next_time_total)

        return next_time_total

    def _run_time_period(self, person_update_set):
        tmp_person_update_set = set()
        tmp_person_update_set.update(person_update_set)
        new_person_update_set = set()
        while True:
            for person in tmp_person_update_set:
                person.goto_next_time_period(self.current_time)
                person.update(self.current_time)
                self.next_time_dict[person] = "update"
            tmp_person_update_set.clear()
            is_change = False
            for arbitrator in self.arbitrators:
                new_person_update_set.clear()
                arbitrator.goto_next_time_period(self.current_time)
                if arbitrator.update(self.current_time, new_person_update_set):
                    is_change = True
                    sim_log.debug(
                        "current_time={}, change_person_set={}".format(
                            self.current_time, new_person_update_set
                        )
                    )
                    tmp_person_update_set.update(new_person_update_set)
            if not is_change:
                break

    def run_simulation(self):  # run simulation after init
        tmp_person_update_set = set()
        tmp_person_update_set.update(self.population)
        while True:
            self._run_time_period(tmp_person_update_set)
            next_time = self._get_next_time()
            # termination
            if next_time is None:
                break
            if next_time > self.end_time:
                break
            # next time
            self.current_time = next_time
            tmp_person_update_set.clear()
            for person in self.population:
                if self.next_time_dict[person] == self.current_time:
                    tmp_person_update_set.add(person)
        # finish
        for person in self.population:
            person.finish()
