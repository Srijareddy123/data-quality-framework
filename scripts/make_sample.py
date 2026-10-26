"""Build the committed demo sample from the public NYC TLC yellow taxi file (January 2024).

Usage: python scripts/make_sample.py [path-to-parquet]
Without an argument the parquet file is downloaded (about 50 MB) to a temp folder.
Writes data/sample/reference.csv (3000 rows, the baseline) and
data/sample/loads.csv (7000 rows, the pool that demo loads are cut from).
"""

import sys
import tempfile
import urllib.request
from pathlib import Path

import pandas as pd

URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet"
COLUMNS = [
    "VendorID",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "RatecodeID",
    "store_and_fwd_flag",
    "PULocationID",
    "DOLocationID",
    "payment_type",
    "fare_amount",
    "tip_amount",
    "tolls_amount",
    "total_amount",
    "congestion_surcharge",
]
SEED = 42
OUT = Path(__file__).resolve().parents[1] / "data" / "sample"


def main() -> None:
    if len(sys.argv) > 1:
        src = Path(sys.argv[1])
    else:
        src = Path(tempfile.mkdtemp()) / "yellow.parquet"
        urllib.request.urlretrieve(URL, src)
    df = pd.read_parquet(src, columns=COLUMNS)
    in_month = df["tpep_pickup_datetime"].between("2024-01-01", "2024-01-31 23:59:59")
    df = df[in_month].sample(n=10_000, random_state=SEED).reset_index(drop=True)
    df = df.round({c: 2 for c in df.select_dtypes("float").columns})
    OUT.mkdir(parents=True, exist_ok=True)
    df.iloc[:3000].to_csv(OUT / "reference.csv", index=False)
    df.iloc[3000:].reset_index(drop=True).to_csv(OUT / "loads.csv", index=False)
    print(f"wrote {OUT}/reference.csv and loads.csv")


if __name__ == "__main__":
    main()
