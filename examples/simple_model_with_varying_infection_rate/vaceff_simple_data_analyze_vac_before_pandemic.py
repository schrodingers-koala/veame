import os, sys
import argparse
import pickle
import datetime
import matplotlib.pyplot as plt
from numpy.core.numeric import NaN
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

# import veame
from veame import *

# count positive event
def make_diagram(stat_start_date_time, vac1_shift_days, vac2_shift_days):
    r = StatNode("root", wh=(2, 0.75))

    r0 = StatNode(
        "total",
        condition=EventLog(),
    )
    r0_v2 = StatNode(
        "exception",
        condition=EventLog("PCR_positive") < EventLog(stat_start_date_time),
    )
    r.set_branch([r0, r0_v2], "left")

    r1_v1 = StatNode(
        "others",
        wh=(2, 0.75),
        condition=~EventLog(),
    )
    r1_v2 = StatNode(
        "not pos",
        wh=(2, 0.75),
        condition=~EventLog("PCR_positive"),
    )
    r1_v3 = StatNode(
        "pos",
        wh=(2, 0.75),
        condition=EventLog("PCR_positive"),
    )
    r0.set_branch([r1_v1, r1_v2, r1_v3], "left")

    r2_v1 = StatNode(
        "others",
        wh=(2, 0.75),
        condition=~EventLog(),
    )
    # vac2_pos_event
    r2_v2 = StatNode(
        "vac2 after {} days < pos".format(vac2_shift_days),
        wh=(2, 0.75),
        condition=(
            EventLog("vac2") + EventLog(datetime.timedelta(days=vac2_shift_days))
            <= EventLog("PCR_positive")
        )
        & (EventLog("PCR_positive")),
    )
    # vac1_pos_event
    r2_v3 = StatNode(
        "vac1 after {} days <= pos < vac2 after {} days".format(
            vac1_shift_days, vac2_shift_days
        ),
        wh=(2, 0.75),
        condition=(
            EventLog("vac1") + EventLog(datetime.timedelta(days=vac1_shift_days))
            <= EventLog("PCR_positive")
        )
        & (
            EventLog("PCR_positive")
            < EventLog("vac2") + EventLog(datetime.timedelta(days=vac2_shift_days))
        ),
    )
    # novac_pos_event
    r2_v4 = StatNode(
        "pos < vac1 after {} days".format(vac1_shift_days),
        wh=(2, 0.75),
        condition=EventLog("PCR_positive")
        < EventLog("vac1") + EventLog(datetime.timedelta(days=vac1_shift_days)),
    )
    r1_v3.set_branch([r2_v1, r2_v2, r2_v3, r2_v4], "left")

    return r


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


# put datetime forward or backward
def shift_datetime(datetime_list, days):
    return list(
        map(
            lambda d: d + datetime.timedelta(days=days),
            datetime_list,
        )
    )


# parse args
parser = argparse.ArgumentParser(description="analyze data.")
parser.add_argument("--input", required=True, type=str, help="event data file")
parser.add_argument(
    "--startdate", required=True, type=str, help="pandemic start date (YYYY-MM-DD)"
)
parser.add_argument("--outcsv", action="store_true")
args = parser.parse_args()

# args
log_filename = args.input
outcsv = args.outcsv
pandemic_start_date = args.startdate

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

