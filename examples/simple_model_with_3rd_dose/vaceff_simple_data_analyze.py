import os
import sys
import argparse
import pickle
import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

# import veame
from veame import *


def make_diagram():
    def level0(r0):
        r1 = StatNode("Vaccination", wh=(2, 0.75), condition=EventLog())
        r0.set_branch([r1])

        r1_v0 = StatNode(
            "Get no VAC", wh=(2, 0.75), condition=EventLog("select_no_vac")
        )
        r1_v1 = StatNode("Get 1 VAC", wh=(2, 0.75), condition=EventLog("select_1_vac"))
        r1_v2 = StatNode("Get 2 VAC", wh=(2, 0.75), condition=EventLog("select_2_vac"))
        r1_v3 = StatNode("Get 3 VAC", wh=(2, 0.75), condition=EventLog("select_3_vac"))
        r1.set_branch([r1_v0, r1_v1, r1_v2, r1_v3], "center")

        return [r1_v0, r1_v3]

    def level1(path_i, r2_v):
        r3_v1 = StatNode(
            f"path{path_i} Receive VAC1", wh=(1.8, 0.75), condition=EventLog("vac1")
        )
        r3_v2 = StatNode(
            f"path{path_i} No VAC1",
            wh=(1.8, 0.75),
            condition=~EventLog("vac1"),
        )
        r3_v3 = StatNode(
            f"path{path_i} Positive (before VAC1)",
            wh=(1.8, 0.75),
            condition=EventLog("vac1") > EventLog("PCR_positive"),
        )
        r3_v4 = StatNode(
            f"path{path_i} Death (before VAC1)",
            wh=(1.8, 0.75),
            condition=EventLog("vac1") > EventLog("death"),
        )
        r2_v.set_branch([r3_v1, r3_v2, r3_v3, r3_v4], "left")

        return r3_v1

    def add_PCR_positive_level(path_i, r, event_log, day_list, VAC_or_PCR):
        r_list = []
        for day in day_list:
            r_tmp = StatNode(
                f"path{path_i} Positive (before {day}days from {VAC_or_PCR})",
                wh=(1.8, 0.75),
                condition=event_log + EventLog(datetime.timedelta(days=day))
                > EventLog("PCR_positive"),
            )
            r_list.append(r_tmp)
        r.set_branch(r_list, "left")

    def level2(path_i, r3_v):
        EventLog_VAC1_14d = EventLog("vac1") + EventLog(datetime.timedelta(days=14))
        r4_v1 = StatNode(
            f"path{path_i} 14days after VAC1", wh=(1.8, 0.75), condition=EventLog()
        )
        r4_v2 = StatNode(
            f"path{path_i} Positive (before 14days from VAC1) branch",
            wh=(1.8, 0.75),
            condition=EventLog_VAC1_14d > EventLog("PCR_positive"),
        )
        r4_v3 = StatNode(
            f"path{path_i} ADV or Death (before 14days from VAC1)",
            wh=(1.8, 0.75),
            condition=(EventLog_VAC1_14d > EventLog("ADV1_severe"))
            | (EventLog_VAC1_14d > EventLog("death")),
        )
        r3_v.set_branch([r4_v1, r4_v2, r4_v3], "left")
        add_PCR_positive_level(path_i, r4_v2, EventLog("vac1"), [14, 10, 5], "VAC1")

        return r4_v1

    def level3(path_i, r4_v):
        r5_v1 = StatNode(
            f"path{path_i} Receive VAC2", wh=(1.8, 0.75), condition=EventLog("vac2")
        )
        r5_v2 = StatNode(
            f"path{path_i} No VAC2",
            wh=(1.8, 0.75),
            condition=~EventLog("vac2"),
        )
        r5_v3 = StatNode(
            f"path{path_i} Positive (before VAC2)",
            wh=(1.8, 0.75),
            condition=EventLog("vac2") > EventLog("PCR_positive"),
        )
        r5_v4 = StatNode(
            f"path{path_i} ADV or Death (before VAC2)",
            wh=(1.8, 0.75),
            condition=(EventLog("vac2") > EventLog("ADV1_severe"))
            | (EventLog("vac2") > EventLog("death")),
        )
        r4_v.set_branch([r5_v1, r5_v2, r5_v3, r5_v4], "left")

        return r5_v1

    def level4(path_i, r5_v):
        EventLog_VAC2_7d = EventLog("vac2") + EventLog(datetime.timedelta(days=7))
        r6_v1 = StatNode(
            f"path{path_i} 7days after VAC2", wh=(1.8, 0.75), condition=EventLog()
        )
        r6_v2 = StatNode(
            f"path{path_i} Positive (before 7days from VAC2) branch",
            wh=(1.8, 0.75),
            condition=EventLog_VAC2_7d > EventLog("PCR_positive"),
        )
        r6_v3 = StatNode(
            f"path{path_i} ADV or Death (before 7days from VAC2)",
            wh=(1.8, 0.75),
            condition=(EventLog_VAC2_7d > EventLog("ADV2_severe"))
            | (EventLog_VAC2_7d > EventLog("death")),
        )
        r5_v.set_branch([r6_v1, r6_v2, r6_v3], "left")
        add_PCR_positive_level(path_i, r6_v2, EventLog("vac2"), [7, 3], "VAC2")

        return r6_v1

    def level5(path_i, r6_v):
        r7_v1 = StatNode(
            f"path{path_i} Receive VAC3", wh=(1.8, 0.75), condition=EventLog("vac3")
        )
        r7_v2 = StatNode(
            f"path{path_i} No VAC3",
            wh=(1.8, 0.75),
            condition=~EventLog("vac3"),
        )
        r7_v3 = StatNode(
            f"path{path_i} Positive (before VAC3)",
            wh=(1.8, 0.75),
            condition=EventLog("vac3") > EventLog("PCR_positive"),
        )
        r7_v4 = StatNode(
            f"path{path_i} ADV or Death (before VAC3)",
            wh=(1.8, 0.75),
            condition=(EventLog("vac3") > EventLog("ADV2_severe"))
            | (EventLog("vac3") > EventLog("death")),
        )
        r6_v.set_branch([r7_v1, r7_v2, r7_v3, r7_v4], "left")
        add_PCR_positive_level(
            path_i, r7_v3, EventLog("vac2"), [150, 120, 90, 60, 30], "VAC2"
        )

        return r7_v1

    def level6(path_i, r7_v):
        EventLog_VAC3_7d = EventLog("vac3") + EventLog(datetime.timedelta(days=7))
        r8_v1 = StatNode(
            f"path{path_i} 7days after VAC3", wh=(1.8, 0.75), condition=EventLog()
        )
        r8_v2 = StatNode(
            f"path{path_i} Positive (before 7days from VAC3) branch",
            wh=(1.8, 0.75),
            condition=EventLog_VAC3_7d > EventLog("PCR_positive"),
        )
        r8_v3 = StatNode(
            f"path{path_i} ADV or Death (before 7days from VAC3)",
            wh=(1.8, 0.75),
            condition=(EventLog_VAC3_7d > EventLog("ADV3_severe"))
            | (EventLog_VAC3_7d > EventLog("death")),
        )
        r7_v.set_branch([r8_v1, r8_v2, r8_v3], "left")
        add_PCR_positive_level(path_i, r8_v2, EventLog("vac3"), [7, 3], "VAC3")

        return r8_v1

    def level7(path_i, r8_v):
        r9_v1 = StatNode(
            f"path{path_i} Negative after 7days from VAC3",
            wh=(1.8, 0.75),
            condition=~EventLog("PCR_positive")
            & ~EventLog("ADV1_severe")
            & ~EventLog("ADV2_severe")
            & ~EventLog("ADV3_severe")
            & ~EventLog("death"),
        )
        r9_v2 = StatNode(
            f"path{path_i} Positive after 7days from VAC3",
            wh=(1.8, 0.75),
            condition=EventLog("PCR_positive"),
        )
        r9_v3 = StatNode(
            f"path{path_i} ADV or Death",
            wh=(1.8, 0.75),
            condition=EventLog("ADV3_severe") | EventLog("death"),
        )
        r8_v.set_branch([r9_v1, r9_v2, r9_v3], "left")

        return r9_v1

    r0 = StatNode("Eligibility", wh=(2, 0.75))
    r1_list = level0(r0)
    for path_i, r2_v in enumerate(r1_list):
        r3_v = level1(path_i, r2_v)
        r4_v = level2(path_i, r3_v)
        r5_v = level3(path_i, r4_v)
        r6_v = level4(path_i, r5_v)
        r7_v = level5(path_i, r6_v)
        r8_v = level6(path_i, r7_v)
        r9_v = level7(path_i, r8_v)
    return r0


