import random
import numpy as np
import copy
import datetime
import collections

from .common import EventType
from .common import EventArgType
from .common import LogStoreFlag
from .common import EventTriggerType
from .common import NotifyType
from .common import sim_log
from .event_base import EdgeOnceEvent
from .event_base import ResettableEvent
from .event_base import TriggerControllableEvent


class DatetimeParam:
    def __init__(self):
        self._init()
        self.timetable = None
        self.time_list = None

    def _init(self):
        self.time_index = None
        self.previous_current_time = None

    def read_timetable(self, timetable):
        try:
            if not isinstance(timetable, collections.abc.Mapping):
                return False
            self.timetable = dict()
            for key, value in timetable.items():
                time = datetime.datetime.strptime(key, "%Y-%m-%d %H:%M:%S")
                self.timetable[time] = value
            self.time_list = sorted(self.timetable.keys())
        except TypeError:
            self.timetable = None
            self.time_list = None
            return False
        return True

    def _find_time_index(self, current_time, current_index):
        if len(self.time_list) == 0:
            return -1
        if current_index is None:
            index0 = 0
        elif current_index < 0:
            index0 = 0
        else:
            index0 = current_index
        time0 = self.time_list[index0]
        if current_time < time0:
            return -1

        index1 = len(self.time_list) - 1
        time1 = self.time_list[index1]
        if time1 <= current_time:
            return index1

        # time0 <= current_time < time1
        while True:
            if index1 - index0 <= 1:
                break
            index_mid = int((index0 + index1) / 2)
            time0 = self.time_list[index0]
            time1 = self.time_list[index1]
            time_mid = self.time_list[index_mid]
            if time0 <= current_time and current_time < time_mid:
                index1 = index_mid
            elif time_mid <= current_time and current_time < time1:
                index0 = index_mid
        return index0

    def _get_time_index(self, current_time):
        if (
            self.previous_current_time is None
            or self.previous_current_time <= current_time
        ):
            self.time_index = self._find_time_index(current_time, self.time_index)
            self.previous_current_time = current_time
            return self.time_index
        else:
            self.time_index = self._find_time_index(current_time, None)
            self.previous_current_time = current_time
            return self.time_index

    def _get_parameter(self, update_time):
        parameter = self.timetable.get(update_time)
        if parameter is not None:
            return parameter
        current_time_index = self._get_time_index(update_time)
        if current_time_index < 0:
            sim_log.info("current_time_index={}".format(current_time_index))
            return {}
        else:
            return self.timetable[self.time_list[current_time_index]]

    def _calc_update_time(self, current_time, active, start_time, last_update_time):
        if active == False:
            return None

        current_time_index = self._get_time_index(current_time)
        if current_time_index < 0:
            sim_log.info("current_time_index={}".format(current_time_index))
            update_time_t0 = None
        else:
            update_time_t0 = self.time_list[current_time_index]

        next_time_index = current_time_index + 1
        if next_time_index >= len(self.time_list):
            update_time_t1 = None
        else:
            update_time_t1 = self.time_list[next_time_index]

        sim_log.info(
            "start_time={}, update_time_t0={}, update_time_t1={}".format(
                start_time, update_time_t0, update_time_t1
            )
        )

        if update_time_t0 is not None and last_update_time is None:
            return current_time

        return update_time_t1


class DeltatimeParam:
    def __init__(self):
        self._init()
        self.timetable = None
        self.time_list = None

    def _init(self):
        self.time_index = None
        self.previous_current_time = None
        self.current_time_index = -1
        self.start_time = None

    def read_timetable(self, timetable):
        if not isinstance(timetable, collections.abc.Mapping):
            return False
        self.timetable = dict()
        for key, value in timetable.items():
            if type(key) is int or type(key) is float:
                self.timetable[key] = value
            else:
                self.timetable = None
                self.time_list = None
                return False
        self.time_list = sorted(self.timetable.keys())
        return True

    def _get_parameter(self, update_time):
        days = self.time_list[self.current_time_index]
        update_time1 = self.start_time + datetime.timedelta(days=days)
        if not update_time == update_time1:
            raise ValueError(
                "update_time({}) != update_time1({})".format(update_time, update_time1)
            )
        return self.timetable[days]

    def _calc_update_time(self, current_time, active, start_time, last_update_time):
        if active == False:
            return None

        self.start_time = start_time
        self.current_time_index += 1
        if self.current_time_index >= len(self.time_list):
            return None
        days = self.time_list[self.current_time_index]
        if days < 0:
            raise ValueError("delta_time days must be >= 0, but {}".format(days))
        next_time = start_time + datetime.timedelta(
            days=self.time_list[self.current_time_index]
        )
        sim_log.info("start_time={}, next_time={}".format(start_time, next_time))

        return next_time


class FuncParam:
    def __init__(self):
        self._init()

    def _init(self):
        self.start_time = None
        self.current_time_index = -1
        self.param = None

    def set_func(self, func):
        if not callable(func):
            return False
        self.func = func
        return True

    def _get_parameter(self, update_time):
        return self.param

    def _calc_update_time(self, current_time, active, start_time, last_update_time):
        if active == False:
            return None

        self.start_time = start_time
        self.current_time_index += 1
        delta_time, self.param = self.func(
            current_time, start_time, self.current_time_index
        )
        if delta_time is None:
            return None
        elif delta_time < datetime.timedelta(days=0):
            raise ValueError("delta_time must be >= 0, but {}".format(delta_time))
        else:
            next_time = current_time + delta_time
            sim_log.info("start_time={}, next_time={}".format(start_time, next_time))
            return next_time


