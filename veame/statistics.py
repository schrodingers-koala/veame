import copy
import datetime
import collections

from .common import OperationType
from .common import OperationType
from .common import stat_log


class EventEval:
    def __init__(self, name, child_a=None, child_b=None, operation=None):
        self.name = name
        self.child_a = child_a
        self.child_b = child_b
        self.operation = operation

    def _check_other(self, other, info):
        if not isinstance(other, EventLog) and not isinstance(other, EventEval):
            raise ValueError(
                "{}, class is not {} or {}".format(
                    info,
                    EventLog.__class__.__name__,
                    EventEval.__class__.__name__,
                )
            )

    def __and__(self, other):
        info = "{}&{}".format(self.name, other.name)
        self._check_other(other, info)
        new_name = "({}&{})".format(self.name, other.name)
        if isinstance(other, EventLog):
            new_event_eval = EventEval(other.name, other)
            return EventEval(new_name, self, new_event_eval, OperationType.AND)
        return EventEval(new_name, self, other, OperationType.AND)

    def __or__(self, other):
        info = "{}|{}".format(self.name, other.name)
        self._check_other(other, info)
        new_name = "({}|{})".format(self.name, other.name)
        if isinstance(other, EventLog):
            new_event_eval = EventEval(other.name, other)
            return EventEval(new_name, self, new_event_eval, OperationType.OR)
        return EventEval(new_name, self, other, OperationType.OR)

    def __invert__(self):
        new_name = "(~({}))".format(self.name)
        return EventEval(new_name, self, None, OperationType.INVERT)

    def eval(self, event_data_info, ignore_error=True):
        if self.operation == OperationType.AND:
            if self.child_a.is_true(event_data_info, ignore_error):
                # child_a is True
                return self.child_b.is_true(event_data_info, ignore_error)
            else:
                # child_a is False
                return False
        if self.operation == OperationType.OR:
            if self.child_a.is_true(event_data_info, ignore_error):
                # child_a is True
                return True
            else:
                # child_a is False
                return self.child_b.is_true(event_data_info, ignore_error)
        if self.operation == OperationType.INVERT:
            return not self.child_a.is_true(event_data_info, ignore_error)
        if self.operation is None:
            return self.child_a.is_true(event_data_info, ignore_error)
        raise ValueError('operation must be "&", "|", "~"')

    def is_true(self, event_data_info, ignore_error):
        return self.eval(event_data_info, ignore_error)


class EventCountEval(EventEval):
    def __init__(self, name, child_a=None, child_b=None, operation=None):
        super().__init__(name, child_a, child_b, operation)

    def _check_other(self, other, info):
        if not isinstance(other, EventEval):
            raise ValueError(
                "{}, class is not {}".format(
                    info,
                    EventEval.__class__.__name__,
                )
            )

    def eval(self, event_data_info, ignore_error=True):
        if self.operation == OperationType.EQ:
            return self.child_a.eval(event_data_info) == self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.NE:
            return self.child_a.eval(event_data_info) != self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.GT:
            return self.child_a.eval(event_data_info) > self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.GE:
            return self.child_a.eval(event_data_info) >= self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.LT:
            return self.child_a.eval(event_data_info) < self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.LE:
            return self.child_a.eval(event_data_info) <= self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.RS:
            return self.child_a.eval(event_data_info) > self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.LS:
            return self.child_a.eval(event_data_info) < self.child_b.eval(
                event_data_info
            )
        try:
            return super().eval(event_data_info, ignore_error=True)
        except ValueError:
            raise ValueError(
                'operation must be "&", "|", "~", "==", "!=", ">", ">=", "<", "<=", ">>", "<<", "+", "-"'
            )