# get sorted event data
def get_event(diagram, node_name, event_name):
    r = diagram(node_name)
    event_data, eval_error = r.event_eval(EventLog(event_name), "inbound")
    return sorted(event_data)


# floor datetime to date
def floor_datetime(datetime_list):
    return list(
        map(
            lambda d: d.replace(hour=0, minute=0, second=0, microsecond=0),
            datetime_list,
        )
    )


# min datetime
def calc_min_time(time1, time2):
    if time1 is None and time2 is None:
        return None
    elif time1 is None and time2 is not None:
        return time2
    elif time1 is not None and time2 is None:
        return time1
    if time1 > time2:
        return time2
    else:
        return time1


# max datetime
def calc_max_time(time1, time2):
    if time1 is None and time2 is None:
        return None
    elif time1 is None and time2 is not None:
        return time2
    elif time1 is not None and time2 is None:
        return time1
    if time1 < time2:
        return time2
    else:
        return time1


# datetime range
def calc_datetime_range(range1, range2):
    return (calc_max_time(range1[0], range2[0]), calc_min_time(range1[1], range2[1]))


# calculate number of PCR positive case and person days in case of vac2
def calc_PCRpos_and_personday_vac2(
    event_data_info_list,
    day1,
    day2,
    sdate,
    edate,
    PCR_pos_type,
    vac2_name,
    vac3_name,
    event_list_flag=False,
):
    PCRpos_count = 0
    person_day = 0
    person_count = 0
    range_compare = [None, None]
    event_list = []
    for event_data_info in event_data_info_list:
        vac2_datetime = EventLog(vac2_name).eval(event_data_info, True)
        if vac2_datetime is None:
            continue
        day1_after_vac2 = vac2_datetime + datetime.timedelta(days=day1)
        if day2 is None:
            day2_after_vac2 = None
        else:
            day2_after_vac2 = vac2_datetime + datetime.timedelta(days=day2)

        if (
            day2_after_vac2 is not None
            and (day1_after_vac2 < sdate or edate < day2_after_vac2)
        ) or (day2_after_vac2 is None and edate < day1_after_vac2):
            continue

        vac3_datetime = EventLog(vac3_name).eval(event_data_info, True)
        PCRpos_datetime = EventLog(PCR_pos_type).eval(event_data_info, True)
        stop_datetime = calc_min_time(vac3_datetime, PCRpos_datetime)
        stop_datetime = calc_min_time(stop_datetime, end_date_time)

        range_after_vac2 = (day1_after_vac2, day2_after_vac2)
        range_time_window = (sdate, edate)
        range_to_stop = (start_date_time, stop_datetime)

        range_person_day = calc_datetime_range(range_after_vac2, range_time_window)
        range_person_day = calc_datetime_range(range_person_day, range_to_stop)

        if PCRpos_datetime is not None and (
            (vac3_datetime is not None and PCRpos_datetime < vac3_datetime)
            or vac3_datetime is None
        ):
            # T(vac2) < T(PCR_positive), without vac3
            # or
            # T(vac2) < T(PCR_positive) < T(vac3)
            if (
                day1_after_vac2 <= PCRpos_datetime
                and (
                    (day2_after_vac2 is not None and PCRpos_datetime < day2_after_vac2)
                    or day2_after_vac2 is None
                )
                and sdate <= PCRpos_datetime
                and PCRpos_datetime < edate
            ):
                PCRpos_count += 1
                if event_list_flag:
                    event_list.append(PCRpos_datetime)

        if range_person_day[0] <= range_person_day[1]:
            person_day += (range_person_day[1] - range_person_day[0]).days
            person_count += 1
            range_compare[0] = calc_min_time(range_compare[0], range_person_day[0])
            range_compare[1] = calc_max_time(range_compare[1], range_person_day[1])
    if event_list_flag:
        plot_event(event_list)
    return PCRpos_count, person_day, person_count, range_compare, event_list