class ParameterUpdater:
    """
    Update values of person's health parameters at specified time points.
    Parameter updater starts when the current state moves to state_for_activate.
    Parameter updater ends when the current state moves to state_for_deactivate.

    Constructor options
    -------------------
    name : str
        name of parameter updater.
    timetable_or_func :
        dict (datetime type): for example,
            {
                "2021-06-01 00:00:00": {"parameter1": 0.0},
                "2021-06-10 00:00:00": {"parameter1": 1.0},
            }
        dict (datetime type): for example,
            {
                0: {"parameter1": 0.0},
                1: {"parameter1": 1.0},
            }
        or callable : for example,
            def funcparam(current_time, start_time, current_time_index):
                return datetime.timedelta(days=1), {"parameter1": 1.0}
    state_for_activate (optional): State
    state_for_deactivate (optional): State

    Examples
    --------
    >>> pu = ParameterUpdater(
            "sample_updater1",
            {
                "2021-06-01 00:00:00": {"parameter1": 0.0},
                "2021-06-10 00:00:00": {"parameter1": 1.0},
            },
            state_for_activate=state1,
        )
    # set multiple states for activate
    >>> pu = ParameterUpdater(
            "sample_updater2",
            {
                "2021-09-01 00:00:00": {"parameter2": 0.0},
                "2021-09-10 00:00:00": {"parameter2": 1.0},
            },
        )
    >>> pu.set_states_for_activate([state1, state2])
    """

    def __init__(
        self,
        name,
        timetable_or_func=None,
        state_for_activate=None,
        state_for_deactivate=None,
    ):
        self.name = name
        if state_for_activate is None:
            self.states_for_activate = None
        else:
            self.set_states_for_activate([state_for_activate])
        if state_for_deactivate is None:
            self.states_for_deactivate = None
        else:
            self.set_states_for_deactivate([state_for_deactivate])
        self.time_param = None
        datetime_param = DatetimeParam()
        deltatime_param = DeltatimeParam()
        func_param = FuncParam()
        if datetime_param.read_timetable(timetable_or_func):
            self.time_param = datetime_param
        elif deltatime_param.read_timetable(timetable_or_func):
            self.time_param = deltatime_param
        elif func_param.set_func(timetable_or_func):
            self.time_param = func_param
        if self.time_param is None:
            raise ValueError("time_param is not assigned")
        self.last_update_time = None
        self.start_time = None
        self.update_time = None
        self.replay_logger = None
        self.log_store = None
        self.finished = False

    def set_states_for_activate(self, states_for_activate):
        """
        Set states_for_activate which is a list of State.
        Parameter updater starts when the current state moves to any State
        in state_for_activate.

        Parameters
        ----------
        states_for_activate : list
            list of State.

        Returns
        -------
            None

        Examples
        --------
        >>> pu = ParameterUpdater(
                "sample_updater",
                {
                    "2021-06-01 00:00:00": {"parameter1": 0.0},
                    "2021-06-10 00:00:00": {"parameter1": 1.0},
                }
            )
        # set state_for_activate
        >>> pu.set_states_for_activate([state1])
        """
        if states_for_activate is None:
            self.states_for_activate = None
            return
        if not isinstance(states_for_activate, list):
            raise ValueError("states_for_activate must be list")
        self.states_for_activate = states_for_activate

    def set_states_for_deactivate(self, states_for_deactivate):
        """
        Set states_for_deactivate which is a list of State.
        Parameter updater starts when the current state moves to any State
        in state_for_activate.

        Parameters
        ----------
        states_for_deactivate : list
            list of State.

        Returns
        -------
            None

        Examples
        --------
        >>> pu = ParameterUpdater(
                "sample_updater",
                {
                    "2021-06-01 00:00:00": {"parameter1": 0.0},
                    "2021-06-10 00:00:00": {"parameter1": 1.0},
                }
            )
        # set state_for_activate
        >>> pu.set_states_for_deactivate([state1])
        """
        if states_for_deactivate is None:
            self.states_for_deactivate = None
            return
        if not isinstance(states_for_deactivate, list):
            raise ValueError("states_for_deactivate must be list")
        self.states_for_deactivate = states_for_deactivate

    def _set_replay_logger(self, replay_logger):
        self.replay_logger = replay_logger

    def _set_log_store(self, log_store):
        self.log_store = log_store

    def _init(self, current_time):
        self.done_time = None
        self.previous_current_time = None
        self.last_update_time = None
        self.update_time = None
        self.event_raise_time = None
        if self.states_for_activate is None:
            self.active = True
            self.start_time = current_time
        else:
            self.active = False
            self.start_time = None
        self.finished = False
        self.time_param._init()
        sim_log.info("ParameterUpdater({}), active={}".format(self.name, self.active))

    def _activate(self, current_time):
        self._init(current_time)
        self.active = True
        self.start_time = current_time

    def _deactivate(self):
        self.active = False

    def _get_update_time(self, current_time):
        if self.active == False or self.finished == True:
            return None
        if self.update_time is not None and current_time < self.update_time:
            return self.update_time
        # update
        sim_log.info(
            "current_time={}, ParameterUpdater, logging_function".format(current_time)
        )
        self.update_time = self._logging_function(
            self,
            self.time_param._calc_update_time,
            current_time,
            self.active,
            self.start_time,
            self.last_update_time,
        )
        if self.update_time is None:
            self.finished = True

        sim_log.info("update_time={}".format(self.update_time))
        return self.update_time

    def _update_parameter_main(self, current_time, parameter):
        # update_pramameter = self.timetable[self.update_time]
        update_pramameter = self.time_param._get_parameter(self.update_time)
        parameter.update(update_pramameter)
        return update_pramameter

    def _update_parameter(self, current_time, parameter):
        if self.active == False:
            return False
        sim_log.info(
            "current_time={}, ParameterUpdater({}), update_time={}, last_update_time={}, active={}, finished={}".format(
                current_time,
                self.name,
                self.update_time,
                self.last_update_time,
                self.active,
                self.finished,
            )
        )

        if self.last_update_time == current_time:
            return False

        if self.update_time is None or not current_time == self.update_time:
            return False
        update_pramameter = self._logging_parameter(
            self, self._update_parameter_main, current_time, parameter
        )
        self._update_detail(current_time, LogStoreFlag.PARAMETER, copy.copy(parameter))

        self.last_update_time = current_time
        sim_log.info(
            "current_time={}, parameter={}, update_pramameter={}".format(
                current_time, parameter, update_pramameter
            )
        )
        return True

    def _logging_parameter(self, log_target, func, current_time, parameter):
        if self.replay_logger is None:
            return func(current_time, parameter)
        else:
            return self.replay_logger.logging_parameter(
                log_target, func, current_time, parameter
            )

    def _logging_function(self, log_target, func, *args):
        if self.replay_logger is None:
            if func is not None:
                return func(*args)
            else:
                return args[0]
        else:
            return self.replay_logger.logging_function(log_target, func, *args)

    def _update_detail(
        self,
        current_time,
        log_type,
        log_info,
        is_event_raise_flag=None,
        append_flag=True,
    ):
        if self.log_store is not None:
            self.log_store.update_detail(
                current_time, log_type, log_info, is_event_raise_flag, append_flag
            )