class EventCountCalc:
    def __init__(self, name, child_a=None, child_b=None, operation=None):
        self.name = name
        self.child_a = child_a
        self.child_b = child_b
        self.operation = operation

    def _new_event_count(self, other):
        if isinstance(other, EventCountCalc):
            return other
        if type(other) is int or type(other) is float or type(other) is str:
            return EventCount(value=other)
        raise ValueError(
            "class is not {}, int or float".format(
                EventCountCalc.__class__.__name__,
            )
        )

    def __eq__(self, other):
        new_other = self._new_event_count(other)
        new_name = "({}=={})".format(self.name, new_other.name)
        return EventCountEval(new_name, self, new_other, OperationType.EQ)

    def __ne__(self, other):
        new_other = self._new_event_count(other)
        new_name = "({}!={})".format(self.name, new_other.name)
        return EventCountEval(new_name, self, new_other, OperationType.NE)

    def __gt__(self, other):
        new_other = self._new_event_count(other)
        new_name = "({}>{})".format(self.name, new_other.name)
        return EventCountEval(new_name, self, new_other, OperationType.GT)

    def __ge__(self, other):
        new_other = self._new_event_count(other)
        new_name = "({}>={})".format(self.name, new_other.name)
        return EventCountEval(new_name, self, new_other, OperationType.GE)

    def __lt__(self, other):
        new_other = self._new_event_count(other)
        new_name = "({}<{})".format(self.name, new_other.name)
        return EventCountEval(new_name, self, new_other, OperationType.LT)

    def __le__(self, other):
        new_other = self._new_event_count(other)
        new_name = "({}<={})".format(self.name, new_other.name)
        return EventCountEval(new_name, self, new_other, OperationType.LE)

    def __add__(self, other):
        new_other = self._new_event_count(other)
        new_name = "({}+{})".format(self.name, new_other.name)
        return EventCountCalc(new_name, self, new_other, OperationType.ADD)

    def __sub__(self, other):
        new_other = self._new_event_count(other)
        new_name = "({}-{})".format(self.name, new_other.name)
        return EventCountCalc(new_name, self, new_other, OperationType.SUB)

    def __mul__(self, other):
        new_other = self._new_event_count(other)
        new_name = "({}*{})".format(self.name, new_other.name)
        return EventCountCalc(new_name, self, new_other, OperationType.MUL)

    def __truediv__(self, other):
        new_other = self._new_event_count(other)
        new_name = "({}/{})".format(self.name, new_other.name)
        return EventCountCalc(new_name, self, new_other, OperationType.DIV)

    def eval(self, event_data_info, ignore_error=True):
        if self.operation == OperationType.ADD:
            stat_log.debug(
                "child_a.name={} + child_b.name={}".format(
                    self.child_a.name, self.child_b.name
                )
            )
            return self.child_a.eval(event_data_info) + self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.SUB:
            stat_log.debug(
                "child_a.name={} - child_b.name={}".format(
                    self.child_a.name, self.child_b.name
                )
            )
            return self.child_a.eval(event_data_info) - self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.MUL:
            stat_log.debug(
                "child_a.name={} * child_b.name={}".format(
                    self.child_a.name, self.child_b.name
                )
            )
            return self.child_a.eval(event_data_info) * self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.DIV:
            stat_log.debug(
                "child_a.name={} / child_b.name={}".format(
                    self.child_a.name, self.child_b.name
                )
            )
            return self.child_a.eval(event_data_info) / self.child_b.eval(
                event_data_info
            )
        raise ValueError('operation must be "+", "-", "*", "/"')


class EventCount(EventCountCalc):
    """
    Condition used to classify event data.
    Two types of condition are available, event existance or timestamp of event raise.

    Constructor options
    -------------------
    event_name : None or str
        None : default
            no condition.
        str :
            event name.
    value : None, int or float
        None : default
            no condition.
        int or float :
            expression of value.
    meta_data_name: None, str
        None : default
            no condition.
        str :
            metadata name. use PersonLog for simple interface.
    value_name : None, str
        None : default
            no condition.
        str :
            name of value in metadata. use PersonLog for simple interface.

    Examples
    --------
    >>> event_cond = EventCount("event1") == 2
    # event data set which matches condition is returned
    >>> matched_event_data_set, errors = event_data_set.get_event_data_set(event_cond)
    # set condition
    >>> event_cond = EventCount(meta_data_name="person_data", value_name="name") == "name1"
    # event data set which matches condition is returned
    >>> matched_event_data_set, errors = event_data_set.get_event_data_set(event_cond)
    # set condition
    >>> event_cond = PersonLog("person_data", "name") == "name1"
    # event data set which matches condition is returned
    >>> matched_event_data_set, errors = event_data_set.get_event_data_set(event_cond)
    """

    def __init__(
        self, event_name=None, value=None, meta_data_name=None, value_name=None
    ):
        self._init()
        if event_name is not None:
            if type(event_name) is not str:
                raise ValueError("event_name must be str")
            self.name = event_name
            self.event_name = event_name
            return
        if value is not None:
            if type(value) is int:
                self.name = "int({})".format(value)
                self.value = value
                return
            if type(value) is float:
                self.name = "float({})".format(value)
                self.value = value
                return
            if type(value) is str:
                self.name = '"{}"'.format(value)
                self.value = value
                return
            raise ValueError("value must be int, float or str")
        if meta_data_name is not None and value_name is not None:
            if type(meta_data_name) is not str:
                raise ValueError("meta_data_name must be str")
            if type(value_name) is not str:
                raise ValueError("value_name must be str")
            self.name = "{}[{}]".format(meta_data_name, value_name)
            self.meta_data_name = meta_data_name
            self.value_name = value_name
            return

    def _init(self):
        self.name = None
        self.event_name = None
        self.value = None
        self.meta_data_name = None
        self.value_name = None

    def get_event_data(event_data):
        event_time_list = []
        event_name_list = []
        for k, v in event_data.items():
            for event_name in v:
                event_time_list.append(k)
                event_name_list.append(event_name)
        return [event_time_list, event_name_list]

    def count(self, event_data_info):
        count = 0
        if self.event_name is None:
            return count

        event_data = event_data_info.event_data_listtype
        list_of_value = event_data[1]
        for event_name in list_of_value:
            if event_name == self.event_name:
                count += 1

        return count

    def get_meta_data(self, event_data_info, meta_data_name, value_name):
        meta_data = event_data_info.meta_data
        if not isinstance(meta_data, collections.abc.Mapping):
            return None
        meta_data_detail = meta_data[meta_data_name]
        if not isinstance(meta_data_detail, collections.abc.Mapping):
            return None
        value = meta_data_detail.get(value_name)
        return value

    def eval(self, event_data_info, ignore_error=True):
        if self.event_name is not None:
            return self.count(event_data_info)
        if self.value_name is not None and self.meta_data_name is not None:
            return self.get_meta_data(
                event_data_info, self.meta_data_name, self.value_name
            )
        if self.value is not None:
            return self.value


