import datetime
import uuid

from .common import OperationType
from .common import EventCalcType
from .common import EventType
from .common import EventTriggerType
from .common import sim_log
from .common import tool_log


class EventOpe:
    def __init__(self):
        pass

    def _init_ope(self):
        self.ope_dict = {}
        self.ope_dict[OperationType.AND] = self._event_ope__and__
        self.ope_dict[OperationType.OR] = self._event_ope__or__
        self.ope_dict[OperationType.OR_ONCE] = self._event_ope__or_once__
        self.ope_dict[OperationType.INVERT] = self._event_ope__invert__
        self.ope_dict[OperationType.EDGE_ONCE] = self._event_ope__edge_once__

        self.ope_dict[OperationType.EQ] = self._event_ope__eq__
        self.ope_dict[OperationType.NE] = self._event_ope__ne__
        self.ope_dict[OperationType.GT] = self._event_ope__gt__
        self.ope_dict[OperationType.GE] = self._event_ope__ge__
        self.ope_dict[OperationType.LT] = self._event_ope__lt__
        self.ope_dict[OperationType.LE] = self._event_ope__le__
        self.ope_dict[OperationType.ADD] = self._event_ope__add__
        self.ope_dict[OperationType.SUB] = self._event_ope__sub__
        self.ope_dict[OperationType.MUL] = self._event_ope__mul__
        self.ope_dict[OperationType.DIV] = self._event_ope__truediv__

    def _event_ope__and__(self, other):
        return self._set_ope(other, "({}&{})", OperationType.AND)

    def _event_ope__or__(self, other):
        return self._set_ope(other, "({}|{})", OperationType.OR)

    def _event_ope__or_once__(self, other):
        return self._set_ope(other, "({}||{})", OperationType.OR_ONCE)

    def _event_ope__invert__(self):
        return self._set_ope(self, "(~({}))", OperationType.INVERT)

    def _event_ope__edge_once__(self):
        return self._set_ope(self, "(+({}))", OperationType.EDGE_ONCE)

    def _event_ope__eq__(self, other):
        return self._set_ope(other, "({}=={})", OperationType.EQ)

    def _event_ope__ne__(self, other):
        return self._set_ope(other, "({}!={})", OperationType.NE)

    def _event_ope__gt__(self, other):
        return self._set_ope(other, "({}>{})", OperationType.GT)

    def _event_ope__ge__(self, other):
        return self._set_ope(other, "({}>={})", OperationType.GE)

    def _event_ope__lt__(self, other):
        return self._set_ope(other, "({}<{})", OperationType.LT)

    def _event_ope__le__(self, other):
        return self._set_ope(other, "({}<={})", OperationType.LE)

    def _event_ope__add__(self, other):
        return self._set_ope(other, "({}+{})", OperationType.ADD)

    def _event_ope__sub__(self, other):
        return self._set_ope(other, "({}-{})", OperationType.SUB)

    def _event_ope__mul__(self, other):
        return self._set_ope(other, "({}*{})", OperationType.MUL)

    def _event_ope__truediv__(self, other):
        return self._set_ope(other, "({}/{})", OperationType.DIV)

    def _set_ope_invert(self, myself, other, new_name_base, ope_type):
        new_name = new_name_base.format(myself.get_name())
        if hasattr(myself, "virtual_event_set"):
            virtual_event_set = myself.virtual_event_set
            return VirtualEvent(
                new_name,
                child_a=myself,
                child_b=None,
                operation=ope_type,
                virtual_event_set=virtual_event_set,
            )
        else:
            return Event(
                new_name,
                child_a=myself,
                child_b=None,
                operation=ope_type,
                base_name=new_name_base,
            )

    def _set_ope_edge_once(self, myself, other, new_name_base, ope_type):
        new_name = new_name_base.format(myself.get_name())
        if hasattr(myself, "virtual_event_set"):
            virtual_event_set = myself.virtual_event_set
            return VirtualEvent(
                new_name,
                child_a=myself,
                child_b=None,
                operation=ope_type,
                virtual_event_set=virtual_event_set,
            )
        else:
            return EdgeOnceEvent(None, child_a=myself, base_name=new_name_base)

    def _is_arith(self, ope_type):
        if ope_type in [
            OperationType.ADD,
            OperationType.SUB,
            OperationType.MUL,
            OperationType.DIV,
        ]:
            return True
        return False

    def _is_arith_or_eval(self, ope_type):
        if ope_type in [
            OperationType.EQ,
            OperationType.NE,
            OperationType.GT,
            OperationType.GE,
            OperationType.LT,
            OperationType.LE,
            OperationType.ADD,
            OperationType.SUB,
            OperationType.MUL,
            OperationType.DIV,
        ]:
            return True
        return False

    def _set_ope_arith(self, myself, other, new_name_base, ope_type):
        if not self._is_arith_or_eval(ope_type):
            raise ValueError(
                "ope_type '==', '!=', '>=', '<', '>', '+', '-', '*' , '/' are allowed"
            )

        other_name = "{}".format(other)
        other = Event(
            other_name,
            child_a=None,
            child_b=None,
            operation=None,
            calc_type=EventCalcType.ARITH,
            value=other,
            base_name=new_name_base,
        )

        new_name = new_name_base.format(myself.get_name(), other.get_name())
        if hasattr(myself, "virtual_event_set"):
            virtual_event_set = myself.virtual_event_set
            child_a = myself
            child_b = VirtualEvent(
                other.get_name(), virtual_event_set=virtual_event_set
            )
            child_b.set_event(other)
            return VirtualEvent(
                new_name,
                child_a=child_a,
                child_b=child_b,
                operation=ope_type,
                virtual_event_set=virtual_event_set,
            )
        else:
            child_a = myself
            child_b = other
            return Event(
                None,  # new_name,
                child_a=child_a,
                child_b=child_b,
                operation=ope_type,
                base_name=new_name_base,
            )

    def _set_ope(self, myself, other, new_name_base, ope_type):
        if ope_type == OperationType.INVERT:
            return myself._set_ope_invert(myself, other, new_name_base, ope_type)

        if ope_type == OperationType.EDGE_ONCE:
            return myself._set_ope_edge_once(myself, other, new_name_base, ope_type)

        if type(other) is int or type(other) is float:
            return myself._set_ope_arith(myself, other, new_name_base, ope_type)

        if not isinstance(other, EventOpe):
            raise ValueError(
                "class is not {} or subclass of {}".format(
                    EventOpe.__name__, EventOpe.__name__
                )
            )

        if (
            hasattr(myself, "virtual_event_set")
            and hasattr(other, "virtual_event_set")
            and myself.virtual_event_set != other.virtual_event_set
        ):
            raise ValueError("virtual event set must be same")

        new_name = new_name_base.format(myself.get_name(), other.get_name())

        if hasattr(myself, "virtual_event_set") and hasattr(other, "virtual_event_set"):
            virtual_event_set = myself.virtual_event_set
            child_a = myself
            child_b = other
            return VirtualEvent(
                new_name,
                child_a=myself,
                child_b=other,
                operation=ope_type,
                virtual_event_set=virtual_event_set,
            )

        if not hasattr(myself, "virtual_event_set") and not hasattr(
            other, "virtual_event_set"
        ):
            child_a = myself
            child_b = other
            if self._is_arith_or_eval(ope_type):
                calc_type = EventCalcType.ARITH
            else:
                calc_type = EventCalcType.BOOL
            return Event(
                None,  # new_name,
                child_a=child_a,
                child_b=child_b,
                operation=ope_type,
                calc_type=calc_type,
                base_name=new_name_base,
            )

        if hasattr(myself, "virtual_event_set") and not hasattr(
            other, "virtual_event_set"
        ):
            virtual_event_set = myself.virtual_event_set
            child_a = myself
            child_b = VirtualEvent(
                other.get_name(), virtual_event_set=virtual_event_set
            )
            child_b.set_event(other)
            return VirtualEvent(
                new_name,
                child_a=child_a,
                child_b=child_b,
                operation=ope_type,
                virtual_event_set=virtual_event_set,
            )

        if not hasattr(myself, "virtual_event_set") and hasattr(
            other, "virtual_event_set"
        ):
            virtual_event_set = other.virtual_event_set
            child_b = other
            child_a = VirtualEvent(
                myself.get_name(), virtual_event_set=virtual_event_set
            )
            child_a.set_event(myself)
            return VirtualEvent(
                new_name,
                child_a=child_a,
                child_b=child_b,
                operation=ope_type,
                virtual_event_set=virtual_event_set,
            )


