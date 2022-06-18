import copy
from enum import Enum, auto
import logging
import pickle

# logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(funcName)s [%(levelname)s]: %(message)s",
)
tool_log = logging.getLogger("tool")
sim_log = logging.getLogger("sim")
stat_log = logging.getLogger("stat")
diagram_log = logging.getLogger("diagram")
vis_log = logging.getLogger("vis")
smpl_log = logging.getLogger("smpl")
# set level
tool_log.setLevel(logging.INFO)
sim_log.setLevel(logging.INFO)
stat_log.setLevel(logging.INFO)
diagram_log.setLevel(logging.INFO)
vis_log.setLevel(logging.INFO)
smpl_log.setLevel(logging.INFO)


class EventType(Enum):
    EDGE = auto()
    LEVEL = auto()


class EventTriggerType(Enum):
    NOLIMIT = auto()
    ONCE = auto()


class NotifyType(Enum):
    CHANGE_STATE = auto()
    STOP_ON_CHANGE_STATE = auto()
    NEXT_TIME_STEP = auto()


class NotifyCase(Enum):
    ACTIVATE = auto()
    DEACTIVATE = auto()


class OperationType(Enum):
    AND = auto()  # &
    OR = auto()  # |
    OR_ONCE = auto()  # ^ (not xor)
    INVERT = auto()  # ~
    EDGE_ONCE = auto()  # +X
    EQ = auto()  # ==
    NE = auto()  # !=
    GT = auto()  # >
    GE = auto()  # >=
    LT = auto()  # <
    LE = auto()  # <=
    RS = auto()  # >>
    LS = auto()  # <<
    ADD = auto()  # +
    SUB = auto()  # -
    MUL = auto()  # *
    DIV = auto()  # /
    DUMMY = auto()  # dummy


class EventCalcType(Enum):
    BOOL = auto()
    ARITH = auto()


class LogStoreFlag(Enum):
    INIT = auto()
    STATE = auto()
    PARAMETER = auto()
    EVENT = auto()


class EventArgType(Enum):
    FUNCTION = auto()
    LIST = auto()
    NUMBER = auto()
    STRING = auto()
    OTHER = auto()


class LogInfo:
    def __init__(self, current_time, log_type, log_info):
        self.current_time = current_time
        self.log_type = log_type
        self.log_info = log_info


class EventInfo:
    def __init__(self):
        self.name = None
        self.event_formula = None
        self.event_log_name = None
        self.done_time = None
        self.start_time = None
        self.event_raise_time = None
        self.is_event_raise_flag = None