class PersonLog(EventCount):
    """
    Condition of person metadata used to classify event data.

    Constructor options
    -------------------
    meta_data_name: str
        metadata name.
    value_name : str
        name of value in metadata.

    Examples
    --------
    >>> event_cond = PersonLog("person_data", "name") == "name1"
    # event data set which matches condition is returned
    >>> matched_event_data_set, errors = event_data_set.get_event_data_set(event_cond)
    """

    def __init__(self, meta_data_name, value_name):
        self._init()
        self.name = "{}[{}]".format(meta_data_name, value_name)
        self.meta_data_name = meta_data_name
        self.value_name = value_name


class EventLogEval(EventEval):
    def __init__(self, name, child_a=None, child_b=None, operation=None):
        super().__init__(name, child_a, child_b, operation)

    def _check_other(self, other, info):
        if not isinstance(other, EventLogCalc) and not isinstance(other, EventEval):
            raise ValueError(
                "{}, class is not {} or {}".format(
                    info,
                    EventLogCalc.__class__.__name__,
                    EventEval.__class__.__name__,
                )
            )

    def eval(self, event_data_info, ignore_error=True):
        if self.operation == OperationType.EQ:  # ==
            # event_a == event_b is
            #  - indefinite, if event_a and event_b don't exist.
            #  - false, if either event_a or event_b doesn't exist.
            #  - true, if time of event_a == time of event_b.
            #  - false, otherwise.
            child_a_exists = self.child_a.exists(event_data_info)
            child_b_exists = self.child_b.exists(event_data_info)
            if not child_a_exists and not child_b_exists:
                if ignore_error:
                    return False  # False in case of indefinite
                else:
                    raise ValueError(
                        "cannot evaluate 'None({}) == None({})'".format(
                            self.child_a.event_name, self.child_b.event_name
                        )
                    )
            if child_a_exists and not child_b_exists:
                return False
            if not child_a_exists and child_b_exists:
                return False
            return self.child_a.eval(event_data_info) == self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.NE:  # !=
            # event_a != event_b is
            #  - indefinite, if event_a and event_b don't exist.
            #  - true, if either event_a or event_b doesn't exist.
            #  - true, if time of event_a != time of event_b.
            #  - false, otherwise.
            child_a_exists = self.child_a.exists(event_data_info)
            child_b_exists = self.child_b.exists(event_data_info)
            if not child_a_exists and not child_b_exists:
                if ignore_error:
                    return False  # False in case of indefinite
                else:
                    raise ValueError(
                        "cannot evaluate 'None({}) != None({})'".format(
                            self.child_a.event_name, self.child_b.event_name
                        )
                    )
            if child_a_exists and not child_b_exists:
                return True
            if not child_a_exists and child_b_exists:
                return True
            return self.child_a.eval(event_data_info) != self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.GT:  # >
            # event_a > event_b is
            #  - indefinite, if event_a and event_b don't exist.
            #  - false, if event_a exists and event_b doesn't exist.
            #  - true, if event_a doesn't exist and event_b exists.
            #  - true, if time of event_a > time of event_b.
            #  - false, otherwise.
            child_a_exists = self.child_a.exists(event_data_info)
            child_b_exists = self.child_b.exists(event_data_info)
            if not child_a_exists and not child_b_exists:
                if ignore_error:
                    return False  # False in case of indefinite
                else:
                    raise ValueError(
                        "cannot evaluate 'None({}) > None({})'".format(
                            self.child_a.event_name, self.child_b.event_name
                        )
                    )
            if child_a_exists and not child_b_exists:
                return False
            if not child_a_exists and child_b_exists:
                return True
            return self.child_a.eval(event_data_info) > self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.GE:  # >=
            child_a_exists = self.child_a.exists(event_data_info)
            child_b_exists = self.child_b.exists(event_data_info)
            if not child_a_exists and not child_b_exists:
                if ignore_error:
                    return False  # False in case of indefinite
                else:
                    raise ValueError(
                        "cannot evaluate 'None({}) >= None({})'".format(
                            self.child_a.event_name, self.child_b.event_name
                        )
                    )
            if child_a_exists and not child_b_exists:
                return False
            if not child_a_exists and child_b_exists:
                return True
            return self.child_a.eval(event_data_info) >= self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.LT:  # <
            child_a_exists = self.child_a.exists(event_data_info)
            child_b_exists = self.child_b.exists(event_data_info)
            if not child_a_exists and not child_b_exists:
                if ignore_error:
                    return False  # False in case of indefinite
                else:
                    raise ValueError(
                        "cannot evaluate 'None({}) < None({})'".format(
                            self.child_a.event_name, self.child_b.event_name
                        )
                    )
            if child_a_exists and not child_b_exists:
                return True
            if not child_a_exists and child_b_exists:
                return False
            return self.child_a.eval(event_data_info) < self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.LE:  # <=
            child_a_exists = self.child_a.exists(event_data_info)
            child_b_exists = self.child_b.exists(event_data_info)
            if not child_a_exists and not child_b_exists:
                if ignore_error:
                    return False  # False in case of indefinite
                else:
                    raise ValueError(
                        "cannot evaluate 'None({}) <= None({})'".format(
                            self.child_a.event_name, self.child_b.event_name
                        )
                    )
            if child_a_exists and not child_b_exists:
                return True
            if not child_a_exists and child_b_exists:
                return False
            return self.child_a.eval(event_data_info) <= self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.RS:  # >>
            # event_a >> event_b is
            #  - indefinite, if event_a and event_b don't exist.
            #  - false, if event_a exists and event_b doesn't exist.
            #  - false, if event_a doesn't exist and event_b exists.
            #  - true, if time of event_a > time of event_b.
            #  - false, otherwise.
            child_a_exists = self.child_a.exists(event_data_info)
            child_b_exists = self.child_b.exists(event_data_info)
            if not child_a_exists and not child_b_exists:
                if ignore_error:
                    return False  # False in case of indefinite
                else:
                    raise ValueError(
                        "cannot evaluate 'None({}) >> None({})'".format(
                            self.child_a.event_name, self.child_b.event_name
                        )
                    )
            if child_a_exists and not child_b_exists:
                return False
            if not child_a_exists and child_b_exists:
                return False
            return self.child_a.eval(event_data_info) > self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.LS:  # <<
            child_a_exists = self.child_a.exists(event_data_info)
            child_b_exists = self.child_b.exists(event_data_info)
            if not child_a_exists and not child_b_exists:
                if ignore_error:
                    return False  # False in case of indefinite
                else:
                    raise ValueError(
                        "cannot evaluate 'None({}) << None({})'".format(
                            self.child_a.event_name, self.child_b.event_name
                        )
                    )
            if child_a_exists and not child_b_exists:
                return False
            if not child_a_exists and child_b_exists:
                return False
            return self.child_a.eval(event_data_info) < self.child_b.eval(
                event_data_info
            )
        try:
            return super().eval(event_data_info, ignore_error=True)
        except ValueError:
            raise ValueError(
                'operation must be "&", "|", "~", "==", "!=", ">", ">=", "<", "<=", ">>", "<<", "+", "-"'
            )