class EventBoolOpe(EventOpe):
    def __and__(self, other):
        return self._event_ope__and__(other)

    def __or__(self, other):
        return self._event_ope__or__(other)

    def __xor__(self, other):
        return self._event_ope__or_once__(other)

    def __invert__(self):
        return self._event_ope__invert__()

    def __pos__(self):
        return self._event_ope__edge_once__()

    def _set_ope(self, other, new_name_base, ope_type):
        return super()._set_ope(self, other, new_name_base, ope_type)


class EventArithOpe(EventOpe):
    def __eq__(self, other):
        return self._event_ope__eq__(other)

    def __ne__(self, other):
        return self._event_ope__ne__(other)

    def __gt__(self, other):
        return self._event_ope__gt__(other)

    def __ge__(self, other):
        return self._event_ope__ge__(other)

    def __lt__(self, other):
        return self._event_ope__lt__(other)

    def __le__(self, other):
        return self._event_ope__le__(other)

    def __add__(self, other):
        return self._event_ope__add__(other)

    def __sub__(self, other):
        return self._event_ope__sub__(other)

    def __mul__(self, other):
        return self._event_ope__mul__(other)

    def __truediv__(self, other):
        return self._event_ope__truediv__(other)

    def _set_ope(self, other, new_name_base, ope_type):
        if type(other) is int or type(other) is float:
            ret = super()._set_ope(self.event, other, new_name_base, ope_type)
        else:
            ret = super()._set_ope(self.event, other.event, new_name_base, ope_type)
        if self._is_arith(ope_type):
            return ret.value()
        return ret


class EventValue(EventArithOpe):
    def __init__(self, event):
        self.event = event

    def get_name(self):
        return self.event.get_name()


