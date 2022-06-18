import copy

from .common import EventType
from .common import EventTriggerType
from .common import NotifyType
from .common import sim_log
from .common import LogStoreFlag


class State:
    def __init__(self, name):
        self.next = dict()
        self.trigger_to_next = dict()
        self.name = name
        self.trigger_history = ""
        self.event_for_notify_change = dict()
        self.event_for_notify_stop = dict()
        self.event_for_notify = dict()
        self.arbitrator_for_notify = dict()
        self.parameter_updater_for_notify = dict()
        self.update_parameter_func_list = []
        self.replay_logger = None
        self.log_store = None
        self.last_trans_time = None

    def _set_replay_logger(self, replay_logger):
        self.replay_logger = replay_logger

    def _set_log_store(self, log_store):
        self.log_store = log_store

    def _exists_next(self, trigger):
        return trigger in self.next.values()

    def _set_state_machine(self, state_machine):
        self.state_machine = state_machine

    def _get_current_state(self):
        return self.name == self.state_machine.current_state_name

    def _get_next_name(self, trigger_name):
        return self.trigger_to_next.get(trigger_name)  # state name

    def _set_next(self, name, trigger):
        if trigger in self.next.values():
            raise ValueError(
                "State({}) has multiple triggers({}) which have the same transition state".format(
                    self.name, trigger.name
                )
            )
        self.next[name] = trigger
        self.trigger_to_next[trigger.name] = name

    def _discard_next(self, name):
        if name in self.next:
            trigger = self.next[name]
            del self.next[name]
            del self.trigger_to_next[trigger.name]

    def _init_event_for_notify(self):
        self.event_for_notify_change.clear()
        self.event_for_notify_stop.clear()
        self.event_for_notify.clear()

    def _set_event_for_notify(self, event, type=NotifyType.NEXT_TIME_STEP):
        if type == NotifyType.CHANGE_STATE:
            self.event_for_notify_change[event.name] = event
            return
        if type == NotifyType.STOP_ON_CHANGE_STATE:
            self.event_for_notify_stop[event.name] = event
            return
        if type == NotifyType.NEXT_TIME_STEP:
            self.event_for_notify_change[event.name] = event
            self.event_for_notify[event.name] = event
            return

    def _init_arbitrator_for_notify(self):
        self.arbitrator_for_notify.clear()

    def set_arbitrator_for_notify(self, arbitrator_request):
        self.arbitrator_for_notify[
            arbitrator_request.arbitrator_name
        ] = arbitrator_request

    def _init_parameter_updater_for_notify(self):
        self.parameter_updater_for_notify.clear()

    def _set_parameter_updater_for_notify(self, parameter_updater, notify_case):
        self.parameter_updater_for_notify[parameter_updater.name] = [
            parameter_updater,
            notify_case,
        ]
        sim_log.info(self.parameter_updater_for_notify)

    def _do_update_parameter_func(self, current_time, parameter):
        event_log_desc_last = None
        for update_parameter_func in self.update_parameter_func_list:
            event_log_desc = update_parameter_func(current_time, parameter)
            if event_log_desc is not None:
                event_log_desc_last = event_log_desc
        return event_log_desc_last

    def set_update_parameter_func(self, update_parameter_func, index=None):
        if index is None:
            self.update_parameter_func_list.append(update_parameter_func)
        else:
            self.update_parameter_func_list[index] = update_parameter_func

    def _update_parameter(self, current_time, parameter):
        if len(self.update_parameter_func_list) > 0:
            if self.replay_logger is None:
                event_log_desc = self._do_update_parameter_func(current_time, parameter)
                if self.log_store is not None:
                    self.log_store.update_detail(
                        current_time, LogStoreFlag.PARAMETER, copy.copy(parameter)
                    )
                return event_log_desc, True
            else:
                event_log_desc = self.replay_logger.logging_parameter(
                    self, self._do_update_parameter_func, current_time, parameter
                )
                if self.log_store is not None:
                    self.log_store.update_detail(
                        current_time, LogStoreFlag.PARAMETER, copy.copy(parameter)
                    )
                return event_log_desc, True
        return None, False


