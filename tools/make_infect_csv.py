import argparse
import pandas as pd
import datetime

# parse
parser = argparse.ArgumentParser(
    description="make infect ratio csv.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Global data:
 https://github.com/CSSEGISandData/COVID-19/blob/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv
US State data:
 https://github.com/CSSEGISandData/COVID-19/blob/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv""",
)

choices = ["country", "region", "us_state"]
parser.add_argument(
    "--type", required=True, type=str, choices=choices, help="item type"
)
parser.add_argument(
    "--name", required=True, type=str, help="item name. for example: San Francisco"
)
parser.add_argument(
    "--input", required=True, type=str, default=None, help="confirmed data csv"
)
parser.add_argument("--output", type=str, default=None, help="output csv")

args = parser.parse_args()

item_type = args.type
item_name = args.name
input_csv = args.input
output_csv = args.output

if item_type == "country" or item_type == "region":
    # read csv
    df = pd.read_csv(input_csv, index_col=[0, 1, 2, 3])
    df = df.loc[(pd.NA, item_name), :]
    df.index = [item_name]
    df = df.T

    # make index from date
    df.index = [datetime.datetime.strptime(x, "%m/%d/%y") for x in df.index]

    # calculate daily confirmed case
    df[item_name] = df[item_name].diff()
    df = df.dropna(axis=0)

    # resample weekly
    df = df.resample(rule="W").mean()

    # save csv
    df.to_csv(output_csv)

if item_type == "us_state":
    # read csv
    df = pd.read_csv(input_csv, index_col=[1, 5])
    df = df.loc[("US", item_name), :]
    df.index = [item_name]
    df = df.T

    # drop rows
    df = df.drop(
        [
            "UID",
            "iso3",
            "code3",
            "FIPS",
            "item_name",
            "Country_Region",
            "Lat",
            "Long_",
            "Combined_Key",
        ]
    )

    # make index from date
    df.index = [datetime.datetime.strptime(x, "%m/%d/%y") for x in df.index]

    # calculate daily confirmed case
    df = df.astype({item_name: int})
    df[item_name] = df[item_name].diff()
    df = df.dropna(axis=0)

    # resample weekly
    df = df.resample(rule="W").mean()

    # adjust data (incorrect data?)
    df = df.mask(df < 0, 0)

    # save csv
    df.to_csv(output_csv)