class Event(EventBoolOpe):
    def __init__(
        self,
        name,
        child_a=None,
        child_b=None,
        operation=None,
        calc_type=EventCalcType.BOOL,
        value=None,
        dummy_flag=False,
        base_name=None,
    ):
        self.name = name
        self.event_log_name = None
        self.base_name = base_name
        self.event_formula = None
        self.child_a = child_a
        self.child_b = child_b
        self.operation = operation
        self.start_time = None
        self.event_for_notify_change = dict()
        self.event_for_notify_stop = dict()
        self.replay_logger = None
        self.log_store = None
        self.calc_type = calc_type
        self.real_value = value
        self.dummy_flag = dummy_flag
        self._init_ope()

    def _self_set_replay_logger(self, replay_logger):
        self.replay_logger = replay_logger

    def _set_replay_logger(self, replay_logger):
        if hasattr(self, "child_a") and self.child_a is not None:
            self.child_a._set_replay_logger(replay_logger)
        if hasattr(self, "child_b") and self.child_b is not None:
            self.child_b._set_replay_logger(replay_logger)
        self._self_set_replay_logger(replay_logger)

    def _self_set_log_store(self, log_store):
        self.log_store = log_store

    def _set_log_store(self, log_store):
        if hasattr(self, "child_a") and self.child_a is not None:
            self.child_a._set_log_store(log_store)
        if hasattr(self, "child_b") and self.child_b is not None:
            self.child_b._set_log_store(log_store)
        self._self_set_log_store(log_store)

    # dummy
    def _self_set_state_machine_list(self, state_machine_list):
        pass

    def _set_state_machine_list(self, state_machine_list):
        if hasattr(self, "child_a") and self.child_a is not None:
            self.child_a._set_state_machine_list(state_machine_list)
        if hasattr(self, "child_b") and self.child_b is not None:
            self.child_b._set_state_machine_list(state_machine_list)
        self._self_set_state_machine_list(state_machine_list)

    def _self_init_state_machine_value(self):
        pass

    def _init_state_machine_value(self):
        if hasattr(self, "child_a") and self.child_a is not None:
            self.child_a._init_state_machine_value()
        if hasattr(self, "child_b") and self.child_b is not None:
            self.child_b._init_state_machine_value()
        self._self_init_state_machine_value()

    # evaluation of Event Formula
    def value(self):
        if not hasattr(self, "event_value"):
            self.event_value = EventValue(self)
            return self.event_value
        return self.event_value

    def _set_event_for_notify_change(self, event):
        self.event_for_notify_change[event.name] = event

    def _set_event_for_notify_stop(self, event):
        self.event_for_notify_stop[event.name] = event

    def _init(self):
        if hasattr(self, "child_a") and self.child_a is not None:
            self.child_a._init()
        if hasattr(self, "child_b") and self.child_b is not None:
            self.child_b._init()

    def _self_set_start_time(self, start_time):
        self.start_time = start_time

    def _set_start_time(self, start_time):
        if hasattr(self, "child_a") and self.child_a is not None:
            self.child_a._set_start_time(start_time)
        if hasattr(self, "child_b") and self.child_b is not None:
            self.child_b._set_start_time(start_time)
        self._self_set_start_time(start_time)

    def get_name(self):
        if self.name is not None:
            return self.name
        child_a_name = None
        child_b_name = None
        if hasattr(self, "child_a") and self.child_a is not None:
            child_a_name = self.child_a.get_name()
        if hasattr(self, "child_b") and self.child_b is not None:
            child_b_name = self.child_b.get_name()
        return self.base_name.format(child_a_name, child_b_name)

    def get_event_formula(self, func=None):
        if isinstance(self, TriggerControllableEvent) and not isinstance(
            self, EdgeOnceEvent
        ):
            if func is None:
                return self.name
            else:
                return func(self.name)
        if hasattr(self, "real_value") and self.real_value is not None:
            if func is None:
                return self.name
            else:
                return func(self.name)
        child_a_name = None
        child_b_name = None
        if hasattr(self, "child_a") and self.child_a is not None:
            child_a_name = self.child_a.get_event_formula(func)
        if hasattr(self, "child_b") and self.child_b is not None:
            child_b_name = self.child_b.get_event_formula(func)
        return self.base_name.format(child_a_name, child_b_name)

    def get_info(self):
        return "", None

    def _get_event_to_notify(self):
        return self

    def set_name(self, name):
        self.name = name
        self.event_log_name = name

    def get_event_log_name(self):
        return self.name

    def _fix_name(self):
        if hasattr(self, "child_a") and self.child_a is not None:
            self.child_a._fix_name()
        if hasattr(self, "child_b") and self.child_b is not None:
            self.child_b._fix_name()
        if self.name is None:
            self.name = self.get_name()
        if self.event_log_name is None:
            self.event_log_name = self.get_event_log_name()
        self.event_formula = self.get_event_formula()

    def check(self, event_seq=None):
        if event_seq is None:
            event_seq = []
        event_seq.append(self)
        if hasattr(self, "child_a") and self.child_a is not None:
            self.child_a.check(event_seq)
        if hasattr(self, "child_b") and self.child_b is not None:
            self.child_b.check(event_seq)
        event_seq.pop()

    def _get_all_event(self, event_set):
        if hasattr(self, "child_a") and self.child_a is not None:
            self.child_a._get_all_event(event_set)
        if hasattr(self, "child_b") and self.child_b is not None:
            self.child_b._get_all_event(event_set)
        event_set.add(self)

    def get_log_info_event(self, event_set):
        tmp_event_set = set()
        self._get_all_event(tmp_event_set)
        for event in tmp_event_set:
            if hasattr(event, "operation") and event._is_arith(event.operation):
                continue
            if hasattr(event, "real_value") and event.real_value is not None:
                continue
            event_set.add(event)

    def _get_node_event(self, event_set):
        if hasattr(self, "child_a") and self.child_a is not None:
            self.child_a._get_node_event(event_set)
        if hasattr(self, "child_b") and self.child_b is not None:
            self.child_b._get_node_event(event_set)
        if isinstance(self, TriggerControllableEvent):
            event_set.add(self)

    def _get_event_raise_time(self, current_time, parameter, state_machine):
        if hasattr(self, "calc_type") and self.calc_type == EventCalcType.ARITH:
            return True

        if self.operation == OperationType.AND:
            time_a = self.child_a._get_event_raise_time(
                current_time, parameter, state_machine
            )
            time_b = self.child_b._get_event_raise_time(
                current_time, parameter, state_machine
            )
            # "AND" operation's priority:
            #  False > None > datetime > True.

            # "AND" operation returns if both are None,
            #  - None
            if time_a is None and time_b is None:
                return None
            # "AND" operation returns if one is None and the other is bool,
            #  - False if bool is False,
            #  - None if bool is True.
            if time_a is None and type(time_b) is bool:
                return time_a if time_b else time_b
            if type(time_a) is bool and time_b is None:
                return time_b if time_a else time_a
            # "AND" operation returns if one is None and the other is datetime,
            #  - None
            if time_a is None and isinstance(time_b, datetime.datetime):
                return time_a
            if isinstance(time_a, datetime.datetime) and time_b is None:
                return time_b
            # "AND" operation returns if both are bool,
            #  - bool result
            if type(time_a) is bool and type(time_b) is bool:
                return time_a and time_b
            # "AND" operation returns if one is bool and the other is datetime,
            #  - False if bool is False,
            #  - datetime if bool is True.
            if type(time_a) is bool and isinstance(time_b, datetime.datetime):
                return time_b if time_a else time_a
            if isinstance(time_a, datetime.datetime) and type(time_b) is bool:
                return time_a if time_b else time_b
            # "AND" operation returns if both are datetime,
            #  - later datetime
            if isinstance(time_a, datetime.datetime) and isinstance(
                time_b, datetime.datetime
            ):
                return max(time_a, time_b)
            raise ValueError("raise parameter must be None, boolean or datetime")

        if (
            self.operation == OperationType.OR
            or self.operation == OperationType.OR_ONCE
        ):  # "or"
            time_a = self.child_a._get_event_raise_time(
                current_time, parameter, state_machine
            )
            time_b = self.child_b._get_event_raise_time(
                current_time, parameter, state_machine
            )
            # "OR" operation's priority:
            #  True > datetime > None > False.

            # "OR" operation returns if both are None,
            #  - None
            if time_a is None and time_b is None:
                return None
            # "OR" operation returns if one is None and the other is bool,
            #  - True if bool is True,
            #  - None if bool is False.
            if time_a is None and type(time_b) is bool:
                return time_b if time_b else time_a
            if type(time_a) is bool and time_b is None:
                return time_a if time_a else time_b
            # "OR" operation returns if one is None and the other is datetime,
            #  - datetime
            if time_a is None and isinstance(time_b, datetime.datetime):
                return time_b
            if isinstance(time_a, datetime.datetime) and time_b is None:
                return time_a
            # "OR" operation returns if both are bool,
            #  - bool result
            if type(time_a) is bool and type(time_b) is bool:
                return time_a or time_b
            # "OR" operation returns if one is bool and the other is datetime,
            #  - True if bool is True,
            #  - datetime if bool is False.
            if type(time_a) is bool and isinstance(time_b, datetime.datetime):
                return time_a if time_a else time_b
            if isinstance(time_a, datetime.datetime) and type(time_b) is bool:
                return time_b if time_b else time_a
            # "OR" operation returns if both are datetime,
            #  - earlier datetime
            if isinstance(time_a, datetime.datetime) and isinstance(
                time_b, datetime.datetime
            ):
                return min(time_a, time_b)
            raise ValueError("raise parameter must be None, boolean or datetime")

        if self.operation == OperationType.INVERT:  # "invert"
            time_a = self.child_a._get_event_raise_time(
                current_time, parameter, state_machine
            )
            if time_a is None:
                return None
            if type(time_a) is bool:
                return not time_a
            if isinstance(time_a, datetime.datetime):
                return time_a
            raise ValueError("raise parameter must be None, boolean or datetime")

        if self._is_arith_or_eval(self.operation):
            time_a = self.child_a._get_event_raise_time(
                current_time, parameter, state_machine
            )
            time_b = self.child_b._get_event_raise_time(
                current_time, parameter, state_machine
            )
            # "ARITH" operation's priority:
            #  datetime > None > True/False.
            # "ARITH" operation returns if both are None,
            #  - None
            if time_a is None and time_b is None:
                return None
            # "ARITH" operation returns if one is None and the other is bool,
            #  - None
            if time_a is None and type(time_b) is bool:
                return time_a
            if type(time_a) is bool and time_b is None:
                return time_b
            # "ARITH" operation returns if one is None and the other is datetime,
            #  - datetime
            if time_a is None and isinstance(time_b, datetime.datetime):
                return time_b
            if isinstance(time_a, datetime.datetime) and time_b is None:
                return time_a
            # "ARITH" operation returns if both are bool,
            #  - bool result
            if type(time_a) is bool and type(time_b) is bool:
                return time_a or time_b
            # "ARITH" operation returns if one is bool and the other is datetime,
            #  - datetime
            if type(time_a) is bool and isinstance(time_b, datetime.datetime):
                return time_b
            if isinstance(time_a, datetime.datetime) and type(time_b) is bool:
                return time_a
            # "ARITH" operation returns if both are datetime,
            #  - earlier datetime
            if isinstance(time_a, datetime.datetime) and isinstance(
                time_b, datetime.datetime
            ):
                return min(time_a, time_b)
            raise ValueError("raise parameter must be None, boolean or datetime")

        raise ValueError('operation must be "and", "or" or "invert"')

    def _eval_event_calc(self, current_time, parameter, state_machine):
        if not hasattr(self, "calc_type"):
            # no operation is specified.
            # return event raise(1) or not(0).
            return (
                1
                if self._is_event_raise(
                    current_time, parameter, state_machine, log_flag=True
                )
                else 0
            )
        if self.operation == OperationType.ADD:  # "+"
            return self.child_a._eval_event_calc(
                current_time, parameter, state_machine
            ) + self.child_b._eval_event_calc(current_time, parameter, state_machine)
        if self.operation == OperationType.SUB:  # "-"
            return self.child_a._eval_event_calc(
                current_time, parameter, state_machine
            ) - self.child_b._eval_event_calc(current_time, parameter, state_machine)
        if self.operation == OperationType.MUL:  # "*"
            return self.child_a._eval_event_calc(
                current_time, parameter, state_machine
            ) * self.child_b._eval_event_calc(current_time, parameter, state_machine)
        if self.operation == OperationType.DIV:  # "/"
            return self.child_a._eval_event_calc(
                current_time, parameter, state_machine
            ) / self.child_b._eval_event_calc(current_time, parameter, state_machine)
        if self.calc_type == EventCalcType.BOOL:
            return (
                1
                if self._is_event_raise(
                    current_time, parameter, state_machine, log_flag=True
                )
                else 0
            )
        if self.calc_type == EventCalcType.ARITH:
            return self.real_value
        raise ValueError("calc_type error: {}".format(self.calc_type))

    def _is_event_raise_main(self, current_time, parameter, state_machine):
        if self.operation == OperationType.AND:  # "and"
            return self.child_a._is_event_raise(
                current_time, parameter, state_machine
            ) and self.child_b._is_event_raise(current_time, parameter, state_machine)
        if (
            self.operation == OperationType.OR
            or self.operation == OperationType.OR_ONCE
        ):  # "or"
            return self.child_a._is_event_raise(
                current_time, parameter, state_machine
            ) or self.child_b._is_event_raise(current_time, parameter, state_machine)
        if self.operation == OperationType.INVERT:  # "invert"
            return not self.child_a._is_event_raise(
                current_time, parameter, state_machine
            )
        if self.operation == OperationType.EQ:  # "=="
            return self.child_a._eval_event_calc(
                current_time, parameter, state_machine
            ) == self.child_b._eval_event_calc(current_time, parameter, state_machine)
        if self.operation == OperationType.NE:  # "!="
            return self.child_a._eval_event_calc(
                current_time, parameter, state_machine
            ) != self.child_b._eval_event_calc(current_time, parameter, state_machine)
        if self.operation == OperationType.GT:  # ">"
            return self.child_a._eval_event_calc(
                current_time, parameter, state_machine
            ) > self.child_b._eval_event_calc(current_time, parameter, state_machine)
        if self.operation == OperationType.GE:  # ">="
            return self.child_a._eval_event_calc(
                current_time, parameter, state_machine
            ) >= self.child_b._eval_event_calc(current_time, parameter, state_machine)
        if self.operation == OperationType.LT:  # "<"
            return self.child_a._eval_event_calc(
                current_time, parameter, state_machine
            ) < self.child_b._eval_event_calc(current_time, parameter, state_machine)
        if self.operation == OperationType.LE:  # "<="
            return self.child_a._eval_event_calc(
                current_time, parameter, state_machine
            ) <= self.child_b._eval_event_calc(current_time, parameter, state_machine)
        raise ValueError(
            'event name={}, calc_type {}, operation {}, must be "and", "or" or "invert"'.format(
                self.name, self.calc_type, self.operation
            )
        )

    def _is_event_raise(self, current_time, parameter, state_machine, log_flag=True):
        is_event_raise_flag = self._is_event_raise_main(
            current_time, parameter, state_machine
        )
        if log_flag and self.log_store is not None:
            self.log_store.update_detail_event(current_time, self, is_event_raise_flag)
        return is_event_raise_flag

    def _update_event_parameter_change(self, current_time, parameter):
        pass

    def _update_event_parameter_stop(self, current_time, parameter):
        pass

    def _update_state_machine_value(
        self, current_time, parameter, state_machine, event_raise_flag
    ):
        if (
            self.calc_type != EventCalcType.ARITH
            and self._is_event_raise_main(current_time, parameter, state_machine)
            != event_raise_flag
        ):
            return False
        if self.real_value is not None:
            return False
        if self.operation == OperationType.AND:  # "and"
            # event_raise_flag = True
            #  case1: child_a is True  -> update
            #     and child_b is True  -> update
            # event_raise_flag = False
            #  case1: child_a is False -> update
            #     and child_b is True  -> no update
            #  case2: child_a is True  -> no update
            #     and child_b is False -> update
            #  case3: child_a is False -> update
            #     and child_b is False -> update
            res_a = self.child_a._update_state_machine_value(
                current_time, parameter, state_machine, event_raise_flag
            )
            res_b = self.child_b._update_state_machine_value(
                current_time, parameter, state_machine, event_raise_flag
            )
            return res_a or res_b
        if self.operation == OperationType.OR:  # "or"
            # event_raise_flag = False
            #  case1: child_a is False -> update
            #     and child_b is False -> update
            # event_raise_flag = True
            #  case1: child_a is False -> no update
            #     and child_b is True  -> update
            #  case2: child_a is True  -> update
            #     and child_b is False -> no update
            #  case3: child_a is True  -> update
            #     and child_b is True  -> update (OR)
            res_a = self.child_a._update_state_machine_value(
                current_time, parameter, state_machine, event_raise_flag
            )
            res_b = self.child_b._update_state_machine_value(
                current_time, parameter, state_machine, event_raise_flag
            )
            return res_a or res_b
        if self.operation == OperationType.OR_ONCE:  # "or_once"
            # event_raise_flag = False
            #  case1: child_a is False -> update
            #     and child_b is False -> update
            # event_raise_flag = True
            #  case1: child_a is False -> no update
            #     and child_b is True  -> update
            #  case2: child_a is True  -> update
            #     and child_b is False -> no update
            #  case3: child_a is True  -> update
            #     and child_b is True  -> no update (OR_ONCE)
            res_a = self.child_a._update_state_machine_value(
                current_time, parameter, state_machine, event_raise_flag
            )
            if event_raise_flag and res_a:
                return res_a
            res_b = self.child_b._update_state_machine_value(
                current_time, parameter, state_machine, event_raise_flag
            )
            return res_a or res_b
        if self.operation == OperationType.INVERT:  # "invert"
            res_a = self.child_a._update_state_machine_value(
                current_time, parameter, state_machine, not event_raise_flag
            )
            return res_a
        if self._is_arith_or_eval(self.operation):
            res_a = self.child_a._update_state_machine_value(
                current_time, parameter, state_machine, True
            )
            res_b = self.child_b._update_state_machine_value(
                current_time, parameter, state_machine, True
            )
            return res_a or res_b
        raise ValueError(
            'event name={}, operation {} must be "and", "or" or "invert"'.format(
                self.name, self.operation
            )
        )

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

    def _update_detail_event(
        self, current_time, event, is_event_raise_flag=None, append_flag=True
    ):
        if self.log_store is not None:
            self.log_store.update_detail_event(current_time, event)

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