# Analysis 1:
# calculate vaccine efficacy.
# vaccine efficacy (VE) is 1 - incidence rate of vac2 / incidence rate of novac.
# incidence rate is incidence per person day.
# unvaccinated individuals are defined as those for whom "vac1_shift_days" had not
# passed since receiving the first dose of vaccine.
# fully vaccinated individuals are defined as those for whom "vac2_shift_days" had
# passed since receiving the second dose of vaccine.
def calc_vaceff_incidence_per_person_day(
    vac1_shift_days=0, vac2_shift_days=7, pandemic_start_date="2021-09-01"
):
    # set diagram
    stat_start_date_time = start_date_time + datetime.timedelta(days=0)
    diagram = make_diagram(stat_start_date_time, vac1_shift_days, vac2_shift_days)
    statgui = StatGUI(diagram, person_event_data_list=person_event_data_list)

    # datetime of novac positive event
    novac_pos_event = floor_datetime(
        get_event(
            diagram, "pos < vac1 after {} days".format(vac1_shift_days), "PCR_positive"
        )
    )
    # datetime of vac1 positive event
    vac1_pos_event = floor_datetime(
        get_event(
            diagram,
            "vac1 after {} days <= pos < vac2 after {} days".format(
                vac1_shift_days, vac2_shift_days
            ),
            "PCR_positive",
        )
    )
    # datetime of vac2 positive event
    vac2_pos_event = floor_datetime(
        get_event(
            diagram, "vac2 after {} days < pos".format(vac2_shift_days), "PCR_positive"
        )
    )

    # datetime of vac1 and vac2
    vac1_event = floor_datetime(get_event(diagram, "total", "vac1"))
    vac2_event = floor_datetime(get_event(diagram, "total", "vac2"))

    # make dataframe
    start_str = start_date_time.strftime("%Y-%m-%d")
    end_str = end_date_time.strftime("%Y-%m-%d")
    date = pd.date_range(start=start_str, end=end_str, freq="D")
    df = pd.DataFrame(
        None,
        columns=["novac", "vac1", "vac2", "novac_pos", "vac1_pos", "vac2_pos"],
        index=date,
        dtype="int",
    )

    # make sorted event list including vac1 + 0 and vac2 + vac2_shift_days
    vac1_event_zip = zip(shift_datetime(vac1_event, 0), [0] * len(vac1_event))
    vac2_event_zip = zip(
        shift_datetime(vac2_event, vac2_shift_days), [1] * len(vac2_event)
    )
    event_zip = list(vac1_event_zip) + list(vac2_event_zip)
    event_zip = sorted(event_zip)

    novac_num = diagram("total").get_event_data_set("inbound").size()
    vac1_num = 0
    vac2_num = 0
    cur_date = start_date_time
    df.at[cur_date, "novac"] = novac_num
    df.at[cur_date, "vac1"] = vac1_num
    df.at[cur_date, "vac2"] = vac2_num
    df.at[cur_date, "novac_pos"] = 0
    df.at[cur_date, "vac1_pos"] = 0
    df.at[cur_date, "vac2_pos"] = 0

    for event_time, event_type in event_zip:
        if event_type == 0:
            novac_num -= 1
            vac1_num += 1
            df.at[event_time, "novac"] = novac_num
            df.at[event_time, "vac1"] = vac1_num
        if event_type == 1:
            vac1_num -= 1
            vac2_num += 1
            df.at[event_time, "vac1"] = vac1_num
            df.at[event_time, "vac2"] = vac2_num

    pos_num = 0
    for event_time in novac_pos_event:
        pos_num += 1
        df.at[event_time, "novac_pos"] = pos_num
    pos_num = 0
    for event_time in vac1_pos_event:
        pos_num += 1
        df.at[event_time, "vac1_pos"] = pos_num
    pos_num = 0
    for event_time in vac2_pos_event:
        pos_num += 1
        df.at[event_time, "vac2_pos"] = pos_num

    df = df.interpolate("ffill")

    # diff
    df["novac_pos_diff"] = df["novac_pos"].diff()
    df["vac1_pos_diff"] = df["vac1_pos"].diff()
    df["vac2_pos_diff"] = df["vac2_pos"].diff()

    # not infect
    df["novac_not_infect"] = df["novac"] - df["novac_pos"]
    df["vac2_not_infect"] = df["vac2"] - df["vac2_pos"]

    # person day
    drop_index = df.loc[df.index < pandemic_start_date].index
    df.loc[drop_index, "novac_not_infect"] = NaN
    df.loc[drop_index, "vac2_not_infect"] = NaN
    novac_pd = df["novac_not_infect"].sum()
    vac2_pd = df["vac2_not_infect"].sum()

    # pos
    start_index = start_date_time
    end_index = end_date_time
    novac_pos = df.loc[end_index, "novac_pos"] - df.loc[start_index, "novac_pos"]
    vac2_pos = df.loc[end_index, "vac2_pos"] - df.loc[start_index, "vac2_pos"]

    # incidence rate and efficacy
    vac0_ir = novac_pos / novac_pd
    vac2_ir = vac2_pos / vac2_pd
    vaceff = 1 - vac2_ir / vac0_ir

    if outcsv:
        df.to_csv(
            "{}_vac0shift_{}_vac1shift_{}.csv".format(
                log_filename, vac1_shift_days, vac2_shift_days
            )
        )

    return vaceff