# calculate number of PCR positive case and person days in case of no vac
def calc_PCRpos_and_personday_no_vac(
    event_data_info_list, day1, day2, sdate, edate, PCR_pos_type, event_list_flag=False
):
    PCRpos_count = 0
    person_day = 0
    person_count = 0
    range_compare = [None, None]
    event_list = []
    for event_data_info in event_data_info_list:
        PCRpos_datetime = EventLog(PCR_pos_type).eval(event_data_info, True)
        stop_datetime = calc_min_time(PCRpos_datetime, end_date_time)

        range_time_window = (sdate, edate)
        range_to_stop = (start_date_time, stop_datetime)

        range_person_day = calc_datetime_range(range_time_window, range_to_stop)

        if PCRpos_datetime is not None:
            if sdate <= PCRpos_datetime and PCRpos_datetime < edate:
                PCRpos_count += 1
                if event_list_flag:
                    event_list.append(PCRpos_datetime)

        if range_person_day[0] <= range_person_day[1]:
            person_day += (range_person_day[1] - range_person_day[0]).days
            person_count += 1
            range_compare[0] = calc_min_time(range_compare[0], range_person_day[0])
            range_compare[1] = calc_max_time(range_compare[1], range_person_day[1])
    if event_list_flag:
        plot_event(event_list)
    return PCRpos_count, person_day, person_count, range_compare, event_list