class TriggerControllableEvent(Event):
    def __init__(
        self,
        event_type=EventType.LEVEL,
        event_trigger_type=EventTriggerType.NOLIMIT,
    ):
        self.event_type = event_type
        self.event_trigger_type = event_trigger_type
        super()._init_ope()

    def _self_set_state_machine_list(self, state_machine_list):
        self.state_machine_list = state_machine_list
        self.state_machine_value_dict = {}
        self._self_init_state_machine_value()

    def _self_init_state_machine_value(self):
        self.state_machine_value_dict.clear()
        for sm in self.state_machine_list:
            self.state_machine_value_dict[sm] = 0

    def _update_state_machine_value(self, result, state_machine):
        if (
            self.event_type != EventType.EDGE
            or self.event_trigger_type != EventTriggerType.ONCE
        ):
            return False
        sim_log.info(
            "event={}, result={}, state_machine={}".format(
                self.name, result, state_machine.name
            )
        )
        if result:
            self.state_machine_value_dict[state_machine] += 1
            return True
        return False

    def _get_event_raise_time(self, result, state_machine):
        if (
            self.event_type != EventType.EDGE
            or self.event_trigger_type != EventTriggerType.ONCE
        ):
            return result
        if type(result) is bool:
            if self.state_machine_value_dict[state_machine] == 0:
                return result
            return False
        return result

    def _is_event_raise(self, current_time, result, state_machine, log_flag=True):
        if log_flag and self.log_store is not None:
            self.log_store.update_detail_event(current_time, self, result)
        if (
            self.event_type != EventType.EDGE
            or self.event_trigger_type != EventTriggerType.ONCE
        ):
            sim_log.info("result={}".format(result))
            return result
        sim_log.info(
            "state_machine={}, dict={}".format(
                state_machine.name, self.state_machine_value_dict
            )
        )
        if state_machine is None or self.state_machine_value_dict[state_machine] == 0:
            sim_log.info("result={}".format(result))
            return result
        sim_log.info("result={}".format(False))
        return False


