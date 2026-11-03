# TLC data sources

**Source:** NYC Taxi & Limousine Commission, *TLC Trip Record Data* (https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page). The files are public. They are downloaded by `python -m taxidemand.fetch` into `tlc/downloads/`, not stored in git.

| File | Rows | SHA-256 |
|---|---|---|
| yellow_tripdata_2024-01.parquet | 2,964,624 | see `params.toml` |
| yellow_tripdata_2024-02.parquet | 3,007,526 | 〃 |
| yellow_tripdata_2024-03.parquet | 3,582,628 | 〃 |
| yellow_tripdata_2024-04.parquet | 3,514,289 | 〃 |
| yellow_tripdata_2024-05.parquet | 3,723,833 | 〃 |
| yellow_tripdata_2024-06.parquet | 3,539,193 | 〃 |
| taxi_zone_lookup.csv | 265 zones | 〃 |

**Generation:** trip records are captured by taximeters / TPEP systems and submitted to TLC by technology vendors (1 = Creative Mobile Technologies, 2 = Curb Mobility, 6 = Myle Technologies). The data is observational and administrative. Location is given only as a taxi zone. There is no trip, driver or passenger ID.

**Schema (19 columns):** VendorID, tpep_pickup_datetime, tpep_dropoff_datetime, passenger_count, trip_distance, RatecodeID, store_and_fwd_flag, PULocationID, DOLocationID, payment_type (0 = Flex Fare, 1 card, 2 cash, 3 no charge, 4 dispute), fare_amount, extra, mta_tax, tip_amount, tolls_amount, improvement_surcharge, total_amount, congestion_surcharge, Airport_fee. Types and ranges: `artifacts/phase1/tables/schema.csv`.

**Known issues (see report section 5):** a 9.7% block in which five columns are missing together (payment_type 0); vendor 1 folds the congestion and airport fees into `extra`; refund/void rows with negative amounts; 39 timestamps outside the period; the non-existent DST hour on 2024-03-10.

**Derived:** `tlc/derived/zone_hour_panel.parquet` — 263 zones × 4,368 hours of pickup counts (written by `taxidemand.run_all`).