class LogStore:
    def __init__(self, state_machines=None, parameter=None):
        self.state_machines = state_machines
        self.parameter = parameter
        self.state_log = []
        self.parameter_log = []
        self.detail_log = []
        self.event_info_dic = {}
        self.state_idx_list = []
        self.parameter_idx_list = []
        self.event_idx_list = []
        self.clear()
        self.log_store_start = False
        self.detail_logging_flag = False
        self.raise_error_num = 0

    def print_log_info(self, log_info):
        if log_info is None:
            print("detail_log: None")
            return
        if log_info.log_type == LogStoreFlag.EVENT:
            print("detail_log: {}, {}".format(log_info.log_type, log_info.current_time))
            for event_info in log_info.log_info.values():
                print(
                    " event: name={}, event_log_name={}, done_time={}, event_raise_time={}, is_event_raise_flag={}".format(
                        event_info.name,
                        event_info.event_log_name,
                        event_info.done_time,
                        event_info.event_raise_time,
                        event_info.is_event_raise_flag,
                    )
                )
        if (
            log_info.log_type == LogStoreFlag.STATE
            or log_info.log_type == LogStoreFlag.PARAMETER
        ):
            print(
                "detail_log: {}, {}\n{}".format(
                    log_info.log_type, log_info.current_time, log_info.log_info
                )
            )

    def print_detail_logging(self):
        for log_info in self.detail_log:
            self.print_log_info(log_info)

    def clear(self):
        # clear
        self.state_log.clear()
        self.parameter_log.clear()
        self.detail_log.clear()
        self.event_info_dic.clear()
        self.state_idx_list.clear()
        self.parameter_idx_list.clear()
        self.event_idx_list.clear()
        # set header
        if self.state_machines is not None:
            state_log_header = [None]
            for state_machine in self.state_machines:
                state_log_header.append(state_machine.name)
            self.state_log.append(state_log_header)
        parameter_log_header = [None, "parameter"]
        self.parameter_log.append(parameter_log_header)
        # initialize variable
        self.current_state = None
        self.replay_index = None
        self.log_store_start = False

    def set_detail_logging_flag(self, detail_logging_flag):
        self.detail_logging_flag = detail_logging_flag

    def _is_change(self):
        if self.current_state is None:
            return True
        if self.state_machines is None:
            return False
        for i, state_machine in enumerate(self.state_machines):
            if self.current_state[i + 1] != state_machine.current_state_name:
                return True
        return False

    def _update_event_info(self, event, is_event_raise_flag):
        event_info = self.event_info_dic.get(event.name)
        if event_info is None:
            event_info = EventInfo()
            self.event_info_dic[event.name] = event_info
            event_info.name = event.name
            event_info.event_formula = event.event_formula
        is_change = False
        if (
            hasattr(event, "event_log_name")
            and event.event_log_name != event_info.event_log_name
        ):
            event_info.event_log_name = event.event_log_name
            is_change = True
        if hasattr(event, "done_time") and event.done_time != event_info.done_time:
            event_info.done_time = event.done_time
            is_change = True
        if hasattr(event, "start_time") and event.start_time != event_info.start_time:
            event_info.start_time = event.start_time
            is_change = True
        if (
            hasattr(event, "event_raise_time")
            and event.event_raise_time != event_info.event_raise_time
        ):
            event_info.event_raise_time = event.event_raise_time
            is_change = True
        if (
            is_event_raise_flag is not None
            and is_event_raise_flag != event_info.is_event_raise_flag
        ):
            event_info.is_event_raise_flag = is_event_raise_flag
            is_change = True
        return is_change

    def update_detail_event(
        self, current_time, event, is_event_raise_flag=None, append_flag=True
    ):
        if self.detail_logging_flag == False:
            return
        if self._update_event_info(event, is_event_raise_flag):
            if append_flag:
                new_log_info = LogInfo(
                    current_time, LogStoreFlag.EVENT, copy.deepcopy(self.event_info_dic)
                )
                self.detail_log.append(new_log_info)

    def update_detail(
        self,
        current_time,
        log_type,
        log_info,
        is_event_raise_flag=None,
        append_flag=True,
    ):
        if log_type == LogStoreFlag.STATE:
            new_log_info = LogInfo(current_time, log_type, log_info)
            self.detail_log.append(new_log_info)
            return
        if log_type == LogStoreFlag.PARAMETER:
            if log_info is None:
                self.raise_error_num += 1
                if self.raise_error_num > 0:
                    raise ValueError("update_detail: log_info is None")
            new_log_info = LogInfo(current_time, log_type, log_info)
            self.detail_log.append(new_log_info)
            return
        if self.detail_logging_flag == False:
            return
        if log_type == LogStoreFlag.EVENT:
            self.update_detail_event(
                current_time, log_info, is_event_raise_flag, append_flag
            )
            return

    def update(self, current_time, log_store_flag):
        if log_store_flag == LogStoreFlag.INIT:
            self.log_store_start = True
        if not self.log_store_start:
            return
        if log_store_flag == LogStoreFlag.PARAMETER and self.state_machines is not None:
            # update parameter log
            parameter = copy.copy(self.parameter)
            if self.detail_logging_flag:
                self.parameter_log.append([current_time, parameter])
            else:
                self.parameter_log.append([current_time, None])
            self.update_detail(current_time, LogStoreFlag.PARAMETER, parameter)
            return
        if self._is_change():
            # update state log
            self.current_state = [current_time]
            for state_machine in self.state_machines:
                self.current_state.append(state_machine.current_state_name)
            self.state_log.append(self.current_state)
            self.update_detail(current_time, LogStoreFlag.STATE, self.current_state)
            if log_store_flag == LogStoreFlag.INIT:
                # set initial parameter log
                parameter = copy.copy(self.parameter)
                if self.detail_logging_flag:
                    self.parameter_log.append([current_time, parameter])
                else:
                    self.parameter_log.append([current_time, None])
                self.update_detail(current_time, LogStoreFlag.PARAMETER, parameter)
            return

    def _max_time(self, time1, time2):
        if time1 is not None and time2 is not None:
            return max(time1, time2)
        if time1 is not None:
            return time1
        if time2 is not None:
            return time2
        return None

    def get_log_last_idx(self):
        return len(self.detail_log) - 1

    def get_log(self, idx=None):
        if idx is None:
            replay_index = self.replay_index
        else:
            replay_index = int(idx)
        if (
            replay_index is None
            or self.get_log_last_idx() < replay_index
            or replay_index < 0
        ):
            return None, None, None, None
        state_idx = self.state_idx_list[replay_index]
        parameter_idx = self.parameter_idx_list[replay_index]
        event_idx = self.event_idx_list[replay_index]
        state = self.detail_log[state_idx] if state_idx >= 0 else None
        parameter = self.detail_log[parameter_idx] if parameter_idx >= 0 else None
        event = self.detail_log[event_idx] if event_idx >= 0 else None
        current_time_0 = state.current_time if state is not None else None
        current_time_1 = parameter.current_time if parameter is not None else None
        current_time_2 = event.current_time if event is not None else None
        current_time = None
        current_time = self._max_time(current_time, current_time_0)
        current_time = self._max_time(current_time, current_time_1)
        current_time = self._max_time(current_time, current_time_2)
        return (
            state,
            parameter,
            event,
            current_time,
        )

    def replay_reset(self):
        self.state_idx_list.clear()
        self.parameter_idx_list.clear()
        self.event_idx_list.clear()
        state_idx = -1
        parameter_idx = -1
        event_idx = -1
        for log_idx, log_info in enumerate(self.detail_log):
            if log_info.log_type == LogStoreFlag.STATE:
                state_idx = log_idx
            if log_info.log_type == LogStoreFlag.PARAMETER:
                parameter_idx = log_idx
            if log_info.log_type == LogStoreFlag.EVENT:
                event_idx = log_idx
            self.state_idx_list.append(state_idx)
            self.parameter_idx_list.append(parameter_idx)
            self.event_idx_list.append(event_idx)

    def replay_prev(self):
        if self.replay_index is None:
            self.replay_index = len(self.detail_log) - 1
        else:
            self.replay_index = self.replay_index - 1
        if self.replay_index <= 0:
            self.replay_index = 0
        return self.replay_index

    def replay_next(self):
        if self.replay_index is None:
            self.replay_index = 0
        else:
            self.replay_index = self.replay_index + 1
        if self.replay_index >= len(self.detail_log) - 1:
            self.replay_index = len(self.detail_log) - 1
        return self.replay_index

    def save(self, filename):
        fout = open(filename, "wb")
        pickle.dump([self.state_log, self.parameter_log, self.detail_log], fout)
        fout.close()

    def load(self, filename):
        fin = open(filename, "rb")
        dump_list = pickle.load(fin)
        self.state_log = dump_list[0]
        self.parameter_log = dump_list[1]
        self.detail_log = dump_list[2]
        fin.close()
        self.replay_reset()