class EdgeOnceEvent(TriggerControllableEvent):
    def __init__(
        self,
        name,
        child_a,
        base_name=None,
    ):
        super().__init__(EventType.EDGE, EventTriggerType.ONCE)
        self.name = name
        self.event_log_name = None
        self.base_name = base_name
        self.event_formula = None
        self.child_a = child_a
        self.event_for_notify_change = dict()
        self.event_for_notify_stop = dict()
        self._init()

    def _init(self):
        self._reset()
        if hasattr(self, "child_a") and self.child_a is not None:
            self.child_a._init()

    def _reset(self):
        self.done_time = None

    def _get_event_raise_time(self, current_time, parameter, state_machine):
        return super()._get_event_raise_time(
            self.child_a._get_event_raise_time(current_time, parameter, state_machine),
            state_machine,
        )

    def _is_event_raise_main(self, current_time, parameter, state_machine, log_flag):
        done = self.child_a._is_event_raise(
            current_time,
            parameter,
            state_machine,
            log_flag,
        )
        sim_log.info(
            "EdgeOnceEvent({}), child_a={}, done={}, done_time={}".format(
                self.name, self.child_a.name, done, self.done_time
            )
        )
        if done:
            if self.done_time is None:
                self.done_time = current_time
                return done
            if self.done_time != current_time:
                return False
        else:
            self._reset()
        return done

    def _is_event_raise(self, current_time, parameter, state_machine, log_flag=True):
        is_event_raise_flag = self._is_event_raise_main(
            current_time, parameter, state_machine, log_flag
        )
        result = super()._is_event_raise(
            current_time, is_event_raise_flag, state_machine, log_flag
        )
        sim_log.info(
            "EdgeOnceEvent({}), raise={}, result={}".format(
                self.name, is_event_raise_flag, result
            )
        )
        return result

    def _update_state_machine_value(
        self, current_time, parameter, state_machine, event_raise_flag
    ):
        result = self._is_event_raise(
            current_time, parameter, state_machine, log_flag=False
        )
        if result == event_raise_flag:
            return super()._update_state_machine_value(result, state_machine)
        return False