# cumulative graph
def calc_event_line(event_data_list):
    date_list = []
    val_list = []
    current_day = -1
    current_val = 0
    for event_data in event_data_list:
        event_day = event_data.days
        current_val += 1
        if event_day > current_day:
            date_list.append(event_day)
            val_list.append(current_val)
            current_day = event_day
        else:
            val_list[-1] = current_val
    line_x = []
    line_y = []
    current_y = 0
    line_x.append(0)
    line_y.append(current_y)
    for date, val in zip(date_list, val_list):
        line_x.append(date)
        line_y.append(current_y)
        line_x.append(date)
        line_y.append(val)
        current_y = val

    return line_x, line_y


# time series
def calc_event_num(event_data_list):
    floor_event_list = floor_datetime(event_data_list)
    sdate = floor_event_list[0]
    edate = floor_event_list[-1]
    days = int((edate - sdate).days) + 1
    line_x = list(range(days))
    line_x = list(map(lambda x: sdate + datetime.timedelta(days=x), line_x))
    line_y = [0] * days
    for event_data in event_data_list:
        event_day = (event_data - sdate).days
        line_y[event_day] += 1

    return line_x, line_y


# calculate VE by comparing vac2 and another vac2
def calc_VE_compare_vac2_and_vac2(
    diagram, day1, day2, sdate, edate, vac3_name="vac3", dummy_vac3_name="dummy_vac3"
):
    PCR_pos_type = "PCR_positive_dl"

    r = diagram("path1 7days after VAC2")
    event_data_info_list = r.event_data_set_inbound.get_event_data_info_list()
    (
        PCRpos_count_vac2,
        person_day_vac2,
        person_count_vac2,
        range_compare,
        _,
    ) = calc_PCRpos_and_personday_vac2(
        event_data_info_list, day1, day2, sdate, edate, PCR_pos_type, "vac2", vac3_name
    )

    range_compare[0] = range_compare[0] if range_compare[0] is not None else sdate
    range_compare[1] = range_compare[1] if range_compare[1] is not None else edate

    r = diagram("Get no VAC")
    event_data_info_list = r.event_data_set_inbound.get_event_data_info_list()

    (
        PCRpos_count_novac,
        person_day_novac,
        person_count_novac,
        _,
        _,
    ) = calc_PCRpos_and_personday_vac2(
        event_data_info_list,
        day1,
        day2,
        sdate,
        edate,
        PCR_pos_type,
        "dummy_vac2",
        dummy_vac3_name,
    )

    infect_ratio_vac2 = (
        (PCRpos_count_vac2 / person_day_vac2) if person_day_vac2 > 0 else None
    )
    infect_ratio_novac = (
        (PCRpos_count_novac / person_day_novac) if person_day_novac > 0 else None
    )
    VE = (
        (1 - infect_ratio_vac2 / infect_ratio_novac)
        if infect_ratio_vac2 is not None
        and infect_ratio_novac is not None
        and infect_ratio_novac > 0
        else None
    )
    return (
        VE,
        day1,
        day2,
        range_compare,
        PCRpos_count_vac2,
        person_day_vac2,
        person_count_vac2,
        PCRpos_count_novac,
        person_day_novac,
        person_count_novac,
    )


# calculate VE by comparing vac2 and novac
def calc_VE_compare_vac2_and_novac(
    diagram, day1, day2, sdate, edate, vac3_name="vac3", dummy_vac3_name="dummy_vac3"
):
    PCR_pos_type = "PCR_positive_dl"

    r = diagram("path1 7days after VAC2")
    event_data_info_list = r.event_data_set_inbound.get_event_data_info_list()
    (
        PCRpos_count_vac2,
        person_day_vac2,
        person_count_vac2,
        range_compare,
        _,
    ) = calc_PCRpos_and_personday_vac2(
        event_data_info_list, day1, day2, sdate, edate, PCR_pos_type, "vac2", vac3_name
    )

    range_compare[0] = range_compare[0] if range_compare[0] is not None else sdate
    range_compare[1] = range_compare[1] if range_compare[1] is not None else edate

    r = diagram("Get no VAC")
    event_data_info_list = r.event_data_set_inbound.get_event_data_info_list()

    (
        PCRpos_count_novac,
        person_day_novac,
        person_count_novac,
        _,
        _,
    ) = calc_PCRpos_and_personday_no_vac(
        event_data_info_list,
        0,
        240,
        sdate,
        edate,
        PCR_pos_type,
    )

    infect_ratio_vac2 = (
        (PCRpos_count_vac2 / person_day_vac2) if person_day_vac2 > 0 else None
    )
    infect_ratio_novac = (
        (PCRpos_count_novac / person_day_novac) if person_day_novac > 0 else None
    )
    VE = (
        (1 - infect_ratio_vac2 / infect_ratio_novac)
        if infect_ratio_vac2 is not None
        and infect_ratio_novac is not None
        and infect_ratio_novac > 0
        else None
    )
    return (
        VE,
        day1,
        day2,
        range_compare,
        PCRpos_count_vac2,
        person_day_vac2,
        person_count_vac2,
        PCRpos_count_novac,
        person_day_novac,
        person_count_novac,
    )