class StochasticEvent(ResettableEvent):
    """
    Raise random events which intervals follow the exponential distribution.

    Constructor options
    -------------------
    name : str
        name of event.
    start_state_or_event : State or Event
        condition where event process starts.
        arriving at state or raising event makes event process start to count down.
    probability_func : callable
        function which returns 1/lambda. lambda is mean interval (the time unit is hour).
        input arguments are current_time and health_parameter.
    event_type : EventType
        EventType.LEVEL : default
            raise event when current_time >= event_raise_time.
        or EventType.EDGE :
            raise event only when current_time == event_raise_time.
    event_trigger_type : EventTriggerType
        EventTriggerType.NO_LIMIT : default
            no limit on the number of raise events at time slice.
        or EventTriggerType.ONCE :
            maximum number of raise events is 1 per time slice.
    exp_auto_reset : bool
        if exp_auto_reset is True, next event raise time is set when event raises.
        experimental option. not recommend to use.
    exp_stop_state_or_event : State or Event
        condition where event process stops.
        experimental option. not recommend to use.
    exp_stop_and_reset_flag : bool
        if exp_stop_and_reset_flag is True, stopped event doesn't raise.
        if exp_stop_and_reset_flag is False, stopped event isn't auto reset.

    Examples
    --------
    >>> ev = StochasticEvent(
            "poisson_arrival",
            sm("start"),
            lambda current_time, parameter: parameter["poisson_arrival_rate"],
        )
    """

    def __init__(
        self,
        name,
        start_state_or_event,
        probability_func=None,
        event_type=EventType.LEVEL,
        event_trigger_type=EventTriggerType.NOLIMIT,
        exp_auto_reset=False,
        exp_stop_state_or_event=None,
        exp_stop_and_reset_flag=False,
    ):
        self.auto_reset_flag = exp_auto_reset
        super().__init__(
            name,
            start_state_or_event,
            NotifyType.NEXT_TIME_STEP,
            exp_stop_state_or_event,
            exp_stop_and_reset_flag,
            event_type,
            event_trigger_type,
        )
        self._init()
        self.set_probability_func(probability_func)

    def _init(self):
        super()._init()
        self.auto_reset = self.auto_reset_flag
        self.event_num = 0
        self.current_probability_per_day = None

    def get_info(self):
        return (
            "start_state={}".format(self.start_state_or_event.name),
            self.probability_func,
        )

    def set_probability_func(self, probability_func):
        """
        Set probability_func which returns 1/lambda. lambda is mean interval (the time unit is hour).
        Input arguments are current_time and health_parameter.

        Parameters
        ----------
        probability_func : callable

        Returns
        -------
            None

        Examples
        --------
        >>> ev = StochasticEvent(
                "poisson_arrival",
                sm("start"),
            )
        # set probability_func
        >>> ev.set_probability_func(
                lambda current_time, parameter: parameter["poisson_arrival_rate"]
            )
        """

        if probability_func is None:
            return
        if type(probability_func) is int or type(probability_func) is float:
            self.probability_func = lambda parameter: probability_func
            return
        if callable(probability_func):
            self.probability_func = probability_func
            return
        raise ValueError("bad probability_func")

    def _update_event_log_name(self):
        self.event_log_name = "{}#{}".format(self.name, self.event_num)

    def _calc_next_event_time_delta(self, probability_per_day):
        next_event_day_max = 3650  # inf
        if probability_per_day < 0.000000001:
            sim_log.debug("probability_per_day < 0.000000001")
            return datetime.timedelta(days=next_event_day_max)
        if probability_per_day >= 1.0:
            sim_log.debug("probability_per_day = 1.0")
            return datetime.timedelta(seconds=0)
        random_value = random.random()
        next_event_day = np.log(1 - random_value) / np.log(1 - probability_per_day)
        if next_event_day == float("inf"):
            next_event_day = next_event_day_max
        next_event_day = min(next_event_day, next_event_day_max)
        return datetime.timedelta(days=next_event_day)

    def _set_event_raise_time(self, current_time, probability_per_day):
        next_event_time_delta = self._logging_function(
            self, self._calc_next_event_time_delta, probability_per_day
        )
        self.event_raise_time = current_time + next_event_time_delta
        self.current_probability_per_day = probability_per_day
        sim_log.info(
            "_set_event_raise_time({}): current_time={}, event_raise_time={}".format(
                self.name, current_time, self.event_raise_time
            )
        )
        self._update_detail_event(current_time, self)

    def _get_decision(self, current_time, event_time):
        if self.event_type == EventType.LEVEL:
            # Level trigger
            return event_time <= current_time
        else:
            # Edge trigger
            return event_time == current_time

    def _get_event_raise_time(self, current_time, parameter, state_machine):
        if self.active == False:
            return None
        if self.done_time is not None:
            # after done
            if self._get_decision(current_time, self.done_time):
                return super()._get_event_raise_time(True, state_machine)
            if self.done_time < current_time:
                # in case of Edge trigger
                return False
            else:
                raise ValueError("bad condition")
        # before done
        if self.event_raise_time is None:
            return None
        if self._get_decision(current_time, self.event_raise_time):
            if super()._get_event_raise_time(True, state_machine):
                return self.event_raise_time
            else:
                return False
        if self.event_raise_time < current_time:
            # in case of Edge trigger
            return False
        else:
            return self.event_raise_time

    def _update_event_parameter(self, current_time, parameter):
        self.auto_reset = self.auto_reset_flag
        self._update_event_parameter_next(current_time, parameter, next_time_step=False)

    def _update_event_parameter_next(
        self, current_time, parameter, next_time_step=False
    ):
        sim_log.info("current_time={}, update_event_parameter".format(current_time))
        if self.active == False:
            return

        if next_time_step:
            # update done_time
            self._is_event_raise(current_time, parameter, None, log_flag=True)
            if self.done_time is not None and self.auto_reset == False:
                sim_log.info(
                    "update_event_parameter, event_raise_time={}, auto reset off".format(
                        self.event_raise_time
                    )
                )
                return
            if self.done_time is not None and self.auto_reset == True:
                self.event_raise_time = None  # reset
                self.done_time = None

        sim_log.info(
            "update_event_parameter, event_raise_time={}".format(self.event_raise_time)
        )
        if self.event_raise_time is None and self.done_time is None:
            probability_per_day = self.probability_func(current_time, parameter)
            # event_raise_time is not set. set event_raise_time.
            self._set_event_raise_time(current_time, probability_per_day)
            return
        if self.event_raise_time is not None and self.done_time is None:
            probability_per_day = self.probability_func(current_time, parameter)
            if not self.current_probability_per_day == probability_per_day:
                # probability_per_day is updated. update event_raise_time.
                self._set_event_raise_time(current_time, probability_per_day)
            return
        if self.event_raise_time is None and self.done_time is not None:
            probability_per_day = self.probability_func(current_time, parameter)
            # event_raise_time is not set. set event_raise_time.
            self._set_event_raise_time(current_time, probability_per_day)
            return
        if self.event_raise_time is not None and self.done_time is not None:
            # done. update event_raise_time.
            probability_per_day = self.probability_func(current_time, parameter)
            self._set_event_raise_time(current_time, probability_per_day)

    def _update_event_parameter_stop(self, current_time, parameter):
        if self.stop_and_reset_flag:
            # stop
            super()._update_event_parameter_stop(current_time, parameter)
        else:
            # auto_reset off
            self.auto_reset = False

    def _is_event_raise_main(self, current_time, parameter):
        sim_log.info("event_raise_time={}".format(self.event_raise_time))
        if self.active == False:
            return False
        if self.done_time is not None:
            # after done
            return self._get_decision(current_time, self.done_time)
        # before done
        if self.event_raise_time is None:
            return False
        done = self._get_decision(current_time, self.event_raise_time)
        if done:
            self.event_num += 1
            self._update_event_log_name()
            sim_log.info("event_num={}".format(self.event_num))
            if not self.event_raise_time == current_time:
                # detection of event raise failed
                raise ValueError("event_raise_time != current_time")
            self.done_time = current_time
        return done

    def _is_event_raise(self, current_time, parameter, state_machine, log_flag=True):
        sim_log.info("current_time={}".format(current_time))
        is_event_raise_flag = self._is_event_raise_main(current_time, parameter)
        return super()._is_event_raise(
            current_time, is_event_raise_flag, state_machine, log_flag
        )

    def _update_state_machine_value(
        self, current_time, parameter, state_machine, event_raise_flag
    ):
        result = self._is_event_raise(
            current_time, parameter, state_machine, log_flag=False
        )
        if result == event_raise_flag:
            return super()._update_state_machine_value(result, state_machine)
        return False