class ResettableEvent(TriggerControllableEvent):
    def __init__(
        self,
        name,
        start_state_or_event,
        notify_type,
        stop_state_or_event=None,
        stop_and_reset_flag=False,
        event_type=EventType.LEVEL,
        event_trigger_type=EventTriggerType.NOLIMIT,
    ):
        super().__init__(event_type, event_trigger_type)
        self.name = name
        self.event_log_name = None
        self.base_name = None
        self.event_formula = None
        self._set_start_state_or_event(start_state_or_event)
        self._set_stop_state_or_event(stop_state_or_event)
        self.stop_and_reset_flag = stop_and_reset_flag
        self.event_for_notify_change = dict()
        self.event_for_notify_stop = dict()
        self.notify_type = notify_type
        self.replay_logger = None
        self.log_store = None

    def _set_start_state_or_event(self, start_state_or_event):
        if hasattr(start_state_or_event, "_add_resettable_event_for_set_start_event"):
            start_state_or_event._add_resettable_event_for_set_start_event(self)
            self.start_state_or_event = start_state_or_event  # virtual event
        else:
            self.start_state_or_event = start_state_or_event

    def _set_stop_state_or_event(self, stop_state_or_event):
        if hasattr(stop_state_or_event, "_add_resettable_event_for_set_stop_event"):
            stop_state_or_event._add_resettable_event_for_set_stop_event(self)
            self.stop_state_or_event = stop_state_or_event  # virtual event
        else:
            self.stop_state_or_event = stop_state_or_event

    def set_start_event(self, event):
        self.start_state_or_event = event

    def set_stop_event(self, event):
        self.stop_state_or_event = event

    def _init(self):
        self.done_time = None
        self.start_time = None
        self.event_raise_time = None
        self.event_decision = None
        if self.start_state_or_event is None:
            self.active = True
        else:
            self.active = False

    def _update_event_parameter_change(self, current_time, parameter):
        sim_log.info(
            "current_time={}, ResettableEvent({}), parameter={}".format(
                current_time, self.name, parameter
            )
        )
        if self.start_state_or_event is not None:
            self.active = True

        if self.active == False:
            return

        if self.done_time is not None:
            self.event_raise_time = None
            self.done_time = None

        self._update_event_parameter(current_time, parameter)

    def _update_event_parameter_stop(self, current_time, parameter):
        self.active = False