# print VE day1-day2 days since vac2
def print_VE(diagram, day1, day2, month_period, calc_VE, vac3_name, dummy_vac3_name):
    shift = "04"
    sdate_str = f"2021-04-{shift} 00:00:00"
    date0 = datetime.datetime.strptime(sdate_str, "%Y-%m-%d %H:%M:%S")
    edate_str = f"2022-01-{shift} 00:00:00"
    date1 = datetime.datetime.strptime(edate_str, "%Y-%m-%d %H:%M:%S")

    print(f"day1={day1},day2={day2},month_period={month_period}")
    print(
        "VE,start_date,start_range,end_range,PCRpos_count_vac2,person_day_vac2,person_count_vac2,PCRpos_count_novac,person_day_novac,person_count_novac"
    )

    for i in range(48):
        sdate = date0 + datetime.timedelta(days=7 * i)
        if date1 < sdate:
            break
        if type(month_period) is int:
            edate = sdate + relativedelta(months=month_period)
        else:
            edate = sdate + datetime.timedelta(days=30 * month_period)
        (
            VE,
            day1,
            day2,
            range_compare,
            PCRpos_count_vac2,
            person_day_vac2,
            person_count_vac2,
            PCRpos_count_novac,
            person_day_novac,
            person_count_novac,
        ) = calc_VE(diagram, day1, day2, sdate, edate, vac3_name, dummy_vac3_name)
        print(
            f"{VE},{sdate},{range_compare[0]},{range_compare[1]},{PCRpos_count_vac2},{person_day_vac2},{person_count_vac2},{PCRpos_count_novac},{person_day_novac},{person_count_novac}"
        )


# calculate population day1-day2 days since vac2
def calc_population_vac2(diagram, day1, day2, stat_node_name, vac2_name, vac3_name):
    r = diagram(stat_node_name)
    event_data_info_list = r.event_data_set_inbound.get_event_data_info_list()
    date_in = []
    date_out = []
    for event_data_info in event_data_info_list:
        vac2_datetime = EventLog(vac2_name).eval(event_data_info, True)
        if vac2_datetime is None:
            continue
        day1_after_vac2 = vac2_datetime + datetime.timedelta(days=day1)
        if day2 is None:
            day2_after_vac2 = None
        else:
            day2_after_vac2 = vac2_datetime + datetime.timedelta(days=day2)
        PCRpos_datetime = EventLog("PCR_positive").eval(event_data_info, True)
        vac3_datetime = EventLog(vac3_name).eval(event_data_info, True)
        stop_datetime = calc_min_time(day2_after_vac2, vac3_datetime)
        stop_datetime = calc_min_time(stop_datetime, PCRpos_datetime)
        if (
            PCRpos_datetime is None
            or (PCRpos_datetime is not None and day1_after_vac2 < PCRpos_datetime)
        ) and (
            stop_datetime is None
            or (stop_datetime is not None and stop_datetime >= day1_after_vac2)
        ):
            date_in.append(day1_after_vac2)
            if stop_datetime is not None:
                if stop_datetime < day1_after_vac2:
                    print(
                        f"error: {day1_after_vac2}, {day2_after_vac2}, {PCRpos_datetime}, {vac3_datetime}"
                    )
                date_out.append(stop_datetime)
            else:
                print(
                    f"error: {day1_after_vac2}, {day2_after_vac2}, {PCRpos_datetime}, {vac3_datetime}"
                )

    floor_date_in = floor_datetime(sorted(date_in))
    floor_date_out = floor_datetime(sorted(date_out))
    floor_date_in_first = floor_date_in[0] if len(floor_date_in) > 0 else None
    floor_date_out_first = floor_date_out[0] if len(floor_date_out) > 0 else None
    floor_date_in_last = floor_date_in[-1] if len(floor_date_in) > 0 else None
    floor_date_out_last = floor_date_out[-1] if len(floor_date_out) > 0 else None
    sdate = calc_min_time(floor_date_in_first, floor_date_out_first)
    edate = calc_max_time(floor_date_in_last, floor_date_out_last)
    if sdate is None or edate is None:
        return [], []
    days = int((edate - sdate).days) + 1
    line_x = list(range(days))
    line_x = list(map(lambda x: sdate + datetime.timedelta(days=x), line_x))
    in_out = [0] * days
    line_y = [0] * days
    for event_data in floor_date_in:
        event_day = (event_data - sdate).days
        in_out[event_day] += 1

    for event_data in floor_date_out:
        event_day = (event_data - sdate).days
        in_out[event_day] -= 1

    pop_num = 0
    for i, num in enumerate(in_out):
        pop_num += num
        line_y[i] = pop_num

    return line_x, line_y