class EventLogCalc:
    def __init__(self, name, child_a=None, child_b=None, operation=None):
        self.name = name
        self.child_a = child_a
        self.child_b = child_b
        self.operation = operation

    def _check_other(self, other, info):
        if (
            not isinstance(other, EventLogCalc)
            and not isinstance(other, EventLogEval)
            and not isinstance(other, EventEval)
        ):
            raise ValueError(
                "{}, class is not {}, {} or {}".format(
                    info,
                    EventLogCalc.__class__.__name__,
                    EventLogEval.__class__.__name__,
                    EventEval.__class__.__name__,
                )
            )

    def __and__(self, other):
        info = "{}&{}".format(self.name, other.name)
        self._check_other(other, info)
        new_name = "({}&{})".format(self.name, other.name)
        return EventEval(new_name, self, other, OperationType.AND)

    def __or__(self, other):
        info = "{}|{}".format(self.name, other.name)
        self._check_other(other, info)
        new_name = "({}|{})".format(self.name, other.name)
        return EventEval(new_name, self, other, OperationType.OR)

    def __invert__(self):
        new_name = "(~({}))".format(self.name)
        return EventEval(new_name, self, None, OperationType.INVERT)

    def __eq__(self, other):
        if not isinstance(other, EventLogCalc):
            raise ValueError("class is not {}".format(EventLogCalc.__name__))
        new_name = "({}=={})".format(self.name, other.name)
        return EventLogEval(new_name, self, other, OperationType.EQ)

    def __ne__(self, other):
        if not isinstance(other, EventLogCalc):
            raise ValueError("class is not {}".format(EventLogCalc.__name__))
        new_name = "({}!={})".format(self.name, other.name)
        return EventLogEval(new_name, self, other, OperationType.NE)

    def __gt__(self, other):
        if not isinstance(other, EventLogCalc):
            raise ValueError("class is not {}".format(EventLogCalc.__name__))
        new_name = "({}>{})".format(self.name, other.name)
        return EventLogEval(new_name, self, other, OperationType.GT)

    def __ge__(self, other):
        if not isinstance(other, EventLogCalc):
            raise ValueError("class is not {}".format(EventLogCalc.__name__))
        new_name = "({}>={})".format(self.name, other.name)
        return EventLogEval(new_name, self, other, OperationType.GE)

    def __lt__(self, other):
        if not isinstance(other, EventLogCalc):
            raise ValueError("class is not {}".format(EventLogCalc.__name__))
        new_name = "({}<{})".format(self.name, other.name)
        return EventLogEval(new_name, self, other, OperationType.LT)

    def __le__(self, other):
        if not isinstance(other, EventLogCalc):
            raise ValueError("class is not {}".format(EventLogCalc.__name__))
        new_name = "({}<={})".format(self.name, other.name)
        return EventLogEval(new_name, self, other, OperationType.LE)

    def __rshift__(self, other):
        if not isinstance(other, EventLogCalc):
            raise ValueError("class is not {}".format(EventLogCalc.__name__))
        new_name = "({}>>{})".format(self.name, other.name)
        return EventLogEval(new_name, self, other, OperationType.RS)

    def __lshift__(self, other):
        if not isinstance(other, EventLogCalc):
            raise ValueError("class is not {}".format(EventLogCalc.__name__))
        new_name = "({}<<{})".format(self.name, other.name)
        return EventLogEval(new_name, self, other, OperationType.LS)

    def __add__(self, other):
        # + a (pos) is not supported
        if not isinstance(other, EventLogCalc):
            raise ValueError("class is not {}".format(EventLogCalc.__name__))
        new_name = "({}+{})".format(self.name, other.name)
        return EventLogCalc(new_name, self, other, OperationType.ADD)

    def __sub__(self, other):
        # - a (neg) is not supported
        if not isinstance(other, EventLogCalc):
            raise ValueError("class is not {}".format(EventLogCalc.__name__))
        new_name = "({}-{})".format(self.name, other.name)
        return EventLogCalc(new_name, self, other, OperationType.SUB)

    def exists(self, event_data_info):
        if self.child_a is None and self.child_b is None:
            raise ValueError("bad calculation")
        if self.child_a is not None:
            child_a_exists = self.child_a.exists(event_data_info)
        else:
            child_a_exists = True
        if self.child_b is not None:
            child_b_exists = self.child_b.exists(event_data_info)
        else:
            child_b_exists = True
        return child_a_exists and child_b_exists

    def eval(self, event_data_info, ignore_error=True):
        if self.operation == OperationType.ADD:
            stat_log.debug(
                "child_a.name={} + child_b.name={}".format(
                    self.child_a.name, self.child_b.name
                )
            )
            child_a_exists = self.child_a.exists(event_data_info)
            child_b_exists = self.child_b.exists(event_data_info)
            error_info = ""
            if not child_a_exists:
                error_info += ", '{}' is not exist".format(self.child_a.name)
            if not child_b_exists:
                error_info += ", '{}' is not exist".format(self.child_b.name)
            if not error_info == "":
                raise ValueError(
                    "Calculation error '{}' + '{}'{}".format(
                        self.child_a.name,
                        self.child_b.name,
                        error_info,
                    )
                )
            return self.child_a.eval(event_data_info) + self.child_b.eval(
                event_data_info
            )
        if self.operation == OperationType.SUB:
            stat_log.debug(
                "child_a.name={} - child_b.name={}".format(
                    self.child_a.name, self.child_b.name
                )
            )
            child_a_exists = self.child_a.exists(event_data_info)
            child_b_exists = self.child_b.exists(event_data_info)
            error_info = ""
            if not child_a_exists:
                error_info += ", '{}' is not exist".format(self.child_a.name)
            if not child_b_exists:
                error_info += ", '{}' is not exist".format(self.child_b.name)
            if not error_info == "":
                raise ValueError(
                    "Calculation error '{}' - '{}'{}".format(
                        self.child_a.name,
                        self.child_b.name,
                        error_info,
                    )
                )
            return self.child_a.eval(event_data_info) - self.child_b.eval(
                event_data_info
            )
        raise ValueError('operation must be "+", "-"')

    def is_true(self, event_data_info, ignore_error):
        return self.exists(event_data_info)