class VirtualEvent(EventBoolOpe):
    def __init__(
        self, name, child_a=None, child_b=None, operation=None, virtual_event_set=None
    ):
        self.name = name
        self.child_a = child_a
        self.child_b = child_b
        self.operation = operation
        self.virtual_event_set = virtual_event_set
        self.uuid = uuid.uuid4()  # for checking loop
        tool_log.debug("VirtualEvent[{}] uuid={}".format(self.name, self.uuid))
        self.trigger_set = set()
        self.arbitrator_set = set()
        self.resettable_event_start_set = set()
        self.resettable_event_stop_set = set()
        self.state_machine_reset_set = set()
        self.state_machine_drop_set = set()
        self.this_event = None
        self.already_set = False
        self.is_real_event = False
        self.real_event = None
        self.event_name = None
        if virtual_event_set is not None:
            virtual_event_set._register_virtual_event(self)
        else:
            print("Error? virtual_event_set is None")
        self._init_ope()

    def _init(self):
        if hasattr(self, "child_a") and self.child_a is not None:
            self.child_a._init()
        if hasattr(self, "child_b") and self.child_b is not None:
            self.child_b._init()
        self.this_event = None
        self.already_set = False

    def value(self):
        if not hasattr(self, "event_value"):
            self.event_value = EventValue(self)
            return self.event_value
        return self.event_value

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def set_event(self, event):
        self.is_real_event = True
        self.real_event = event
        self.set_name(event.get_name())

    def get_event_name(self):
        return self.event_name

    def set_event_name(self, event_name):
        self.event_name = event_name

    def get_event_to_modify_name(self, raise_error_flag=True):
        return self._get_event([], raise_error_flag=raise_error_flag)

    def modify_event_name(self, raise_error_flag=True):
        event_name = self.get_event_name()
        if event_name is not None:
            event = self.get_event_to_modify_name(raise_error_flag=raise_error_flag)
            tool_log.debug(
                "VirtualEvent[{}] event name '{}' -> '{}'".format(
                    self.name, event.get_name(), event_name
                )
            )
            event.set_name(event_name)

    def _get_ope_event(self, child_a, child_b, ope_type, event_stack, raise_error_flag):
        event_a = self.child_a._get_event(
            event_stack, raise_error_flag=raise_error_flag
        )
        ope = event_a.ope_dict.get(ope_type)
        if ope is None:
            return None
        if child_b is not None:
            event_b = self.child_b._get_event(
                event_stack, raise_error_flag=raise_error_flag
            )
            return ope(event_b)
        return ope()

    def get_log_info_event(self, event_set):
        sim_log.info("VirtualEvent[{}] is not assigned".format(self.name))

    # for getting real Event
    def _get_event(self, event_stack=[], raise_error_flag=True):
        if self.this_event is not None:
            return self.this_event
        if self.is_real_event:
            event = self.real_event
            tool_log.debug(
                "VirtualEvent[{}] event = '{}'".format(self.name, event.name)
            )
            self.this_event = event
            return event
        if self.uuid in event_stack:
            tool_log.debug("uuid={}, event_stack={}".format(self.uuid, event_stack))
            raise ValueError("event evaluation looping")
        if self.child_a is None and self.child_b is None:
            if raise_error_flag:
                raise ValueError("VirtualEvent[{}] event is not set".format(self.name))
            return self
        event_stack.append(self.uuid)
        if self.operation is None:
            if self.child_a is not None and self.child_b is None:
                event = self.child_a._get_event(
                    event_stack, raise_error_flag=raise_error_flag
                )
                tool_log.debug(
                    "VirtualEvent[{}] event = '{}'".format(self.name, event.name)
                )
                self.this_event = event
                event_stack.pop()
                return event
            if self.child_a is None and self.child_b is not None:
                event = self.child_b._get_event(
                    event_stack, raise_error_flag=raise_error_flag
                )
                tool_log.debug(
                    "VirtualEvent[{}] event = '{}'".format(self.name, event.name)
                )
                self.this_event = event
                event_stack.pop()
                return event
        event = self._get_ope_event(
            self.child_a, self.child_b, self.operation, event_stack, raise_error_flag
        )
        if event is not None:
            tool_log.debug(
                "VirtualEvent[{}] event = '{}'".format(self.name, event.name)
            )
            self.this_event = event
            event_stack.pop()
            return event
        if self.operation == OperationType.DUMMY:  # "dummy"
            event = self.child_a._get_event(
                event_stack, raise_error_flag=raise_error_flag
            )
            tool_log.debug(
                "VirtualEvent[{}] event = '{}'".format(self.name, event.name)
            )
            self.this_event = event
            event_stack.pop()
            return event
        raise ValueError("event is not set")

    def _add_trigger_for_set_event(self, trigger):
        if (
            hasattr(trigger, "event")
            and trigger.event is not None
            and hasattr(trigger.event, "_add_trigger_for_set_event")
        ):
            trigger.event.trigger_set.remove(trigger)
        self.trigger_set.add(trigger)

    def _add_arbitrator_for_set_event(self, arbitrator):
        if (
            hasattr(arbitrator, "schedule_event")
            and arbitrator.schedule_event is not None
            and hasattr(arbitrator.schedule_event, "_add_arbitrator_for_set_event")
        ):
            arbitrator.schedule_event.arbitrator_set.remove(arbitrator)
        self.arbitrator_set.add(arbitrator)

    def _add_resettable_event_for_set_start_event(self, event):
        # event is resettable event and start_state_or_event of event is VirtualEvent
        if (
            hasattr(event, "start_state_or_event")
            and event.start_state_or_event is not None
            and hasattr(
                event.start_state_or_event, "_add_resettable_event_for_set_start_event"
            )
        ):
            # remove registerd resettable event in old start_state_or_event
            event.start_state_or_event.resettable_event_start_set.remove(event)
        # register resettable event in new start_state_or_event (self)
        self.resettable_event_start_set.add(event)

    def _add_resettable_event_for_set_stop_event(self, event):
        if (
            hasattr(event, "stop_state_or_event")
            and event.stop_state_or_event is not None
            and hasattr(
                event.stop_state_or_event, "_add_resettable_event_for_set_stop_event"
            )
        ):
            event.stop_state_or_event.resettable_event_stop_set.remove(event)
        self.resettable_event_stop_set.add(event)

    def _add_state_machine_for_set_reset_event(self, state_machine):
        if (
            hasattr(state_machine, "reset_event")
            and state_machine.reset_event is not None
            and hasattr(
                state_machine.reset_event, "_add_state_machine_for_set_reset_event"
            )
        ):
            state_machine.reset_event.state_machine_reset_set.remove(state_machine)
        self.state_machine_reset_set.add(state_machine)

    def _add_state_machine_for_set_drop_event(self, state_machine):
        if (
            hasattr(state_machine, "drop_event")
            and state_machine.drop_event is not None
            and hasattr(
                state_machine.drop_event, "_add_state_machine_for_set_drop_event"
            )
        ):
            state_machine.drop_event.state_machine_drop_set.remove(state_machine)
        self.state_machine_drop_set.add(state_machine)

    def _set_trigger_event(self, raise_error_flag=True):
        event = self._get_event([], raise_error_flag=raise_error_flag)
        trigger_list = list(self.trigger_set)
        for trigger in trigger_list:
            tool_log.debug(
                "VirtualEvent[{}] Trigger['{}']._set_trigger_event(event = '{}')".format(
                    self.name, trigger.name, event.name
                )
            )
            trigger.set_event(event)

    def _set_arbitrator_event(self, raise_error_flag=True):
        event = self._get_event([], raise_error_flag=raise_error_flag)
        arbitrator_list = list(self.arbitrator_set)
        for arbitrator in arbitrator_list:
            tool_log.debug(
                "VirtualEvent[{}] Arbitrator['{}']._set_arbitrator_event(event = '{}')".format(
                    self.name, arbitrator.name, event.name
                )
            )
            arbitrator.set_event(event)

    def _set_resettable_event_event(self, raise_error_flag=True):
        event = self._get_event([], raise_error_flag=raise_error_flag)
        resettable_event_list = list(self.resettable_event_start_set)
        for resettable_event in resettable_event_list:
            tool_log.debug(
                "VirtualEvent[{}] TimerEvent['{}']._set_resettable_event_event(event = '{}')".format(
                    self.name, resettable_event.name, event.name
                )
            )
            resettable_event.set_start_event(event)
        resettable_event_list = list(self.resettable_event_stop_set)
        for resettable_event in resettable_event_list:
            tool_log.debug(
                "VirtualEvent[{}] TimerEvent['{}']._set_resettable_event_event(event = '{}')".format(
                    self.name, resettable_event.name, event.name
                )
            )
            resettable_event.set_stop_event(event)

    def _set_state_machine_reset_event(self, raise_error_flag=True):
        event = self._get_event([], raise_error_flag=raise_error_flag)
        state_machine_reset_list = list(self.state_machine_reset_set)
        for state_machine in state_machine_reset_list:
            tool_log.debug(
                "VirtualEvent[{}] StateMachine['{}']._set_state_machine_reset_event(event = '{}')".format(
                    self.name, state_machine.name, event.name
                )
            )
            state_machine.set_reset_event(event)

    def _set_state_machine_drop_event(self, raise_error_flag=True):
        event = self._get_event([], raise_error_flag=raise_error_flag)
        state_machine_drop_list = list(self.state_machine_drop_set)
        for state_machine in state_machine_drop_list:
            tool_log.debug(
                "VirtualEvent[{}] StateMachine['{}']._set_state_machine_drop_event(event = '{}')".format(
                    self.name, state_machine.name, event.name
                )
            )
            state_machine.set_drop_event(event)

    def _set_local(self, raise_error_flag=True):
        if not self.already_set:
            tool_log.debug("VirtualEvent[{}].set()".format(self.name))
            self._set_trigger_event(raise_error_flag=raise_error_flag)
            self._set_arbitrator_event(raise_error_flag=raise_error_flag)
            self._set_resettable_event_event(raise_error_flag=raise_error_flag)
            self._set_state_machine_reset_event(raise_error_flag=raise_error_flag)
            self._set_state_machine_drop_event(raise_error_flag=raise_error_flag)
            self.already_set = True

    def set(self, event_stack=[], raise_error_flag=True):
        if self.uuid in event_stack:
            tool_log.debug("uuid={}, event_stack={}".format(self.uuid, event_stack))
            raise ValueError("event evaluation looping")
        event_stack.append(self.uuid)
        if self.child_a is not None:
            self.child_a.set(event_stack, raise_error_flag=raise_error_flag)
        if self.child_b is not None:
            self.child_b.set(event_stack, raise_error_flag=raise_error_flag)
        self._set_local(raise_error_flag=raise_error_flag)
        event_stack.pop()

    def event(self, random_event_child_name):
        return VirtualRandomEventChild(
            self.name,
            self,
            random_event_child_name,
            virtual_event_set=self.virtual_event_set,
        )