# calculate population
def calc_population_novac(diagram):
    r = diagram("Get no VAC")
    event_data_info_list = r.event_data_set_inbound.get_event_data_info_list()
    date_in = []
    date_out = []
    for event_data_info in event_data_info_list:
        vac0_in_time = EventLog("select_no_vac").eval(event_data_info, True)
        if vac0_in_time is None:
            continue
        PCRpos_datetime = EventLog("PCR_positive").eval(event_data_info, True)
        vac3_datetime = EventLog("dummy_vac3").eval(event_data_info, True)
        stop_datetime = PCRpos_datetime
        if (
            PCRpos_datetime is None
            or (PCRpos_datetime is not None and vac0_in_time < PCRpos_datetime)
        ) and (
            stop_datetime is None
            or (stop_datetime is not None and stop_datetime >= vac0_in_time)
        ):
            date_in.append(vac0_in_time)
            if stop_datetime is not None:
                if stop_datetime < vac0_in_time:
                    print(f"error: {vac0_in_time}, {PCRpos_datetime}, {vac3_datetime}")
                date_out.append(stop_datetime)

    floor_date_in = floor_datetime(sorted(date_in))
    floor_date_out = floor_datetime(sorted(date_out))
    floor_date_in_first = floor_date_in[0] if len(floor_date_in) > 0 else None
    floor_date_out_first = floor_date_out[0] if len(floor_date_out) > 0 else None
    floor_date_in_last = floor_date_in[-1] if len(floor_date_in) > 0 else None
    floor_date_out_last = floor_date_out[-1] if len(floor_date_out) > 0 else None
    sdate = calc_min_time(floor_date_in_first, floor_date_out_first)
    edate = calc_max_time(floor_date_in_last, floor_date_out_last)
    if sdate is None or edate is None:
        return [], []
    days = int((edate - sdate).days) + 1
    line_x = list(range(days))
    line_x = list(map(lambda x: sdate + datetime.timedelta(days=x), line_x))
    in_out = [0] * days
    line_y = [0] * days
    for event_data in floor_date_in:
        event_day = (event_data - sdate).days
        in_out[event_day] += 1

    for event_data in floor_date_out:
        event_day = (event_data - sdate).days
        in_out[event_day] -= 1

    pop_num = 0
    for i, num in enumerate(in_out):
        pop_num += num
        line_y[i] = pop_num

    return line_x, line_y


# calc event
def calc_event(diagram, stat_node_name, event_name):
    r = diagram(stat_node_name)
    event_data_info_list = r.event_data_set_inbound.get_event_data_info_list()
    event_list = []
    for event_data_info in event_data_info_list:
        event_time = EventLog(event_name).eval(event_data_info, True)
        if event_time is None:
            continue
        event_list.append(event_time)
    return event_list


# plot event
def plot_event(event_list):

    days = int((end_date_time - start_date_time).days) + 1
    line_y = [0] * days
    line_x = list(range(days))
    line_x = list(map(lambda x: start_date_time + datetime.timedelta(days=x), line_x))
    for event_time in event_list:
        event_day = (event_time - start_date_time).days
        line_y[event_day] += 1

    sdate_str = f"2021-02-01 00:00:00"
    first_date = datetime.datetime.strptime(sdate_str, "%Y-%m-%d %H:%M:%S")
    edate_str = f"2022-02-01 00:00:00"
    last_date = datetime.datetime.strptime(edate_str, "%Y-%m-%d %H:%M:%S")
    # plot
    plt.title("Event")
    plt.xlabel("Date")
    plt.ylabel("Event count")
    plt.xlim([first_date, last_date])
    plt.plot(line_x, line_y, color="black", label="event")
    plt.legend(
        bbox_to_anchor=(0, 0, 1, 1), loc="upper left", borderaxespad=1, fontsize=10
    )
    plt.xlim([first_date, last_date])
    plt.show()


