import os, sys
import argparse
import pickle
import datetime
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

# import veame
from veame import *


def make_diagram():
    def level0(r0):
        r1 = StatNode("Randomized", wh=(2, 0.75), condition=EventLog())
        r0.set_branch([r1])

        r1_v1 = StatNode("Randomized1", wh=(2, 0.75), condition=EventLog("vaccine"))
        r1_p1 = StatNode("Randomized2", wh=(2, 0.75), condition=EventLog("placebo"))
        r1.set_branch([r1_v1, r1_p1], "center")

        r2_v1 = StatNode("Selected1", wh=(2, 0.75), condition=EventLog())
        r2_v2 = StatNode(
            "Exception1 (infect>2)",
            wh=(2, 0.75),
            condition=EventLog("infect_c19#2", 1),
        )
        r2_v3 = StatNode(
            "Exception1 (fever)",
            wh=(2, 0.75),
            condition=EventLog("feversum_up_to_1(eval_func)", 2),
        )
        r2_p1 = StatNode("Selected2", wh=(2, 0.75), condition=EventLog())
        r2_p2 = StatNode(
            "Exception2 (infect>2)",
            wh=(2, 0.75),
            condition=EventLog("infect_c19#2", 1),
        )
        r2_p3 = StatNode(
            "Exception2 (fever)",
            wh=(2, 0.75),
            condition=EventLog("feversum_up_to_1(eval_func)", 2),
        )

        r1_v1.set_branch([r2_v1, r2_v2, r2_v3])
        r1_p1.set_branch([r2_p1, r2_p2, r2_p3])
        return r2_v1, r2_p1

    def level1(r2_v, r2_p):
        ##### Dose 1
        r3_v1 = StatNode("Receive VAC1", wh=(1.8, 0.75), condition=EventLog("vac1"))
        r3_v2 = StatNode(
            "No VAC1",
            wh=(1.8, 0.75),
            condition=~EventLog("vac1"),
        )
        r3_v3 = StatNode(
            "Positive (before VAC1)",
            wh=(1.8, 0.75),
            condition=EventLog("vac1") > EventLog("PCR_positive"),
        )
        r3_v4 = StatNode(
            "Death (before VAC1)",
            wh=(1.8, 0.75),
            condition=EventLog("vac1") > EventLog("death"),
        )
        r2_v.set_branch([r3_v1, r3_v2, r3_v3, r3_v4], "left")

        r3_p1 = StatNode("Receive PLC1", wh=(1.8, 0.75), condition=EventLog("vac1"))
        r3_p2 = StatNode(
            "No PLC1",
            wh=(1.8, 0.75),
            condition=~EventLog("vac1"),
        )
        r3_p3 = StatNode(
            "Positive (before PLC1)",
            wh=(1.8, 0.75),
            condition=EventLog("vac1") > EventLog("PCR_positive"),
        )
        r3_p4 = StatNode(
            "Death (before PLC1)",
            wh=(1.8, 0.75),
            condition=EventLog("vac1") > EventLog("death"),
        )
        r2_p.set_branch([r3_p1, r3_p2, r3_p3, r3_p4], "left")
        return r3_v1, r3_p1

    def add_PCR_positive_level(r, event_log, day_list, VAC_or_PCR):
        r_list = []
        for day in day_list:
            r_tmp = StatNode(
                "Positive (before {}days from {})".format(day, VAC_or_PCR),
                wh=(1.8, 0.75),
                condition=event_log + EventLog(datetime.timedelta(days=day))
                > EventLog("PCR_positive"),
            )
            r_list.append(r_tmp)
        r.set_branch(r_list, "left")

    def level2(r3_v, r3_p):
        EventLog_VAC1_14d = EventLog("vac1") + EventLog(datetime.timedelta(days=14))
        r4_v1 = StatNode("14days after VAC1", wh=(1.8, 0.75), condition=EventLog())
        r4_v2 = StatNode(
            "Positive (before 14days from VAC1) branch",
            wh=(1.8, 0.75),
            condition=EventLog_VAC1_14d > EventLog("PCR_positive"),
        )
        r4_v3 = StatNode(
            "ADV or Death (before 14days from VAC1)",
            wh=(1.8, 0.75),
            condition=(EventLog_VAC1_14d > EventLog("ADV1_severe"))
            | (EventLog_VAC1_14d > EventLog("death")),
        )
        r3_v.set_branch([r4_v1, r4_v2, r4_v3], "left")
        add_PCR_positive_level(r4_v2, EventLog("vac1"), [14, 10, 5], "VAC1")

        r4_p1 = StatNode(
            "14days after PLC1",
            wh=(1.8, 0.75),
            condition=EventLog(),
        )
        r4_p2 = StatNode(
            "Positive (before 14days from PLC1) branch",
            wh=(1.8, 0.75),
            condition=EventLog_VAC1_14d > EventLog("PCR_positive"),
        )
        r4_p3 = StatNode(
            "ADV or Death (before 14days from PLC1)",
            wh=(1.8, 0.75),
            condition=(EventLog_VAC1_14d > EventLog("ADV1_severe"))
            | (EventLog_VAC1_14d > EventLog("death")),
        )
        r3_p.set_branch([r4_p1, r4_p2, r4_p3], "left")
        add_PCR_positive_level(r4_p2, EventLog("vac1"), [14, 10, 5], "PLC1")
        return r4_v1, r4_p1

    def level3(r4_v, r4_p):
        ##### Dose 2
        r5_v1 = StatNode("Receive VAC2", wh=(1.8, 0.75), condition=EventLog("vac2"))
        r5_v2 = StatNode(
            "No VAC2",
            wh=(1.8, 0.75),
            condition=~EventLog("vac2"),
        )
        r5_v3 = StatNode(
            "Positive (before VAC2)",
            wh=(1.8, 0.75),
            condition=EventLog("vac2") > EventLog("PCR_positive"),
        )
        r5_v4 = StatNode(
            "ADV or Death (before VAC2)",
            wh=(1.8, 0.75),
            condition=(EventLog("vac2") > EventLog("ADV1_severe"))
            | (EventLog("vac2") > EventLog("death")),
        )
        r4_v.set_branch([r5_v1, r5_v2, r5_v3, r5_v4], "left")

        r5_p1 = StatNode("Receive PLC2", wh=(1.8, 0.75), condition=EventLog("vac2"))
        r5_p2 = StatNode(
            "No PLC2",
            wh=(1.8, 0.75),
            condition=~EventLog("vac2"),
        )
        r5_p3 = StatNode(
            "Positive (before PLC2)",
            wh=(1.8, 0.75),
            condition=EventLog("vac2") > EventLog("PCR_positive"),
        )
        r5_p4 = StatNode(
            "ADV or Death (before PLC2)",
            wh=(1.8, 0.75),
            condition=(EventLog("vac2") > EventLog("ADV1_severe"))
            | (EventLog("vac2") > EventLog("death")),
        )
        r4_p.set_branch([r5_p1, r5_p2, r5_p3, r5_p4], "left")
        return r5_v1, r5_p1

    def level4(r5_v, r5_p):
        EventLog_VAC2_7d = EventLog("vac2") + EventLog(datetime.timedelta(days=7))
        r6_v1 = StatNode("7days after VAC2", wh=(1.8, 0.75), condition=EventLog())
        r6_v2 = StatNode(
            "Positive (before 7days from VAC2) branch",
            wh=(1.8, 0.75),
            condition=EventLog_VAC2_7d > EventLog("PCR_positive"),
        )
        r6_v3 = StatNode(
            "ADV or Death (before 7days from VAC2)",
            wh=(1.8, 0.75),
            condition=(EventLog_VAC2_7d > EventLog("ADV2_severe"))
            | (EventLog_VAC2_7d > EventLog("death")),
        )
        r5_v.set_branch([r6_v1, r6_v2, r6_v3], "left")
        add_PCR_positive_level(r6_v2, EventLog("vac2"), [7, 3], "VAC2")

        r6_p1 = StatNode(
            "7days after PLC2",
            wh=(1.8, 0.75),
            condition=EventLog(),
        )
        r6_p2 = StatNode(
            "Positive (before 7days from PLC2) branch",
            wh=(1.8, 0.75),
            condition=EventLog_VAC2_7d > EventLog("PCR_positive"),
        )
        r6_p3 = StatNode(
            "ADV or Death (before 7days from PLC2)",
            wh=(1.8, 0.75),
            condition=(EventLog_VAC2_7d > EventLog("ADV2_severe"))
            | (EventLog_VAC2_7d > EventLog("death")),
        )
        r5_p.set_branch([r6_p1, r6_p2, r6_p3], "left")
        add_PCR_positive_level(r6_p2, EventLog("vac2"), [7, 3], "PLC2")
        return r6_v1, r6_p1

    def level5(r6_v, r6_p):
        ##### VAC2_7d
        r7_v1 = StatNode(
            "Negative after 7days from VAC2",
            wh=(1.8, 0.75),
            condition=~EventLog("PCR_positive")
            & ~EventLog("ADV1_severe")
            & ~EventLog("ADV2_severe")
            & ~EventLog("death"),
        )
        r7_v2 = StatNode(
            "Positive after 7days from VAC2",
            wh=(1.8, 0.75),
            condition=EventLog("PCR_positive"),
        )
        r7_v3 = StatNode(
            "ADV or Death",
            wh=(1.8, 0.75),
            condition=EventLog("ADV2_severe") | EventLog("death"),
        )
        r6_v.set_branch([r7_v1, r7_v2, r7_v3], "left")

        r7_p1 = StatNode(
            "Negative after 7days from PLC2",
            wh=(1.8, 0.75),
            condition=~EventLog("PCR_positive")
            & ~EventLog("ADV1_severe")
            & ~EventLog("ADV2_severe")
            & ~EventLog("death"),
        )
        r7_p2 = StatNode(
            "Positive after 7days from PLC2",
            wh=(1.8, 0.75),
            condition=EventLog("PCR_positive"),
        )
        r7_p3 = StatNode(
            "ADV or Death",
            wh=(1.8, 0.75),
            condition=EventLog("ADV2_severe") | EventLog("death"),
        )
        r6_p.set_branch([r7_p1, r7_p2, r7_p3], "left")

        return r7_v1, r7_p1

    r0 = StatNode("Eligibility", wh=(2, 0.75))
    r2_v, r2_p = level0(r0)
    r3_v, r3_p = level1(r2_v, r2_p)
    r4_v, r4_p = level2(r3_v, r3_p)
    r5_v, r5_p = level3(r4_v, r4_p)
    r6_v, r6_p = level4(r5_v, r5_p)
    r7_v, r7_p = level5(r6_v, r6_p)
    return r0


