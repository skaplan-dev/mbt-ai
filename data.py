import boto3
from io import BytesIO
import pandas as pd
import pathlib
from utils import get_station_by_id

s3 = boto3.client("s3")
cloudfront = boto3.client("cloudfront")

BUCKET = "tm-mbta-performance"

tt_prefix = "SlowZones/traveltimes/"
dwell_prefix = "SlowZones/dwells/"


def generate_natural_language(row, date):
    return f"On {date}, the travel time between {row['fr']} and {row['to']} had a 25th percentile of {row['25%_tt']} seconds, a median of {row['50%_tt']} seconds, and a 75th percentile of {row['75%_tt']} seconds. There were {row['count_tt']} recorded trips, with a maximum of {row['max_tt']} seconds, a mean of {row['mean_tt']} seconds, and a minimum of {row['min_tt']} seconds. The travel time standard deviation was {row['std_tt']} seconds. The 10th percentile was {row['10%_tt']} seconds and the 90th percentile was {row['90%_tt']} seconds. The route color was {row['color_tt']}. The dwell time had a 25th percentile of {row['25%_dwell']} seconds, a median of {row['50%_dwell']} seconds, and a 75th percentile of {row['75%_dwell']} seconds. There were {row['count_dwell']} recorded dwell times, with a maximum of {row['max_dwell']} seconds, a mean of {row['mean_dwell']} seconds, and a minimum of {row['min_dwell']} seconds. The dwell time standard deviation was {row['std_dwell']} seconds. The 10th percentile was {row['10%_dwell']} seconds and the 90th percentile was {row['90%_dwell']} seconds. The route color was {row['color_dwell']}. The origin station ID is {row['fr_id']}, and the destination station ID is {row['to_id']}."


def get_tt_key(color, pair):
    return pathlib.Path(tt_prefix, color, f"{pair.fr}_{pair.to}").with_suffix(".csv.gz")


def get_dwell_key(color, pair):
    return pathlib.Path(dwell_prefix, color, f"{pair.fr}_{pair.to}").with_suffix(
        ".csv.gz"
    )


traveltimes = [
    x["Key"] for x in s3.list_objects(Bucket=BUCKET, Prefix=tt_prefix)["Contents"]
]
dwells = [
    x["Key"] for x in s3.list_objects(Bucket=BUCKET, Prefix=dwell_prefix)["Contents"]
]


def download(key):
    # TODO: handle missing key

    key = str(key)  # in case it's a pathlib.Path
    print("downloading", key)

    obj = s3.get_object(Bucket=BUCKET, Key=key)

    buffer = BytesIO()
    buffer.write(obj["Body"].read())
    buffer.seek(0)
    df = pd.read_csv(buffer, compression="gzip", encoding="utf-8")

    df.service_date = pd.to_datetime(df.service_date).dt.date

    return df


COLORS = ["Red", "Blue", "Orange"]


def gather_data_for_stop_pair(key):
    p = pathlib.Path(key)
    color = p.parent.name
    stem = p.name
    fr, to = p.stem.split(".")[0].split("_")

    tt_key = pathlib.Path("SlowZones/traveltimes") / color / stem
    dwell_key = pathlib.Path("SlowZones/dwells") / color / stem

    tts = download(tt_key).set_index("service_date")
    dwells = download(dwell_key).set_index("service_date")

    tts["color"] = color
    tts["fr"] = get_station_by_id(fr)
    tts["to"] = get_station_by_id(to)

    dwells["color"] = color
    dwells["fr_id"] = fr
    dwells["to_id"] = to

    stop_pair_data = tts.join(dwells, how="outer", lsuffix="_tt", rsuffix="_dwell")
    return stop_pair_data


def gather_all_stop_pairs_data():
    keys = [k for k in traveltimes for c in COLORS if c in k]
    all_data = pd.concat([gather_data_for_stop_pair(o) for o in keys])
    return all_data


if __name__ == "__main__":
    all_stop_pairs_data = gather_all_stop_pairs_data()
    all_stop_pairs_data.to_csv("./data/all_stop_pairs_data.csv")