# plot population of vac2 day1-day2 days since vac2
def plot_population_vac2(
    diagram, incidence_rate_data, stat_node_name, vac2_name, vac3_name, filename=None
):
    pu_key = incidence_rate_data[0]
    pu_data_dl = incidence_rate_data[1]
    line_x0, line_y0 = calc_population_vac2(
        diagram, 14, 30, stat_node_name, vac2_name, vac3_name
    )
    line_x1, line_y1 = calc_population_vac2(
        diagram, 31, 60, stat_node_name, vac2_name, vac3_name
    )
    line_x2, line_y2 = calc_population_vac2(
        diagram, 61, 90, stat_node_name, vac2_name, vac3_name
    )
    line_x3, line_y3 = calc_population_vac2(
        diagram, 91, 120, stat_node_name, vac2_name, vac3_name
    )
    line_x4, line_y4 = calc_population_vac2(
        diagram, 121, None, stat_node_name, vac2_name, vac3_name
    )

    sdate_str = f"2021-02-01 00:00:00"
    first_date = datetime.datetime.strptime(sdate_str, "%Y-%m-%d %H:%M:%S")
    edate_str = f"2022-02-01 00:00:00"
    last_date = datetime.datetime.strptime(edate_str, "%Y-%m-%d %H:%M:%S")
    # plot
    fig = plt.figure()
    ax1 = fig.add_subplot()
    ax1.set_title("Population and incidence case")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Population")
    ax1.set_xlim([first_date, last_date])
    # ax1.plot(line_x0, line_y0, color="black", label="14-30 days")
    # ax1.plot(line_x1, line_y1, color="orange", label="31-60 days")
    # ax1.plot(line_x2, line_y2, color="blue", label="61-90 days")
    # ax1.plot(line_x3, line_y3, color="green", label="91-120 days")
    ax1.plot(line_x4, line_y4, color="red", label=">120 days")
    ax1.plot([0], [0], "-", color="black", label="Delta variant")
    ax1.legend(
        bbox_to_anchor=(0, 0, 1, 1), loc="upper left", borderaxespad=1, fontsize=10
    )
    ax2 = ax1.twinx()
    ax2.set_xlim([first_date, last_date])
    ax2.set_ylabel("Incidence case")
    ax2.fill_between(pu_key, pu_data_dl, color="lightblue", alpha=0.5)
    ax2.plot(pu_key, pu_data_dl, color="black", label="Delta variant")
    if filename is None:
        plt.show()
    else:
        plt.savefig(filename)


# plot population of novac
def plot_population_novac(diagram, incidence_rate_data, filename=None):
    pu_key = incidence_rate_data[0]
    pu_data_dl = incidence_rate_data[1]
    line_x0, line_y0 = calc_population_novac(diagram)

    sdate_str = f"2021-02-01 00:00:00"
    first_date = datetime.datetime.strptime(sdate_str, "%Y-%m-%d %H:%M:%S")
    edate_str = f"2022-02-01 00:00:00"
    last_date = datetime.datetime.strptime(edate_str, "%Y-%m-%d %H:%M:%S")
    # plot
    fig = plt.figure()
    ax1 = fig.add_subplot()
    ax1.set_title("Population and incidence case")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Population")
    ax1.set_xlim([first_date, last_date])
    ax1.plot(line_x0, line_y0, color="red", label="No vac")
    ax1.plot([0], [0], "-", color="black", label="Delta variant")
    ax1.legend(
        bbox_to_anchor=(0, 0, 1, 1), loc="upper left", borderaxespad=1, fontsize=10
    )
    ax2 = ax1.twinx()
    ax2.set_xlim([first_date, last_date])
    ax2.set_ylabel("Incidence case")
    ax2.fill_between(pu_key, pu_data_dl, color="lightblue", alpha=0.5)
    ax2.plot(pu_key, pu_data_dl, color="black", label="Delta variant")
    if filename is None:
        plt.show()
    else:
        plt.savefig(filename)


# cumulative graph of event
def get_graph_line_sum(diagram, node_name, event_name, start_date_time, last_date):
    r = diagram(node_name)
    event_data_set, eval_error = r.event_eval(
        EventLog(event_name) - EventLog(start_date_time), "inbound"
    )
    line_x_vac2, line_y_vac2 = calc_event_line(sorted(event_data_set))
    line_x_vac2 = list(
        map(lambda x: start_date_time + datetime.timedelta(days=x), line_x_vac2)
    )
    if len(line_x_vac2) > 0:
        if line_x_vac2[-1] < last_date:
            line_x_vac2.append(last_date)
            line_y_vac2.append(line_y_vac2[-1])
    return line_x_vac2, line_y_vac2


# plot time series graph of vaccination
def plot_vaccination(diagram, filename=None):
    r = diagram("Eligibility")
    event_data_set, eval_error = r.event_eval(EventLog("vac1"), "inbound")
    sdate_str = f"2021-02-01 00:00:00"
    first_date = datetime.datetime.strptime(sdate_str, "%Y-%m-%d %H:%M:%S")
    edate_str = f"2022-02-01 00:00:00"
    last_date = datetime.datetime.strptime(edate_str, "%Y-%m-%d %H:%M:%S")
    event_data_set = list(filter(None, event_data_set))
    line_x_vac2, line_y_vac2 = calc_event_num(sorted(event_data_set))
    # plot
    fig = plt.figure()
    ax = fig.add_subplot()
    ax.set_title("Vaccination")
    ax.set_xlabel("Date")
    ax.set_ylabel("Number")
    ax.set_xlim([first_date, last_date])
    ax.plot(line_x_vac2, line_y_vac2, color="green", label="vac1")
    ax.legend(bbox_to_anchor=(1, 1), loc="upper right", borderaxespad=1, fontsize=10)
    if filename is None:
        plt.show()
    else:
        plt.savefig(filename)
    return line_x_vac2, line_y_vac2