def count_event(event_data_list, show=True):
    r0 = make_diagram()
    id_manager = IdManager()
    event_data_set = EventDataSet(id_manager, event_data_list)
    for event_data_info in event_data_set.get_event_data_info_list():
        r0.send(event_data_info, ignore_error=True)
    if show:
        fig = plt.figure()
        ax = plt.axes()
        fig.subplots_adjust(left=0.0, bottom=0.0, right=1.0, top=1.0)
        r0.draw_all(fig, ax, equal_arrange=False)
        ax.set_aspect("equal", anchor="C", adjustable="datalim")
        ax.autoscale()
        ax.axis("off")
        plt.show()
    else:
        r0.draw_all()
    return r0


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


def get_positive_event(diagram, name, origin_event_name):
    r = diagram(name)
    event_data_set, eval_error = r.event_eval(
        EventLog("PCR_positive") - EventLog(origin_event_name), "inbound"
    )
    return sorted(event_data_set)


def check_vac2(vac2_req_n):
    event_data_set = diagram.get_event_data_set(count_type="inbound")
    event_data_set, eval_error = event_data_set.get_event_data_set(
        (EventLog("vac2_req", vac2_req_n))
        & (~EventLog("vac2_req", vac2_req_n + 1))
        & (EventLog("vac2"))
    )
    event_data_set, eval_error = event_data_set.get_event_data_set(
        EventLog("vac2")
        < EventLog("vac2_req", vac2_req_n) + EventLog(datetime.timedelta(days=1))
    )
    return event_data_set