class EventLog(EventLogCalc):
    """
    Condition used to classify event data.
    Two types of condition are available, event existance or timestamp of event raise.

    Constructor options
    -------------------
    event_name_or_date : None, str, datetime.datetime or datetime.timedelta
        None : default
            no condition.
        str : event name
        datetime.datetime :
            expression of timestamp of event raise.
        datetime.timedelta :
            expression of timedelta between two timestamps.
    num : int, default 1
        index of event raise.

    Examples
    --------
    >>> event_cond = EventLog("event1") == EventLog(
            datetime.datetime.strptime(
                "2021-06-07 12:00:00", "%Y-%m-%d %H:%M:%S"
            )
        )
    # event data set which matches condition is returned
    >>> matched_event_data_set, errors = event_data_set.get_event_data_set(event_cond)
    """

    def __init__(self, event_name_or_date=None, num=1):
        self._init()
        if isinstance(event_name_or_date, str):
            self.event_name = event_name_or_date
            self.num = num
            self.name = "{}#{}".format(event_name_or_date, num)
            return
        self.name = "{}".format(event_name_or_date)
        if isinstance(event_name_or_date, datetime.datetime):
            self.datetime = event_name_or_date
            return
        if isinstance(event_name_or_date, datetime.timedelta):
            self.timedelta = event_name_or_date
            return

    def _init(self):
        self.name = None
        self.event_name = None
        self.datetime = None
        self.timedelta = None

    def get_event_data(event_data):
        event_time_list = []
        event_name_list = []
        for k, v in event_data.items():
            for event_name in v:
                event_time_list.append(k)
                event_name_list.append(event_name)
        return [event_time_list, event_name_list]

    def exists(self, event_data_info):
        if self.event_name is not None:
            event_data = event_data_info.event_data_listtype
            list_of_value = event_data[1]
            find_list = [i for i, x in enumerate(list_of_value) if x == self.event_name]
            return len(find_list) >= self.num
        # if datetime or timedelta is specified, return True
        return True

    def eval(self, event_data_info, ignore_error=True):
        if self.event_name is not None:
            event_data = event_data_info.event_data_listtype
            list_of_key = event_data[0]
            list_of_value = event_data[1]
            find_list = [i for i, x in enumerate(list_of_value) if x == self.event_name]
            event_num = self.num - 1
            if len(find_list) <= event_num:
                raise ValueError("{} not found".format(self.name))
            index = find_list[event_num]
            date = list_of_key[index]
            return date
        if self.datetime is not None:
            return self.datetime
        if self.timedelta is not None:
            return self.timedelta
        return None

    def is_true(self, event_data_info, ignore_error):
        return self.exists(event_data_info)