# plot cumulative graph of vaccination
def plot_vaccination_sum_vac(
    diagram, stat_node_name, vac1_name, vac2_name, vac3_name, suffix, filename=None
):
    sdate_str = f"2021-02-01 00:00:00"
    first_date = datetime.datetime.strptime(sdate_str, "%Y-%m-%d %H:%M:%S")
    edate_str = f"2022-02-01 00:00:00"
    last_date = datetime.datetime.strptime(edate_str, "%Y-%m-%d %H:%M:%S")
    line_x_vac1, line_y_vac1 = get_graph_line_sum(
        diagram, stat_node_name, vac1_name, start_date_time, last_date
    )
    line_x_vac2, line_y_vac2 = get_graph_line_sum(
        diagram, stat_node_name, vac2_name, start_date_time, last_date
    )
    line_x_vac3, line_y_vac3 = get_graph_line_sum(
        diagram, stat_node_name, vac3_name, start_date_time, last_date
    )
    # plot
    fig = plt.figure()
    ax = fig.add_subplot()
    ax.set_title(f"Vaccination {suffix}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Number")
    ax.set_xlim([first_date, last_date])
    # ax.plot(line_x_vac1, line_y_vac1, color="blue", label=f"1st dose {suffix}")
    ax.plot(line_x_vac2, line_y_vac2, color="green", label=f"2nd dose {suffix}")
    ax.plot(line_x_vac3, line_y_vac3, color="red", label=f"3rd dose {suffix}")
    ax.legend(bbox_to_anchor=(1, 0), loc="lower right", borderaxespad=1, fontsize=10)
    if filename is None:
        plt.show()
    else:
        plt.savefig(filename)


def print_VE_over_time(month_period):
    # vac2 and dummy vac
    print_VE(
        diagram,
        121,
        None,
        month_period,
        calc_VE_compare_vac2_and_vac2,
        "vac3",
        "dummy_vac3",
    )
    # vac2 and novac
    print_VE(
        diagram, 121, None, month_period, calc_VE_compare_vac2_and_novac, "vac3", "no"
    )


# parse args
parser = argparse.ArgumentParser(description="analyze data.")
parser.add_argument("--input", required=True, type=str, help="event data file")
args = parser.parse_args()

# args
log_filename = args.input

# read log file
fin = open(log_filename, "rb")
person_event_data_list = pickle.load(fin)
fin.close()
print(len(person_event_data_list))

# read person event data
person0 = person_event_data_list[0]
person0_meta_data = person0["person_data"]
start_date_time = person0_meta_data["sim_start_time"]
end_date_time = person0_meta_data["sim_end_time"]

# read incidence rate
current_dir = os.path.dirname(__file__)
input_csv = os.path.join(current_dir, "Denmark_dl_om.csv")
df = pd.read_csv(input_csv, index_col=[0])
pu_key = [datetime.datetime.strptime(x, "%Y-%m-%d") for x in df.index]
pu_value_dl = df["Denmark_dl"]
pu_data_dl = [value for value in pu_value_dl]
incidence_rate_data = (pu_key, pu_data_dl)

# set diagram
diagram = make_diagram()
statgui = StatGUI(diagram, person_event_data_list=person_event_data_list)

print("VE 2 months")
print_VE_over_time(2)
print("VE 3 months")
print_VE_over_time(3)
print("VE 4 months")
print_VE_over_time(4)

print("Population_and_incidence_case_vac")
plot_population_vac2(
    diagram,
    incidence_rate_data,
    "path1 7days after VAC2",
    "vac2",
    "vac3",
    "Population_and_incidence_case_vac.png",
)
print("Population_and_incidence_case_novac_dummy_vac")
plot_population_vac2(
    diagram,
    incidence_rate_data,
    "Get no VAC",
    "dummy_vac2",
    "dummy_vac3",
    "Population_and_incidence_case_novac_dummy_vac.png",
)
print("Population_and_incidence_case_novac")
plot_population_novac(
    diagram, incidence_rate_data, "Population_and_incidence_case_novac.png"
)

print("Vaccination_vac")
plot_vaccination_sum_vac(
    diagram, "Eligibility", "vac1", "vac2", "vac3", "", "Vaccination_vac.png"
)
print("Vaccination_novac_dummy")
plot_vaccination_sum_vac(
    diagram,
    "Eligibility",
    "dummy_vac1",
    "dummy_vac2",
    "dummy_vac3",
    "(dummy)",
    "Vaccination_novac_dummy.png",
)