class ScheduleEvent(ResettableEvent):
    """
    Raise an event at specified time.

    Constructor options
    -------------------
    name : str
        name of event.
    start_state_or_event : State or Event
        condition where event process starts.
        arraiving at state or raising event makes event process start to count down.
    time : datetime.datetime
        time to raise event.
    event_type : EventType
        EventType.LEVEL : default
            raise event when current_time >= event_raise_time.
        or EventType.EDGE :
            raise event only when current_time == event_raise_time.
    event_trigger_type : EventTriggerType
        EventTriggerType.NO_LIMIT : default
            no limit on the number of raise events at time slice.
        or EventTriggerType.ONCE :
            maximum number of raise events is 1 per time slice.

    Examples
    --------
    >>> ev = ScheduleEvent(
            "schedule1",
            time=datetime.datetime.strptime("2021-06-01 00:00:00", "%Y-%m-%d %H:%M:%S"),
        )
    """

    def __init__(
        self,
        name,
        start_state_or_event=None,
        time=None,
        event_type=EventType.LEVEL,
        event_trigger_type=EventTriggerType.NOLIMIT,
    ):
        super().__init__(
            name,
            start_state_or_event,
            NotifyType.CHANGE_STATE,
            None,
            False,
            event_type,
            event_trigger_type,
        )
        self.event_raise_time0 = time
        self._init()

    def _self_set_start_time(self, start_time):
        pass

    def _init(self):
        super()._init()

    def set_time(self, time):
        """
        Set time to raise event.

        Parameters
        ----------
        probability_func : callable

        Returns
        -------
            None

        Examples
        --------
        >>> ev = StochasticEvent(
                "poisson_arrival",
                sm("start"),
            )
        # set probability_func
        >>> ev.set_probability_func(
                lambda current_time, parameter: parameter["poisson_arrival_rate"]
            )
        """
        self.event_raise_time0 = time

    def _set_time(self, current_time, time):
        self.event_raise_time = self._logging_function(self, None, time)
        sim_log.debug(
            "current_time={}, StochasticEvent({}), event_raise_time={}".format(
                current_time, self.name, self.event_raise_time
            )
        )
        if self.event_raise_time is not None and self.event_raise_time < current_time:
            ValueError(
                " StochasticEvent({}), bad condition: event_raise_time ({}) < current_time ({})".format(
                    self.name, self.event_raise_time, current_time
                )
            )
        self.done_time = None
        self._update_detail_event(current_time, self)

    def _get_decision(self, current_time, event_time):
        if self.event_type == EventType.LEVEL:
            # Level trigger
            return event_time <= current_time
        else:
            # Edge trigger
            return event_time == current_time

    def _get_event_raise_time(self, current_time, parameter, state_machine):
        if self.active == False:
            return None
        if self.done_time is not None:
            # after done
            if self._get_decision(current_time, self.done_time):
                return super()._get_event_raise_time(True, state_machine)
            if self.done_time < current_time:
                # in case of Edge trigger
                return False
            else:
                raise ValueError("bad condition")
        # before done
        if self.event_raise_time is None:
            return None
        if self._get_decision(current_time, self.event_raise_time):
            if super()._get_event_raise_time(True, state_machine):
                return self.event_raise_time
            else:
                return False
        if self.event_raise_time < current_time:
            # in case of Edge trigger
            return False
        else:
            return self.event_raise_time

    def _is_event_raise_main(self, current_time, parameter):
        sim_log.info("event_raise_time={}".format(self.event_raise_time))
        if self.active == False:
            return False
        if self.done_time is not None:
            # after done
            return self._get_decision(current_time, self.done_time)
        # before done
        if self.event_raise_time is None:
            return False
        done = self._get_decision(current_time, self.event_raise_time)
        if done:
            self.done_time = current_time
            if not self.event_raise_time == current_time:
                # detection of event raise missed
                sim_log.debug(
                    "event={}, event_raise_time ({})!= current_time ({})".format(
                        self.name, self.event_raise_time, current_time
                    )
                )
        return done

    def _is_event_raise(self, current_time, parameter, state_machine, log_flag=True):
        is_event_raise_flag = self._is_event_raise_main(current_time, parameter)
        return super()._is_event_raise(
            current_time, is_event_raise_flag, state_machine, log_flag
        )

    def _set_event_raise_time_main(self, current_time, parameter):
        self._set_time(current_time, self.event_raise_time0)

    def _set_event_raise_time(self, current_time, parameter):
        self._set_event_raise_time_main(current_time, parameter)

    def _update_event_parameter(self, current_time, parameter):
        self._set_event_raise_time(current_time, parameter)

    def _update_state_machine_value(
        self, current_time, parameter, state_machine, event_raise_flag
    ):
        result = self._is_event_raise(
            current_time, parameter, state_machine, log_flag=False
        )
        if result == event_raise_flag:
            return super()._update_state_machine_value(result, state_machine)
        return False


