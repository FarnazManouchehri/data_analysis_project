# Project card — NYC yellow-taxi zone demand

- **Student:** Farnaz Haj-Manouchehri (فرناز حاج‌منوچهری), ID 401100111
- **Course:** Data Analysis, Fall 1405 — **Track A: NYC TLC Trip Record Data**
- **Phase:** 1 (fixed 2026-11-02)

| # | Item | Decision |
|---|---|---|
| 1 | Track and subset | Track A. **Yellow taxi (TPEP)** trips, pickups **2024-01-01 to 2024-06-30** (6 monthly Parquet files, 20,332,093 raw rows) + `taxi_zone_lookup.csv`. One service only, so that behaviour is consistent; six months give 4 training months, 1 validation month and 1 locked test month, and fit in 8 GB of RAM. Fixed in `params.toml` before any modelling. |
| 2 | Working title | *Where and when will a taxi be needed? Day-ahead hourly pickup demand by taxi zone.* |
| 3 | Real decision supported | Fleet and shift planning (how many cabs, where, when), early warning when demand departs from forecast, and TLC planning (airport taxi stands, policy evaluation). |
| 4 | Unit of analysis / prediction | Analysis: one trip. Prediction: one **zone × clock hour**, issued at 00:00 of day D for all 24 hours of day D+1. |
| 5 | Target population / scope | Street-hail and dispatched yellow-taxi pickups inside the 263 NYC taxi zones, H1 2024. Out of scope: green taxis, Uber/Lyft (FHVHV), unmet demand, trips after congestion pricing (Jan 2025). |
| 6 | Main question | Using only information available a day ahead, how accurately can hourly pickups be forecast for each active zone, and by how much does a learned model beat a seasonal profile? |
| 7 | Target | `pickups` = count of trips starting in zone z during hour h (zeros included). 134 active zones (≥ 10 pickups/day in train) cover 99.55% of train pickups. Mean 33.9, median 2, max 838 per zone-hour; 27.6% zeros. |
| 8 | Initial baseline | Zone × weekday × hour mean from train: **WAPE 20.0%** (MAE 7.27, RMSE 18.52) on validation. Others: lag-168 22.2%, lag-24 28.2%, zone mean 61.4%. |
| 9 | Metrics | Primary **WAPE**. Secondary MAE, RMSE, bias, peak-hour WAPE, WAPE per zone group (core Manhattan / airports / outer boroughs). Day-level bootstrap CIs. |
| 10 | Split | Temporal on pickup hour: train Jan–Apr (2,904 h), valid May (744 h), **test June (720 h), locked**. DST gap hour (2024-03-10 02:00) excluded. |
| 11 | Leakage risks | Lags < 24 h and rolling windows that touch day D; post-trip fields (duration, distance, fare, tip, destination); global statistics or active-zone list computed on all months; realised weather; later TLC corrections. Demo: neighbour features under a random split under-state WAPE by ~22% (14.7% vs 18.8%). |
| 12 | Unsupervised component | k-means / hierarchical clustering of zones on normalised 168-hour weekly profiles (silhouette + seed/subsample stability), PCA for visualisation, clustering of days to isolate holidays and anomalies. |
| 13 | Track-specific advanced part | Time series and events: day-ahead forecasting with rolling-origin evaluation, residual-based anomaly detection (separating data errors from real events using a holiday calendar and NOAA weather), drift analysis from valid to test. |
| 14 | Ethics, privacy, bias | Re-identification risk of rare zone pairs plus exact times → publish aggregates only and suppress cells < 10 trips. Coverage bias: yellow cabs are Manhattan-centric; the model must not be used to justify withdrawing service from outer boroughs. Realised ≠ true demand (supply feedback loop). Not a tool to monitor or penalise drivers. Associations are not causal claims. |