class EventDataInfo:
    def __init__(
        self, id, id_manager, event_data, event_data_listtype=None, meta_data=None
    ):
        self.id = id
        self.id_manager = id_manager
        self.event_data = event_data
        if event_data_listtype is None:
            self.event_data_listtype = EventLog.get_event_data(event_data)
        else:
            self.event_data_listtype = event_data_listtype
        self.meta_data = meta_data

    def info(self):
        return "id[{}]: [person_data={}] {}".format(
            self.id, self.meta_data["person_data"], self.event_data
        )

    def is_same_event_data(self, event_data_info):
        self_event_data_listtype = self.event_data_listtype
        other_event_data_listtype = event_data_info.event_data_listtype
        self_time_list = self_event_data_listtype[0]
        other_time_list = other_event_data_listtype[0]
        if len(self_time_list) != len(other_time_list):
            return False
        for self_time, other_time in zip(self_time_list, other_time_list):
            if self_time != other_time:
                return False
        self_event_list = self_event_data_listtype[1]
        other_event_list = other_event_data_listtype[1]
        if len(self_event_list) != len(other_event_list):
            return False
        for self_event, other_event in zip(self_event_list, other_event_list):
            self_event_set = set(self_event)
            other_event_set = set(other_event)
            if len(self_event_set ^ other_event_set) > 0:
                return False
        return True

    def print(self):
        print(self.info())