class TimerEvent(ResettableEvent):
    """
    Raise an event after specified time interval.

    Constructor options
    -------------------
    name : str
        name of event.
    start_state_or_event : State or Event
        condition where event process starts.
        arriving at state or raising event makes event process start to count down.
    interval :
        callable :
            function which returns datetime.timedelta.
            input argument is health_parameter.
        or datetime.timedelta
    event_type : EventType
        EventType.LEVEL : default
            raise event when current_time >= event_raise_time.
        or EventType.EDGE :
            raise event only when current_time == event_raise_time.
    event_trigger_type : EventTriggerType
        EventTriggerType.NO_LIMIT : default
            no limit on the number of raise events at time slice.
        or EventTriggerType.ONCE :
            maximum number of raise events is 1 per time slice.

    Examples
    --------
    >>> ev = TimerEvent(
            "timer1",
            sm("start"),
            datetime.timedelta(hours=12),
        )
    """

    def __init__(
        self,
        name,
        start_state_or_event=None,
        interval=None,
        event_type=EventType.LEVEL,
        event_trigger_type=EventTriggerType.NOLIMIT,
    ):
        super().__init__(
            name,
            start_state_or_event,
            NotifyType.CHANGE_STATE,
            None,
            False,
            event_type,
            event_trigger_type,
        )
        self._init()
        self.set_interval(interval)

    def _self_set_start_time(self, start_time):
        pass

    def _init(self):
        super()._init()

    def get_info(self):
        return "start_state={}".format(self.start_state_or_event.name), self.interval

    def set_interval(self, interval):
        """
        Set time interval

        Parameters
        ----------
        interval :
            callable :
                function which returns datetime.timedelta.
                input argument is health_parameter.
            or datetime.timedelta

        Returns
        -------
            None

        Examples
        --------
        >>> ev = TimerEvent(
                "timer1",
                sm("start"),
            )
        # set interval
        >>> ev.set_interval(
                datetime.timedelta(hours=12),
            )
        """
        if interval is None:
            self.interval = None
            return
        if type(interval) is datetime.timedelta:
            self.interval = lambda current_time, parameter: interval
            return
        if callable(interval):
            self.interval = interval
            return
        raise ValueError("bad interval")

    def _get_decision(self, current_time, event_time):
        if self.event_type == EventType.LEVEL:
            # Level trigger
            return event_time <= current_time
        else:
            # Edge trigger
            return event_time == current_time

    def _get_event_raise_time(self, current_time, parameter, state_machine):
        if self.active == False:
            return None
        if self.done_time is not None:
            # after done
            if self._get_decision(current_time, self.done_time):
                return super()._get_event_raise_time(True, state_machine)
            if self.done_time < current_time:
                # in case of Edge trigger
                return False
            else:
                raise ValueError("bad condition")
        # before done
        if self.event_raise_time is None:
            return None
        if self._get_decision(current_time, self.event_raise_time):
            if super()._get_event_raise_time(True, state_machine):
                return self.event_raise_time
            else:
                return False
        if self.event_raise_time < current_time:
            # in case of Edge trigger
            return False
        else:
            return self.event_raise_time

    def _is_event_raise_main(self, current_time, parameter):
        sim_log.info("event_raise_time={}".format(self.event_raise_time))
        if self.active == False:
            return False
        if self.done_time is not None:
            # after done
            return self._get_decision(current_time, self.done_time)
        # before done
        if self.event_raise_time is None:
            return False
        done = self._get_decision(current_time, self.event_raise_time)
        if done:
            self.done_time = current_time
            if not self.event_raise_time == current_time:
                # detection of event raise missed
                sim_log.debug(
                    "event={}, event_raise_time ({})!= current_time ({})".format(
                        self.name, self.event_raise_time, current_time
                    )
                )
        return done

    def _is_event_raise(self, current_time, parameter, state_machine, log_flag=True):
        is_event_raise_flag = self._is_event_raise_main(current_time, parameter)
        return super()._is_event_raise(
            current_time, is_event_raise_flag, state_machine, log_flag
        )

    def _set_event_raise_time_main(self, current_time, parameter):
        self.start_time = current_time
        if self.interval is None:
            self.event_raise_time = None
            return
        interval_datetime = self._logging_function(
            self, self.interval, current_time, parameter
        )
        self.event_raise_time = (
            None if interval_datetime is None else current_time + interval_datetime
        )
        sim_log.debug(
            "current_time={}, TimerEvent({}), event_raise_time={}".format(
                current_time, self.name, self.event_raise_time
            )
        )
        if self.event_raise_time is not None and self.event_raise_time < current_time:
            ValueError(
                " TimerEvent({}), bad condition: event_raise_time ({}) < current_time ({})".format(
                    self.name, self.event_raise_time, current_time
                )
            )

    def _set_event_raise_time(self, current_time, parameter):
        self._set_event_raise_time_main(current_time, parameter)
        self._update_detail_event(current_time, self)

    def _update_event_parameter(self, current_time, parameter):
        if self.event_raise_time is None and self.done_time is None:
            # event_raise_time is not set. set event_raise_time.
            self._set_event_raise_time(current_time, parameter)
            return
        if self.event_raise_time is not None and self.done_time is None:
            # before done. parameter may change. update event_raise_time.
            self._set_event_raise_time(current_time, parameter)
            return
        if self.event_raise_time is None and self.done_time is not None:
            # event_raise_time is not set. set event_raise_time.
            self._set_event_raise_time(current_time, parameter)
            return
        if self.event_raise_time is not None and self.done_time is not None:
            # done. update event_raise_time.
            self._set_event_raise_time(current_time, parameter)
            return

    def _update_state_machine_value(
        self, current_time, parameter, state_machine, event_raise_flag
    ):
        result = self._is_event_raise(
            current_time, parameter, state_machine, log_flag=False
        )
        if result == event_raise_flag:
            return super()._update_state_machine_value(result, state_machine)
        return False