choices = [
    "show",
    "graph",
    "report_html",
    "report_md",
]
parser = argparse.ArgumentParser(description="show diagram.")
parser.add_argument("--input", required=True, type=str, help="event data file")
parser.add_argument(
    "--task", required=True, type=str, choices=choices, help="task name"
)
parser.add_argument("--report", type=str, help="path to save report")

args = parser.parse_args()
task_name = args.task
log_filename = args.input
report_path = args.report
fin = open(log_filename, "rb")
person_event_data_list = pickle.load(fin)
fin.close()
print(len(person_event_data_list))

diagram = make_diagram()
statgui = StatGUI(diagram, person_event_data_list=person_event_data_list)

if task_name == "show":
    statgui.show()

if task_name in ["report_html", "report_md"]:
    if report_path is None:
        current_dir = os.path.dirname(__file__)
        report_path = os.path.join(current_dir, "report")
        os.makedirs(report_path, exist_ok=True)
    if task_name == "report_html":
        statgui.make_report(report_path, format="html")
    if task_name == "report_md":
        statgui.make_report(report_path, format="md")

if task_name == "graph":
    pos_vac2 = get_positive_event(diagram, "Receive VAC1", "vac1")
    pos_plc2 = get_positive_event(diagram, "Receive PLC1", "vac1")

    line_x_vac2, line_y_vac2 = calc_event_line(pos_vac2)
    line_x_plc2, line_y_plc2 = calc_event_line(pos_plc2)

    # plot
    fig = plt.figure()
    ax = fig.add_subplot()
    ax.set_title("Event Graph")
    ax.set_xlabel("Days")
    ax.set_ylabel("Positive")
    ax.plot(line_x_vac2, line_y_vac2, color="red", label="vac2")
    ax.plot(line_x_plc2, line_y_plc2, color="blue", label="plc2")
    ax.legend(bbox_to_anchor=(1, 1), loc="upper right", borderaxespad=1, fontsize=10)
    plt.show()