# Analysis 2:
# calculate vaccine efficacy.
# vaccine efficacy (VE) is 1 - incidence rate of vac2 / incidence rate of novac.
# incidence rate is calculated by averaging daily incidence per person day.
# definitions of unvaccinated individuals and fully vaccinated individuals are
# same as those of Analysis 1.
def calc_vaceff_average_daily_incidence_per_person_day(
    vac1_shift_days=0,
    vac2_shift_days=7,
    pos_shift_days=4,
    pandemic_start_date="2021-09-01",
):
    # set diagram
    stat_start_date_time = start_date_time + datetime.timedelta(days=0)
    diagram = make_diagram(
        stat_start_date_time,
        vac1_shift_days + pos_shift_days,
        vac2_shift_days + pos_shift_days,
    )
    statgui = StatGUI(diagram, person_event_data_list=person_event_data_list)

    # datetime of novac positive event
    novac_pos_event = floor_datetime(
        get_event(
            diagram,
            "pos < vac1 after {} days".format(vac1_shift_days + pos_shift_days),
            "PCR_positive",
        )
    )
    # datetime of vac1 positive event
    vac1_pos_event = floor_datetime(
        get_event(
            diagram,
            "vac1 after {} days <= pos < vac2 after {} days".format(
                vac1_shift_days + pos_shift_days, vac2_shift_days + pos_shift_days
            ),
            "PCR_positive",
        )
    )
    # datetime of vac2 positive event
    vac2_pos_event = floor_datetime(
        get_event(
            diagram,
            "vac2 after {} days < pos".format(vac2_shift_days + pos_shift_days),
            "PCR_positive",
        )
    )

    # datetime of vac1 and vac2
    vac1_event = floor_datetime(get_event(diagram, "total", "vac1"))
    vac2_event = floor_datetime(get_event(diagram, "total", "vac2"))

    # make dataframe
    start_str = start_date_time.strftime("%Y-%m-%d")
    end_str = end_date_time.strftime("%Y-%m-%d")
    date = pd.date_range(start=start_str, end=end_str, freq="D")
    df = pd.DataFrame(
        None,
        columns=["novac", "vac1", "vac2", "novac_pos", "vac1_pos", "vac2_pos"],
        index=date,
        dtype="int",
    )

    # make sorted event list including vac1 + vac1_shift_days and vac2 + vac2_shift_days
    vac1_event_zip = zip(
        shift_datetime(vac1_event, vac1_shift_days), [0] * len(vac1_event)
    )
    vac2_event_zip = zip(
        shift_datetime(vac2_event, vac2_shift_days), [1] * len(vac2_event)
    )
    event_zip = list(vac1_event_zip) + list(vac2_event_zip)
    event_zip = sorted(event_zip)

    novac_num = diagram("total").get_event_data_set("inbound").size()
    vac1_num = 0
    vac2_num = 0
    cur_date = start_date_time
    df.at[cur_date, "novac"] = novac_num
    df.at[cur_date, "vac1"] = vac1_num
    df.at[cur_date, "vac2"] = vac2_num
    df.at[cur_date, "novac_pos"] = 0
    df.at[cur_date, "vac1_pos"] = 0
    df.at[cur_date, "vac2_pos"] = 0

    for event_time, event_type in event_zip:
        if event_type == 0:
            novac_num -= 1
            vac1_num += 1
            df.at[event_time, "novac"] = novac_num
            df.at[event_time, "vac1"] = vac1_num
        if event_type == 1:
            vac1_num -= 1
            vac2_num += 1
            df.at[event_time, "vac1"] = vac1_num
            df.at[event_time, "vac2"] = vac2_num

    pos_num = 0
    for event_time in novac_pos_event:
        pos_num += 1
        df.at[event_time, "novac_pos"] = pos_num
    pos_num = 0
    for event_time in vac1_pos_event:
        pos_num += 1
        df.at[event_time, "vac1_pos"] = pos_num
    pos_num = 0
    for event_time in vac2_pos_event:
        pos_num += 1
        df.at[event_time, "vac2_pos"] = pos_num

    df = df.interpolate("ffill")

    # diff
    df["novac_pos_diff"] = df["novac_pos"].diff()
    df["vac1_pos_diff"] = df["vac1_pos"].diff()
    df["vac2_pos_diff"] = df["vac2_pos"].diff()

    # infect pct per day
    novac_day_shift = "novac_day_shift_{}".format(pos_shift_days)
    vac2_day_shift = "vac2_day_shift_{}".format(pos_shift_days)
    df[novac_day_shift] = df["novac"].shift(pos_shift_days) - df["novac_pos"].shift(1)
    df[vac2_day_shift] = df["vac2"].shift(pos_shift_days) - df["vac2_pos"].shift(1)

    df["novac_infect_pct_per_day"] = df["novac_pos_diff"] / df[novac_day_shift]
    df["vac2_infect_pct_per_day"] = df["vac2_pos_diff"] / df[vac2_day_shift]
    df["days"] = pd.Series(range(1, len(df.index) + 1)).values.tolist()

    drop_index = df.loc[df.index < pandemic_start_date].index
    df["days"] = df["days"].shift(drop_index.size + pos_shift_days + 1)
    df.loc[drop_index, "novac_infect_pct_per_day"] = NaN
    df.loc[drop_index, "vac2_infect_pct_per_day"] = NaN

    df["novac_infect_pct_per_day_cum"] = df["novac_infect_pct_per_day"].cumsum()
    df["vac2_infect_pct_per_day_cum"] = df["vac2_infect_pct_per_day"].cumsum()
    df["novac_infect_pct_per_day_cum_avg"] = (
        df["novac_infect_pct_per_day_cum"] / df["days"]
    )
    df["vac2_infect_pct_per_day_cum_avg"] = (
        df["vac2_infect_pct_per_day_cum"] / df["days"]
    )

    df["vac2_eff_pct_per_day_cum_avg"] = (
        1.0
        - df["vac2_infect_pct_per_day_cum_avg"] / df["novac_infect_pct_per_day_cum_avg"]
    )
    end_index = df.index.max()

    if outcsv:
        df.to_csv(
            "{}_vac0shift_{}_vac1shift_{}_pos_shift_days_{}.csv".format(
                log_filename, vac1_shift_days, vac2_shift_days, pos_shift_days
            )
        )

    return df.loc[end_index, "vac2_eff_pct_per_day_cum_avg"]


vaceff_incidence_per_person_day = calc_vaceff_incidence_per_person_day(
    vac1_shift_days=0, vac2_shift_days=7, pandemic_start_date=pandemic_start_date
)
vaceff_average_daily_incidence_per_person_day = (
    calc_vaceff_average_daily_incidence_per_person_day(
        vac1_shift_days=0,
        vac2_shift_days=7,
        pos_shift_days=4,
        pandemic_start_date=pandemic_start_date,
    )
)

print("vaceff_incidence_per_person_day = {}".format(vaceff_incidence_per_person_day))
print(
    "vaceff_average_daily_incidence_per_person_day = {}".format(
        vaceff_average_daily_incidence_per_person_day
    )
)