class StateEvent(TriggerControllableEvent):
    """
    Raise an event when arriving at specified state.

    Constructor options
    -------------------
    name : str
        name of event.
    state : State
        state where event raises.
    event_type : EventType
        EventType.LEVEL : default
            raise event when current_time >= event_raise_time.
        or EventType.EDGE :
            raise event only when current_time == event_raise_time.
    event_trigger_type : EventTriggerType
        EventTriggerType.NO_LIMIT : default
            no limit on the number of raise events at time slice.
        or EventTriggerType.ONCE :
            maximum number of raise events is 1 per time slice.

    Examples
    --------
    >>> ev = StateEvent(
            "arrive_at_state1",
            sm("state1"),
        )
    """

    def __init__(
        self,
        name,
        state,
        event_type=EventType.LEVEL,
        event_trigger_type=EventTriggerType.NOLIMIT,
    ):
        super().__init__(event_type, event_trigger_type)
        self.state = state
        self.name = name
        self.event_log_name = None
        self.event_formula = None
        self.event_for_notify_change = dict()
        self.event_for_notify_stop = dict()

    def _init(self):
        pass

    def get_info(self):
        return "state={}".format(self.state.name), None

    def _get_event_raise_time(self, current_time, parameter, state_machine):
        return super()._get_event_raise_time(
            self._is_event_raise(
                current_time, parameter, state_machine, log_flag=False
            ),
            state_machine,
        )

    def _is_event_raise_main(self, current_time, parameter):
        if self.event_type == EventType.LEVEL:
            return self.state._get_current_state()
        if self.event_type == EventType.EDGE:
            if current_time == self.state.last_trans_time:
                return self.state._get_current_state()
        return False

    def _is_event_raise(self, current_time, parameter, state_machine, log_flag=True):
        is_event_raise_flag = self._is_event_raise_main(current_time, parameter)
        return super()._is_event_raise(
            current_time, is_event_raise_flag, state_machine, log_flag
        )

    def _update_state_machine_value(
        self, current_time, parameter, state_machine, event_raise_flag
    ):
        result = self._is_event_raise(
            current_time, parameter, state_machine, log_flag=False
        )
        if result == event_raise_flag:
            return super()._update_state_machine_value(result, state_machine)
        return False


class ParameterEvent(TriggerControllableEvent):
    """
    Raise an event when specified parameter condition meets.

    Constructor options
    -------------------
    name : str
        name of event.
    parameter_name_value_or_eval_func : callable, list or str
        callable :
            function which returns bool.
            input argument is health_parameter.
        list :
            pair of parameter name and parameter value.
            for example,
            ["parameter1", 0]
        or str :
            parameter name.
            raise event when value of specified parameter changes.
    event_type : EventType
        EventType.LEVEL : default
            raise event when current_time >= event_raise_time.
        or EventType.EDGE :
            raise event only when current_time == event_raise_time.
    event_trigger_type : EventTriggerType
        EventTriggerType.NO_LIMIT : default
            no limit on the number of raise events at time slice.
        or EventTriggerType.ONCE :
            maximum number of raise events is 1 per time slice.

    Examples
    --------
    >>> ev = ParameterEvent(
            "parameter1_is_0",
            ["parameter1", 0],
        )
    """

    def __init__(
        self,
        name,
        parameter_name_value_or_eval_func,
        event_type=EventType.LEVEL,
        event_trigger_type=EventTriggerType.NOLIMIT,
    ):
        super().__init__(event_type, event_trigger_type)
        self.name = name
        self.event_log_name = None
        self.event_formula = None
        self.set_eval_func(parameter_name_value_or_eval_func)
        self.event_for_notify_change = dict()
        self.event_for_notify_stop = dict()
        self.replay_logger = None
        self._init()

    def get_info(self):
        if self.event_arg_type is EventArgType.FUNCTION:
            return "", self.eval_func

        if self.event_arg_type is EventArgType.LIST:
            return (
                "name={}, value={}".format(self.parameter_name, self.parameter_value),
                None,
            )

        if self.event_arg_type is EventArgType.STRING:
            return "name={} (change)".format(self.parameter_name), None

    def check(self, event_seq=None):
        # if Parameter change mode is on and EventType is Level,
        # keep in mind that the event always raises
        if (
            self.event_arg_type == EventArgType.STRING
            and self.event_type == EventType.LEVEL
        ):
            warning_flag = True
            if event_seq is not None:
                for event in event_seq:
                    if isinstance(event, EdgeOnceEvent):
                        warning_flag = False
                        break
            if warning_flag:
                sim_log.warning(
                    "event({}), Parameter change mode is on and EventType is Level. Please keep in mind that ParameterEvent always raises.".format(
                        self.name
                    )
                )

    def _init(self):
        self.tmp_parameter = None
        self.is_triggered = False
        self._reset()

    def _reset(self):
        self.last_decision = None
        self.done_time = None
        self.parameter_updated = False

    def _check_input_type(self, input):
        if callable(input):
            return EventArgType.FUNCTION
        if isinstance(input, list) or isinstance(input, tuple):
            return EventArgType.LIST
        input_type = type(input)
        if input_type is int or input_type is float:
            return EventArgType.NUMBER
        if input_type is str:
            return EventArgType.STRING
        return EventArgType.OTHER

    def _is_parameter_changed(self, parameter):
        current_parameter = parameter.get(self.parameter_name)
        sim_log.info(
            "parameter_name={}, current_parameter={}, is_triggered={}, tmp_parameter={}".format(
                self.parameter_name,
                current_parameter,
                self.is_triggered,
                self.tmp_parameter,
            )
        )
        if self.is_triggered == False:
            self.tmp_parameter = current_parameter
            return False

        if current_parameter != self.tmp_parameter:
            self.tmp_parameter = current_parameter
            self.done_time = None
            return True
        return False

    def _is_parameter_expected(self, parameter):
        return parameter.get(self.parameter_name) == self.parameter_value

    def _reset_if_changes(self, current_time, parameter):
        sim_log.info("ParameterEvent({})".format(self.name))
        self.parameter_updated = True
        if self.event_type == EventType.EDGE:
            sim_log.info("get_decision")
            self._get_decision(current_time, parameter)

    def get_event_log_name(self):
        if not hasattr(self, "event_arg_type"):
            return super().get_event_log_name()

        if self.event_arg_type is EventArgType.FUNCTION:
            return "{}(eval_func)".format(self.name)

        if self.event_arg_type is EventArgType.LIST:
            return '{}("{}"="{}")'.format(
                self.name, self.parameter_name, self.parameter_value
            )

        if self.event_arg_type is EventArgType.STRING:
            return '{}("{}" changed)'.format(self.name, self.parameter_name)

    def set_eval_func(self, parameter_name_value_or_eval_func):
        self.parameter_name = None
        self.parameter_value = None

        if parameter_name_value_or_eval_func is None:
            return

        self.event_arg_type = self._check_input_type(parameter_name_value_or_eval_func)

        if self.event_arg_type is EventArgType.FUNCTION:
            self.eval_func = parameter_name_value_or_eval_func
            return

        if self.event_arg_type is EventArgType.LIST:
            self.parameter_name = parameter_name_value_or_eval_func[0]
            self.parameter_value = parameter_name_value_or_eval_func[1]
            self.eval_func = self._is_parameter_expected
            return

        if self.event_arg_type is EventArgType.STRING:
            self.parameter_name = parameter_name_value_or_eval_func
            self.eval_func = self._is_parameter_changed
            return

        raise ValueError("bad probability_func")

    def _get_decision(self, current_time, parameter, is_trigger=False):
        sim_log.info(
            "current_time={}, ParameterEvent({}), get_decision, parameter={}".format(
                current_time, self.name, parameter
            )
        )
        sim_log.info(
            "last_decision={}, done_time={}, parameter_updated={}".format(
                self.last_decision, self.done_time, self.parameter_updated
            )
        )
        if self.event_type == EventType.LEVEL:
            if self.last_decision is not None and not self.parameter_updated:
                if self.eval_func != self._is_parameter_changed:
                    sim_log.info(" get_decision={}".format(self.last_decision))
                    return self.last_decision
                else:
                    if self.done_time is None:
                        sim_log.info(" get_decision={}".format(self.last_decision))
                        return self.last_decision
                    if self.done_time is not None and self.done_time == current_time:
                        sim_log.info(" get_decision={}".format(self.last_decision))
                        return self.last_decision
                    else:
                        sim_log.info(" get_decision={}".format(False))
                        return False
            self.last_decision = self._logging_function(
                self,
                self.eval_func,
                parameter,
            )
            if is_trigger:
                self.is_triggered = True
            self.parameter_updated = False
            sim_log.info(" get_decision={}".format(self.last_decision))
            return self.last_decision
        else:  # Edge
            if self.last_decision is not None and not self.parameter_updated:
                if self.done_time is None:
                    sim_log.info(" get_decision={}".format(self.last_decision))
                    return self.last_decision
                if self.done_time is not None and self.done_time == current_time:
                    sim_log.info(" get_decision={}".format(self.last_decision))
                    return self.last_decision
                else:
                    sim_log.info(" get_decision={}".format(False))
                    return False
            new_decision = self._logging_function(
                self,
                self.eval_func,
                parameter,
            )
            if is_trigger:
                self.is_triggered = True
            if self.is_triggered and self.last_decision != new_decision:
                self._reset()
                self.last_decision = new_decision  # save last_decision
            self.parameter_updated = False
            sim_log.info(" get_decision={} (new_decision)".format(self.last_decision))
            return self.last_decision

    def _get_event_raise_time(self, current_time, parameter, state_machine):
        return super()._get_event_raise_time(
            self._is_event_raise(
                current_time, parameter, state_machine, log_flag=False, is_trigger=False
            ),
            state_machine,
        )

    def _is_event_raise_main(self, current_time, parameter, is_trigger=False):
        done = self._get_decision(current_time, parameter, is_trigger)
        if done:
            self.done_time = current_time
        sim_log.info(
            "ParameterEvent({}), done={}, done_time={}".format(
                self.name, done, self.done_time
            )
        )
        return done

    def _is_event_raise(
        self, current_time, parameter, state_machine, log_flag=True, is_trigger=True
    ):
        is_event_raise_flag = self._is_event_raise_main(
            current_time, parameter, is_trigger
        )
        result = super()._is_event_raise(
            current_time, is_event_raise_flag, state_machine, log_flag
        )
        sim_log.info("ParameterEvent({}), result={}".format(self.name, result))
        return result

    def _update_state_machine_value(
        self, current_time, parameter, state_machine, event_raise_flag
    ):
        sim_log.info("ParameterEvent({})".format(self.name))
        result = self._is_event_raise(
            current_time, parameter, state_machine, log_flag=False, is_trigger=False
        )
        if result == event_raise_flag:
            return super()._update_state_machine_value(result, state_machine)
        return False