class Trigger:
    """
    Represent a transition from a state to other state.

    Constructor options
    -------------------
    name : str
        name of trigger. the name must be unique in each state machine.

    Examples
    --------
    >>> sm = StateMachine("statemachine1")
    # add transition
    >>> trg1 = Trigger("trigger1")
    >>> sm.add_transition("state1", "state2", trg1)
    # get state
    >>> state1 = sm("state1")
    """

    def __init__(self, name):
        self.name = name

    def set_event(self, event):
        """
        Set an event associated to trigger.

        Parameters
        ----------
        event : Event
            event associated to trigger

        Returns
        -------
            None
        """
        if hasattr(event, "_add_trigger_for_set_event"):
            # virtual event
            event._add_trigger_for_set_event(self)
            self.event = event
        else:
            self.event = event


class StateMachine:
    """
    Stete machine including "start" state and "drop" state.
    A transition from a state to other state is represented by Trigger.

    Constructor options
    -------------------
    name : str
        name of state machine

    Examples
    --------
    >>> sm = StateMachine("statemachine1")
    # add transition
    >>> trg1 = Trigger("trigger1")
    >>> sm.add_transition("state1", "state2", trg1)
    # get state
    >>> state1 = sm("state1")
    """

    def __init__(self, name=None):
        self.name = name
        self.state_dict = dict()
        self.trigger_dict = dict()
        self.current_state_name = "start"
        self._add_state_if_not_exist("start")
        self._add_state_if_not_exist("drop")
        self.reset_event = None
        self.drop_event = None

    def add_transition(self, name_from, name_to, trigger_or_trigger_name):
        """
        Add transition from a state to other state.

        Parameters
        ----------
        name_from : str
            name of a state which the transition starts
        name_to : str
            name of a state which the transition ends
        trigger_or_trigger_name : Trigger or str
            trigger representing the transition or
            name of trigger representing the transition

        Returns
        -------
            None (if trigger_or_trigger_name is Trigger)
            or Trigger (if trigger_or_trigger_name is str)
        """
        if isinstance(trigger_or_trigger_name, Trigger):
            trigger = trigger_or_trigger_name
            self._add_state_if_not_exist(name_from)
            self._add_state_if_not_exist(name_to)
            self.trigger_dict[trigger.name] = trigger
            state_from = self.state_dict[name_from]
            state_from._set_next(name_to, trigger)
        if type(trigger_or_trigger_name) is str:
            trigger_name = trigger_or_trigger_name
            trigger = Trigger(trigger_name)
            self._add_state_if_not_exist(name_from)
            self._add_state_if_not_exist(name_to)
            self.trigger_dict[trigger.name] = trigger
            state_from = self.state_dict[name_from]
            state_from._set_next(name_to, trigger)
            return trigger

    def set_reset_event(self, reset_event):
        """
        Set the reset event which causes the reset trigger.
        The reset trigger moves the current state to "start" state.

        Parameters
        ----------
        reset_event : Event

        Returns
        -------
        None
        """
        if hasattr(reset_event, "_add_state_machine_for_set_reset_event"):
            # virtual event
            reset_event._add_state_machine_for_set_reset_event(self)
            self.reset_event = reset_event
        else:
            self.reset_event = reset_event

    def set_drop_event(self, drop_event):
        """
        Set the drop event which causes the drop trigger.
        The drop trigger moves the current state to "drop" state.

        Parameters
        ----------
        drop_event : Event

        Returns
        -------
        None
        """
        if hasattr(drop_event, "_add_state_machine_for_set_drop_event"):
            # virtual event
            drop_event._add_state_machine_for_set_drop_event(self)
            self.drop_event = drop_event
        else:
            self.drop_event = drop_event

    def get_trigger_list(self):
        """
        Return a list of triggers in state machine.

        Returns
        -------
        list : list of triggers
        """
        trigger_list = []
        for _, state in self.state_dict.items():
            for _, trigger in state.next.items():
                trigger_list.append(trigger)
        return trigger_list

    def get_trigger_event_list(self):
        """
        Return a list of events which are associated to triggers.

        Returns
        -------
        list : list of events
        """
        trigger_event_list = []
        if self.reset_event is not None:
            trigger_event_list.append(self.reset_event)
        if self.drop_event is not None:
            trigger_event_list.append(self.drop_event)
        for trigger in self.get_trigger_list():
            if not hasattr(trigger, "event"):
                continue
            trigger_event_list.append(trigger.event)
        return trigger_event_list

    def get_trigger(self, trigger_name):
        """
        Return trigger which name is trigger_name.
        If state machine has such a trigger, raise a error.

        Returns
        -------
        Trigger : trigger named as trigger_name
        """
        return self.trigger_dict[trigger_name]

    def _init_state(self):
        self.current_state_name = "start"

    def _get_trigger_dict(self):
        trigger_dict = {}
        if self.reset_event is not None:
            trigger_dict["reset"] = self.reset_event
        if self.drop_event is not None:
            trigger_dict["drop"] = self.drop_event
        for _, state in self.state_dict.items():
            for _, trigger in state.next.items():
                trigger_dict[trigger.name] = trigger
        return trigger_dict

    def _get_next_trigger_event_list(self):
        state = self.state_dict.get(self.current_state_name)
        if state is None:
            raise ValueError("invalid state")

        trigger_event_list = []
        if self.reset_event is not None:
            trigger_event_list.append(self.reset_event)
        if self.drop_event is not None:
            trigger_event_list.append(self.drop_event)
        for _, trigger in state.next.items():
            if not hasattr(trigger, "event"):
                continue
            trigger_event_list.append(trigger.event)
        return trigger_event_list

    def _next_state(self, trigger_name):
        state = self.state_dict.get(self.current_state_name)
        if state is None:
            raise ValueError("invalid state")
        if trigger_name == "reset":
            next_state_name = "start"
            is_change = True if self.current_state_name != next_state_name else False
            self.current_state_name = next_state_name
            return is_change
        if trigger_name == "drop":
            next_state_name = "drop"
            is_change = True if self.current_state_name != next_state_name else False
            self.current_state_name = next_state_name
            return is_change
        next_state_name = state._get_next_name(trigger_name)
        if next_state_name is None:
            raise ValueError(
                "invalid next state: statamechine={}({}), trigger_name={}".format(
                    self.name, self.current_state_name, trigger_name
                )
            )
        is_change = True if self.current_state_name != next_state_name else False
        self.current_state_name = next_state_name
        return is_change

    def _set_trigger_dict(self):
        if self.reset_event is not None:
            trigger_name = "reset"
            trigger = Trigger(trigger_name)
            event = self.reset_event
            if (
                hasattr(event, "event_type")
                and event.event_type == EventType.EDGE
                and hasattr(event, "event_trigger_type")
                and event.event_trigger_type == EventTriggerType.ONCE
            ):
                trigger.event = event
                sim_log.info("sm {} set event {}".format(self.name, trigger.event.name))
            else:
                trigger.event = +event
                sim_log.info(
                    "sm {} set +event {}".format(self.name, trigger.event.name)
                )
            self.reset_event = trigger.event
            self.trigger_dict[trigger_name] = trigger

        if self.drop_event is not None:
            trigger_name = "drop"
            trigger = Trigger(trigger_name)
            event = self.drop_event
            if (
                hasattr(event, "event_type")
                and event.event_type == EventType.EDGE
                and hasattr(event, "event_trigger_type")
                and event.event_trigger_type == EventTriggerType.ONCE
            ):
                trigger.event = event
            else:
                trigger.event = +event
            self.drop_event = trigger.event
            self.trigger_dict[trigger_name] = trigger

    def __call__(self, state_name):
        state = self.state_dict.get(state_name)
        if state is None:
            raise ValueError(
                "state machine {} has no state named {}".format(self.name, state_name)
            )
        return state

    def _add_state_if_not_exist(self, name):
        if self._exists(name):
            return
        state = State(name)
        state._set_state_machine(self)
        self.state_dict[name] = state

    def _exists(self, name):
        return name in self.state_dict

    def _exists_transition(self, name_from, trigger):
        if not self._exists(name_from):
            return False
        state_from = self.state_dict[name_from]
        return state_from._exists_next(trigger)

    def get_state(self, state_set):
        for _, state in self.state_dict.items():
            state_set.add(state)