class VirtualRandomEventChild(VirtualEvent):
    def __init__(
        self, name, random_event_parent, random_event_child_name, virtual_event_set=None
    ):
        super().__init__(name, None, None, None, virtual_event_set)
        self.random_event_parent = random_event_parent
        self.random_event_child_name = random_event_child_name

    # for getting real Event
    def _get_event(self, event_stack, raise_error_flag=True):
        if self.this_event is None:
            if self.random_event_parent is None:
                raise ValueError("random_event_parent is not set")
            if self.random_event_child_name is None:
                raise ValueError("random_event_child_name is not set")
            event = self.random_event_parent._get_event(event_stack)
            self.this_event = event.event(self.random_event_child_name)
        return self.this_event


class VirtualEventSet:
    """
    Create a set of virtual event.
    A virtual event is a substitution of event.

    Examples
    --------
    >>> ves = VirtualEventSet()
    # set event to trigger (before assigning)
    >>> trg.set_event(ves["event1"])
    # assign real event to virtual event
    >>> ves["event1"] = StateEvent(
            "event1",
            sm("state1"),
        )
    # example of RandomEvent
    >>> import random
    >>> ves = VirtualEventSet()
    # set event to trigger (before assigning)
    >>> trg_success.set_event(ves["success"])
    >>> trg_fail.set_event(ves["fail"])
    # assign real event to virtual event
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
    >>> ves["random"] = RandomEvent(
            "random1",
            random1_select,
            sm("state1"),
        )
    >>> ves["success"] = ves["random"].event("success")
    >>> ves["fail"] = ves["random"].event("fail")
    """

    def __init__(self):
        self.virtual_event_dict = {}
        self.virtual_event_registerd_dict = {}

    def _register_virtual_event(self, virtual_event):
        self.virtual_event_registerd_dict[virtual_event.uuid] = virtual_event

    def __getitem__(self, key):
        virtual_event = self.virtual_event_dict.get(key)
        if virtual_event is None:
            virtual_event = VirtualEvent(
                key, operation=OperationType.DUMMY, virtual_event_set=self
            )
            self.virtual_event_dict[key] = virtual_event
        tool_log.debug("VirtualEventSet[{}]".format(key))
        return virtual_event

    def __setitem__(self, key, event):
        isVirtualEvent = isinstance(event, VirtualEvent)
        isEvent = isinstance(event, Event)
        if not isVirtualEvent and not isEvent:
            raise ValueError(
                "class must be {} or {}".format(VirtualEvent.__name__, Event.__name__)
            )

        virtual_event = self.virtual_event_dict.get(key)
        if isVirtualEvent:
            if virtual_event is None:
                self.virtual_event_dict[key] = event
                return
            if virtual_event.operation is None:
                raise ValueError("virtual event is already assigned or bad operation")
            if virtual_event.operation != OperationType.DUMMY:
                raise ValueError("virtual event is already assigned")
            if virtual_event.child_a is not None:
                raise ValueError("virtual event dummy is already assigned")
            virtual_event.child_a = event
            return

        if isEvent:
            if virtual_event is None:
                virtual_event = VirtualEvent(event.name, virtual_event_set=self)
                self.virtual_event_dict[key] = virtual_event
            virtual_event.set_event(event)
            return

    def set(self, raise_error_flag=True):
        tool_log.debug("VirtualEventSet set start")
        virtual_event_registerd_list = list(self.virtual_event_registerd_dict.values())
        for virtual_event in virtual_event_registerd_list:
            virtual_event.set([], raise_error_flag=raise_error_flag)
        tool_log.debug("VirtualEventSet set end")

    def is_modify_event_name_collision(self, raise_error_flag=True):
        event_to_modify_name = {}
        virtual_event_registerd_list = list(self.virtual_event_registerd_dict.values())
        for virtual_event in virtual_event_registerd_list:
            event = virtual_event.get_event_to_modify_name(
                raise_error_flag=raise_error_flag
            )
            event_name_set = event_to_modify_name.get(event)
            if event_name_set is None:
                event_name_set = set()
                event_to_modify_name[event] = event_name_set
            event_name = virtual_event.get_event_name()
            if event_name is not None:
                event_name_set.add(event_name)
        is_collision = False
        for event, event_name_set in event_to_modify_name.items():
            if len(event_name_set) > 1:
                tool_log.debug(
                    "modify_event_name_collision event={}, event_names={}".format(
                        event.name, event_name_set
                    )
                )
                is_collision = True
        return is_collision

    def modify_event_name(self, raise_error_flag=True):
        if self.is_modify_event_name_collision(raise_error_flag=raise_error_flag):
            raise ValueError("modify_event_name_collision")
        for virtual_event in set(self.virtual_event_registerd_dict.values()):
            virtual_event.modify_event_name(raise_error_flag=raise_error_flag)