class DummyEvent(TriggerControllableEvent):
    """
    Raise an event.

    Constructor options
    -------------------
    name : str
        name of event.
    parameter_list : list
        list of parametes to log event
    event_raise : bool
        if event_raise is True, raise event is logged.
        if event_raise is False, raise event isn't logged.

    Examples
    --------
    >>> ev = DummyEvent(
            "dummy1",
            ["parameter1", "parameter2", "parameter3"],
        )
    """

    def __init__(self, name, parameter_list=None, event_raise=True):
        super().__init__(EventType.LEVEL, EventTriggerType.NOLIMIT)
        self.name = name
        self.event_log_name = None
        self.event_formula = None
        self.parameter_list = parameter_list
        self.event_for_notify_change = dict()
        self.event_for_notify_stop = dict()
        self.event_raise = event_raise

    def _init(self):
        pass

    def _get_event_raise_time(self, current_time, parameter, state_machine):
        return super()._get_event_raise_time(
            self._is_event_raise(
                current_time, parameter, state_machine, log_flag=False
            ),
            state_machine,
        )

    def _is_event_raise_main(self, current_time, parameter):
        return self.event_raise

    def _update_event_log_name(self, parameter):
        if self.parameter_list is not None:
            parameter_str = [
                '"{}"="{}"'.format(parameter_name, str(parameter.get(parameter_name)))
                for parameter_name in self.parameter_list
            ]
            self.event_log_name = "{}({})".format(self.name, ",".join(parameter_str))
        else:
            self.event_log_name = self.name

    def _is_event_raise(self, current_time, parameter, state_machine, log_flag=True):
        self._update_event_log_name(parameter)
        is_event_raise_flag = self._is_event_raise_main(current_time, parameter)
        return super()._is_event_raise(
            current_time, is_event_raise_flag, state_machine, log_flag
        )

    def _update_state_machine_value(
        self, current_time, parameter, state_machine, event_raise_flag
    ):
        result = self._is_event_raise(
            current_time, parameter, state_machine, log_flag=False
        )
        if result == event_raise_flag:
            return super()._update_state_machine_value(result, state_machine)
        return False


