"""Read the monthly trip files into one compact DataFrame and the zone lookup.

Nothing is filtered here. Types are narrowed to keep 20M rows in about 1.5 GB of RAM,
and a few derived columns (duration, speed, calendar fields, source file) are added.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .settings import RAW, params

FLOAT_COLS = ["trip_distance", "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
              "improvement_surcharge", "total_amount", "congestion_surcharge", "Airport_fee"]


def read_month(month: str) -> pd.DataFrame:
    p = params()["data"]
    t = pq.read_table(RAW / f"{p['service']}_tripdata_{month}.parquet")
    # Older files spell the column "airport_fee"; normalise.
    t = t.rename_columns(["Airport_fee" if c.lower() == "airport_fee" else c for c in t.column_names])
    df = t.to_pandas()
    out = pd.DataFrame({
        "vendor": df["VendorID"].astype("int8"),
        "pickup": df["tpep_pickup_datetime"].astype("datetime64[s]"),
        "dropoff": df["tpep_dropoff_datetime"].astype("datetime64[s]"),
        "passengers": df["passenger_count"].astype("Float32"),
        "ratecode": df["RatecodeID"].astype("Float32"),
        "store_fwd": df["store_and_fwd_flag"].astype("category"),
        "pu": df["PULocationID"].astype("int16"),
        "do": df["DOLocationID"].astype("int16"),
        "payment": df["payment_type"].astype("int8"),
    })
    for c in FLOAT_COLS:
        out[c.lower()] = df[c].astype("float32")
    out["file_month"] = month
    return out


def load_trips(months: list[str] | None = None) -> pd.DataFrame:
    months = months or params()["data"]["months"]
    trips = pd.concat([read_month(m) for m in months], ignore_index=True)
    trips["file_month"] = trips["file_month"].astype("category")
    dur = (trips["dropoff"] - trips["pickup"]).dt.total_seconds() / 60
    trips["duration_min"] = dur.astype("float32")
    with np.errstate(divide="ignore", invalid="ignore"):
        trips["speed_mph"] = (trips["trip_distance"] / (trips["duration_min"] / 60)).astype("float32")
    trips["hour"] = trips["pickup"].dt.hour.astype("int8")
    trips["dow"] = trips["pickup"].dt.dayofweek.astype("int8")
    return trips


def load_zones() -> pd.DataFrame:
    z = pd.read_csv(RAW / "taxi_zone_lookup.csv")
    z.columns = ["zone_id", "borough", "zone", "service_zone"]
    return z
