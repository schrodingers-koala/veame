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
        r1 = StatNode("Vaccination", wh=(2, 0.75), condition=EventLog())
        r0.set_branch([r1])

        r1_v0 = StatNode(
            "Get no VAC", wh=(2, 0.75), condition=EventLog("select_no_vac")
        )
        r1_v1 = StatNode("Get 1 VAC", wh=(2, 0.75), condition=EventLog("select_1_vac"))
        r1_v2 = StatNode("Get 2 VAC", wh=(2, 0.75), condition=EventLog("select_2_vac"))
        r1.set_branch([r1_v0, r1_v1, r1_v2], "center")

        return [r1_v0, r1_v1, r1_v2]

    def level1(vac_i, r2_v):
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

        return r3_v1

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

    def level2(vac_i, r3_v):
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

        return r4_v1

    def level3(vac_i, r4_v):
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

        return r5_v1

    def level4(vac_i, r5_v):
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

        return r6_v1

    def level5(vac_i, r6_v):
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

        return r7_v1

    r0 = StatNode("Eligibility", wh=(2, 0.75))
    r1_list = level0(r0)
    for vac_i, r2_v in enumerate(r1_list):
        r3_v = level1(vac_i, r2_v)
        r4_v = level2(vac_i, r3_v)
        r5_v = level3(vac_i, r4_v)
        r6_v = level4(vac_i, r5_v)
        r7_v = level5(vac_i, r6_v)
    return r0


choices = [
    "show",
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