class RandomEventChild(ResettableEvent):
    def __init__(self, name, parent):
        super().__init__(
            name,
            None,
            parent.notify_type,
            None,
            False,
            parent.event_type,
            parent.event_trigger_type,
        )
        self.parent = parent

    def get_info(self):
        parent_name = self.parent.name
        return (
            "parent={}, parent start_state={}".format(
                parent_name, self.parent.state.name
            ),
            None,
        )

    def _set_replay_logger(self, replay_logger):
        self.parent._set_replay_logger(replay_logger)

    def _init(self):
        self.parent._init()

    def _get_event_to_notify(self):
        return self.parent

    def _get_event_raise_time(self, current_time, parameter, state_machine):
        return super()._get_event_raise_time(
            self._is_event_raise(
                current_time, parameter, state_machine, log_flag=False
            ),
            state_machine,
        )

    def _is_event_raise_main(self, current_time, parameter):
        return self.parent._is_child_event_raise(self.name, current_time, parameter)

    def _is_event_raise(self, current_time, parameter, state_machine, log_flag=True):
        is_event_raise_flag = self._is_event_raise_main(current_time, parameter)
        return super()._is_event_raise(
            current_time, is_event_raise_flag, state_machine, log_flag
        )

    def _update_state_machine_value(
        self, current_time, parameter, state_machine, event_raise_flag
    ):
        result = self._is_event_raise(
            current_time, parameter, state_machine, log_flag=False
        )
        if result == event_raise_flag:
            return super()._update_state_machine_value(result, state_machine)
        return False


class RandomEvent(ResettableEvent):
    """
    Raise a random event.

    Constructor options
    -------------------
    name : str
        name of event.
    name_and_probability_func : callable
        function which returns an event name.
        input arguments are current_time and health_parameter.
    start_state_or_event : State or Event
        condition where event process starts.
        arriving at state or raising event makes event process start to count down.
    event_type : EventType
        EventType.LEVEL : default
            raise event when current_time >= event_raise_time.
        or EventType.EDGE :
            raise event only when current_time == event_raise_time.
    event_trigger_type : EventTriggerType
        EventTriggerType.NO_LIMIT : default
            no limit on the number of raise events at time slice.
        or EventTriggerType.ONCE :
            maximum number of raise events is 1 per time slice.

    Examples
    --------
    >>> import random
    >>> def random1_select(current_time, parameter):
            if parameter[success_rate] == "high":
                rand_param = [0.9, 0.1]
            else:
                rand_param = [0.5, 0.5]
            return random.choices(
                ["success", "fail"],
                k=1,
                weights=rand_param,
            )[0]
    >>> ev = RandomEvent(
            "random1",
            random1_select,
            sm("state1"),
        )
    >>> ev_success = ev.event("success")
    >>> ev_fail = ev.event("fail")
    """

    def __init__(
        self,
        name,
        name_and_probability_func,
        start_state_or_event=None,
        event_type=EventType.LEVEL,
        event_trigger_type=EventTriggerType.NOLIMIT,
    ):
        super().__init__(
            name,
            start_state_or_event,
            NotifyType.CHANGE_STATE,
            None,
            False,
            event_type,
            event_trigger_type,
        )
        self.state = start_state_or_event
        self.name_and_probability_func = name_and_probability_func
        self._init()
        self.child_event_dict = dict()

    def event(self, name):
        """
        Get a random event.
        The event name must correspond to return value of name_and_probability_func.

        Parameters
        ----------
        name : str
            name of event.

        Returns
        -------
            Event

        Examples
        --------
        >>> ev_success = ev.event("success")
        >>> ev_fail = ev.event("fail")
        """

        child_event = self.child_event_dict.get(name)
        if child_event is None:
            child_event = RandomEventChild(name, self)
            self.child_event_dict[name] = child_event
            return child_event
        else:
            return self.child_event_dict[name]

    def _init(self):
        super()._init()

    def _update_event_parameter(self, current_time, parameter):
        self._get_random_event(current_time, parameter)

    def set_name_and_probability_func(self, name_and_probability_func):
        """
        Set  name_and_probability_func.

        Parameters
        ----------
        name_and_probability_func : callable
            function which returns an event name.
            input arguments are current_time and health_parameter.

        Returns
        -------
            None

        Examples
        --------
        >>> import random
        >>> ev = RandomEvent(
                "random1",
                None,
                sm("state1"),
            )
        >>> def random1_select(current_time, parameter):
                if parameter[success_rate] == "high":
                    rand_param = [0.9, 0.1]
                else:
                    rand_param = [0.5, 0.5]
                return random.choices(
                    ["success", "fail"],
                    k=1,
                    weights=rand_param,
                )[0]
        >>> ev.set_name_and_probability_func(random1_select)
        """

        self.name_and_probability_func = name_and_probability_func

    def _get_event_raise_time(self, current_time, parameter, state_machine):
        return False

    def _is_event_raise_main(self, current_time, parameter):
        return False

    def _is_event_raise(self, current_time, parameter, state_machine, log_flag=True):
        is_event_raise_flag = self._is_event_raise_main(current_time, parameter)
        return is_event_raise_flag

    def _get_new_random_event(self, current_time, parameter):
        if isinstance(self.name_and_probability_func, collections.abc.Mapping):
            name_list = list(self.name_and_probability_func.keys())
            prob_list = list(self.name_and_probability_func.values())
            choice = random.choices(name_list, k=1, weights=prob_list)[0]
            sim_log.info("RandomEvent (name_list)={}".format(name_list))
            sim_log.info("RandomEvent (prob_list)={}".format(prob_list))
            sim_log.info("choise={}".format(choice))

        if callable(self.name_and_probability_func):
            choice = self.name_and_probability_func(current_time, parameter)

        child_event = self.child_event_dict.get(choice)
        if child_event is None:
            raise ValueError(
                "random event hasn't event ({}). event name = ({})".format(
                    choice, self.name
                )
            )

        return choice

    def _get_random_event(self, current_time, parameter):
        if self.done_time is not None and self.event_decision is not None:
            return self.event_decision
        # set or update event_decision.
        # keep in mind that event_decision is not updated
        # if start_state_or_event is None.
        self.event_decision = self._logging_function(
            self,
            self._get_new_random_event,
            current_time,
            parameter,
        )
        self.done_time = current_time
        return self.event_decision

    def _is_child_event_raise(self, name, current_time, parameter):
        if self.active == False:
            return False
        if self.event_type == EventType.LEVEL:
            return name == self._get_random_event(current_time, parameter)
        if self.event_type == EventType.EDGE:
            if self.done_time is None or current_time == self.done_time:
                return name == self._get_random_event(current_time, parameter)
        return False

    def _update_state_machine_value(
        self, current_time, parameter, state_machine, event_raise_flag
    ):
        return False