class IdManager:
    def __init__(self):
        self.current_id = 0
        self.id_set = set()

    def new_id(self):
        self.current_id = self.current_id + 1
        self.id_set.add(self.current_id)
        return self.current_id

    def is_id_exist(self, id):
        return id in self.id_set

    def add_id(self, id):
        if self.is_id_exist(id):
            raise ValueError("id {} already exists".format(id))
        self.id_set.add(id)

    def delete_id(self, id):
        self.id_set.discard(id)


class EventDataSet:
    """
    Set of event data.

    Constructor options
    -------------------
    id_manager : IdManager
        id_manager to provide unique id of event data.
    event_data_list : None or list
        None : default
        list :
            list of event data. for details, see Simulation class.
    person_event_data_list : None or list
        None : default
        list :
            list of person event data. for details, see Simulation class.

    Examples
    --------
    >>> person_event_data_list = sim.get_person_event_data_list()
    >>> event_data_set = EventDataSet(
            IdManager(), person_event_data_list=person_event_data_list
        )
    """

    def __init__(
        self, id_manager=None, event_data_list=None, person_event_data_list=None
    ):
        self.id_manager = id_manager
        self.event_data_info_dict = {}
        if event_data_list is not None:
            self.add_event_data_list(event_data_list)
        elif person_event_data_list is not None:
            self.add_person_event_data_list(person_event_data_list)

    def print(self):
        print("EventDataSet")
        for i, event_data_info in enumerate(self.get_event_data_info_list()):
            print("EventDataSet[{}]: {}".format(i, event_data_info.info()))

    def clear(self):
        self.event_data_info_dict.clear()

    def size(self):
        return len(self.event_data_info_dict)

    def get_event_data_info(self, idx):
        event_data_info_list = list(self.get_event_data_info_list())
        return event_data_info_list[int(idx)]

    def get_event_data_info_list(self):
        return self.event_data_info_dict.values()

    def add_event_data(self, event_data):
        if self.id_manager is None:
            raise ValueError("id_manager is not set")
        new_id = self.id_manager.new_id()
        event_data_listtype = None
        meta_data = {
            "health_parameter_init": None,
            "health_parameter_last": None,
            "person_data": None,
        }
        event_data_info = EventDataInfo(
            new_id, self.id_manager, event_data, event_data_listtype, meta_data
        )
        self.event_data_info_dict[new_id] = event_data_info

    def add_event_data_list(self, event_data_list):
        for event_data in event_data_list:
            self.add_event_data(event_data)

    def add_person_event_data(self, person_event_data):
        if self.id_manager is None:
            raise ValueError("id_manager is not set")
        new_id = self.id_manager.new_id()
        event_data = person_event_data["event_data"]
        event_data_listtype = None
        meta_data = {
            "health_parameter_init": person_event_data["health_parameter_init"],
            "health_parameter_last": person_event_data["health_parameter_last"],
            "person_data": person_event_data["person_data"],
        }
        event_data_info = EventDataInfo(
            new_id, self.id_manager, event_data, event_data_listtype, meta_data
        )
        self.event_data_info_dict[new_id] = event_data_info

    def add_person_event_data_list(self, person_event_data_list):
        for person_event_data in person_event_data_list:
            self.add_person_event_data(person_event_data)

    def _create_and_add_event_data_info(self, event_data_info):
        if self.id_manager is None:
            raise ValueError("id_manager is not set")
        new_id = self.id_manager.new_id()
        event_data = event_data_info.event_data
        event_data_listtype = event_data_info.event_data_listtype
        meta_data = event_data_info.meta_data

        event_data_info = EventDataInfo(
            new_id, self.id_manager, event_data, event_data_listtype, meta_data
        )
        self.event_data_info_dict[new_id] = event_data_info

    def add_event_data_info(self, event_data_info):
        if not isinstance(event_data_info, EventDataInfo):
            raise ValueError("class is not {}".format(EventDataInfo.__name__))
        if self.id_manager is None:
            self.id_manager = event_data_info.id_manager
        if self.id_manager == event_data_info.id_manager:
            if self.event_data_info_dict.get(event_data_info.id) is None:
                self.event_data_info_dict[event_data_info.id] = event_data_info
        else:
            self._create_and_add_event_data_info(event_data_info)

    def delete_event_data_info(self, event_data_info):
        if not isinstance(event_data_info, EventDataInfo):
            raise ValueError("class is not {}".format(EventDataInfo.__name__))
        if self.id_manager == event_data_info.id_manager:
            del self.event_data_info_dict[event_data_info.id]
        else:
            pass

    def copy(self):
        new_event_data_set = EventDataSet(self.id_manager)
        new_event_data_set.event_data_info_dict = copy.copy(self.event_data_info_dict)
        return new_event_data_set

    def update(self, other):
        self.event_data_info_dict.update(other.event_data_info_dict)

    def delete(self, other):
        key_set = other.event_data_info_dict.keys() - self.event_data_info_dict.keys()
        for k in key_set:
            del self.event_data_info_dict[k]

    def __add__(self, other):
        if not isinstance(other, EventDataSet):
            raise ValueError("class is not {}".format(EventDataSet.__name__))
        new_event_data_set = self.copy()
        if self.id_manager is None and other.id_manager is None:
            return new_event_data_set
        if self.id_manager is None:
            # self.id_manager is None and other.id_manager is not None
            self.id_manager = other.id_manager
        if self.id_manager == other.id_manager:
            # update
            new_event_data_set.update(other)
            return new_event_data_set
        else:
            # self.id_manager != other.id_manager
            # (other.id_manager may be None)
            # add
            event_data_info_list = other.event_data_info_dict.values()
            for event_data_info in event_data_info_list:
                new_event_data_set._create_and_add_event_data_info(event_data_info)
            return new_event_data_set

    def __sub__(self, other):
        if not isinstance(other, EventDataSet):
            raise ValueError("class is not {}".format(EventDataSet.__name__))
        new_event_data_set = self.copy()
        if self.id_manager is None and other.id_manager is None:
            return new_event_data_set
        if self.id_manager is None:
            self.id_manager = other.id_manager
        if self.id_manager == other.id_manager:
            # delete
            new_event_data_set.delete(other)
            return new_event_data_set
        else:
            # self.id_manager != other.id_manager
            # (other.id_manager may be None)
            # not delete
            return new_event_data_set

    def event_eval(self, event_log, ignore_error=True):
        event_data_eval = []
        eval_error_data_info = []
        eval_error_detail = []
        for event_data_info in self.get_event_data_info_list():
            # if evaluation error occurs,
            #  - add no result to event_data_eval
            #    and add error to error info, if ignore_error is False.
            #  - add result (False) to event_data_eval
            #    and add no error to error info, if ignore_error is True.
            try:
                event_data_eval.append(event_log.eval(event_data_info, ignore_error))
            except ValueError as e:
                eval_error_data_info.append(event_data_info)
                eval_error_detail.append(e)
        eval_error = zip(eval_error_data_info, eval_error_detail)
        return event_data_eval, eval_error

    def get_event_data_set(self, event_log=None, ignore_error=True):
        return self._get_event_data_set_main(event_log, ignore_error, None)

    def _get_event_data_set_main(
        self, event_log=None, ignore_error=True, callback=None
    ):
        new_event_data_set = EventDataSet()
        eval_error_data_info = []
        eval_error_detail = []
        # initialize progress bar variables
        progress_max = self.size()
        progress_unit = max(1, progress_max / 50)
        progress_i = 0
        for event_data_info in self.get_event_data_info_list():
            # update progress bar variables
            progress_i += 1
            if progress_i % progress_unit == 0 and callback is not None:
                callback(progress_i, progress_max, "running")
            # if evaluation error occurs,
            #  - add no result to event_data_eval
            #    and add error to error info, if ignore_error is False.
            #  - add result (False) to event_data_eval
            #    and add no error to error info, if ignore_error is True.
            try:
                if event_log is not None:
                    event_data_eval = event_log.is_true(event_data_info, ignore_error)
                else:
                    event_data_eval = True  # True in case of no condition specified
            except ValueError as e:
                eval_error_data_info.append(event_data_info)
                eval_error_detail.append(e)
                continue
            if type(event_data_eval) is not bool:
                raise ValueError(
                    "result of evaluation ({}) is not boolean".format(event_data_eval)
                )
            if event_data_eval:
                new_event_data_set.add_event_data_info(event_data_info)
        eval_error = zip(eval_error_data_info, eval_error_detail)
        if callback is not None:
            callback(progress_i, progress_max, "running")
        return new_event_data_set, eval_error
