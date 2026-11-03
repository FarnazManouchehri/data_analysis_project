"""Run the whole Phase 1 audit: tables, figures and headline.json under artifacts/phase1.

    python -m taxidemand.run_all
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from . import checks, demand, explore
from .ingest import load_trips, load_zones
from .settings import TABLES, dump, params, prepare_dirs, theme


def gini(x: np.ndarray) -> float:
    x = np.sort(x.astype(float))
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))


def main() -> None:
    t0 = time.time()
    prm = params()
    np.random.seed(prm["seed"])
    prepare_dirs(); theme()
    H: dict = {}

    # 1. Load and audit structure
    trips = load_trips()
    zones = load_zones()
    H["raw_rows"], H["raw_cols"] = len(trips), 19
    H["rows_by_file"] = trips["file_month"].value_counts().sort_index().astype(int).to_dict()
    H["zones_in_lookup"] = int(len(zones))
    H["pu_zones_seen"] = int(trips["pu"].nunique())
    H["pu_ids_not_in_lookup"] = int((~trips["pu"].isin(zones["zone_id"])).sum())
    checks.schema_table(trips)
    print(f"loaded {len(trips):,} rows  [{time.time()-t0:.0f}s]")

    # 2. Quality rules
    trips = checks.add_flags(trips)
    rules = checks.rule_table(trips)
    H["reversals"] = checks.reversal_pairs(trips)
    H["total_mismatch_naive_pct"] = float(100 * (checks.total_residual(trips, vendor_aware=False).abs() > 0.05).mean())
    H["total_mismatch_vendor_aware_pct"] = float(100 * trips["q_total_mismatch"].mean())
    H["missing_block"] = checks.missingness_mechanism(trips)
    out = trips[trips["q_outside_window"]]
    H["outside_window_examples"] = out["pickup"].astype(str).sort_values().tolist()[:8] + ["..."] + \
        out["pickup"].astype(str).sort_values().tolist()[-3:]
    H["vendor6_rows"] = int((trips["vendor"] == 6).sum())
    explore.fig_rules(rules)
    explore.fig_missing(trips)
    clean = trips[~trips["q_any_drop"]].copy()
    H["clean_rows"] = len(clean)
    H["dropped_pct"] = float(100 * trips["q_any_drop"].mean())
    del trips
    print(f"clean {len(clean):,} rows  [{time.time()-t0:.0f}s]")

    # 3. Univariate / categorical
    checks.univariate(clean)
    H["categorical_shares"] = checks.categorical_shares(clean)
    explore.fig_distributions(clean)
    explore.fig_payment(clean)

    # 4. Time audit
    hourly_total = clean.groupby(clean["pickup"].dt.floor("h")).size()
    full = pd.date_range(prm["window"]["start"], prm["window"]["end"], freq="h", inclusive="left")
    hourly_total = hourly_total.reindex(full, fill_value=0)
    H["hours_in_window"] = len(full)
    H["hours_with_zero_trips"] = [str(x) for x in hourly_total[hourly_total == 0].index]
    H["dst_gap_hour_trips"] = int(hourly_total.get(pd.Timestamp("2024-03-10 02:00"), 0))
    H["lowest_hours"] = {str(k): int(v) for k, v in hourly_total.nsmallest(5).items()}
    by_hour = clean.groupby("hour").size()
    H["peak_hour"], H["trough_hour"] = int(by_hour.idxmax()), int(by_hour.idxmin())
    H["peak_trough_ratio"] = float(by_hour.max() / by_hour.min())
    by_dow = clean.groupby("dow").size() / clean["pickup"].dt.normalize().groupby(clean["dow"]).nunique()
    H["mean_daily_by_dow"] = {explore.DOW[int(k)]: float(v) for k, v in by_dow.items()}
    day = demand.daily_anomalies(clean)
    H["daily_mean"], H["daily_min"], H["daily_max"] = float(day["trips"].mean()), day["trips"].idxmin(), day["trips"].idxmax()
    H["anomaly_days"] = day[day["anomaly"]][["trips", "expected", "pct_dev", "robust_z", "holiday"]] \
        .round(1).reset_index().astype(str).to_dict("records")
    H["monthly_trips"] = clean.groupby(clean["pickup"].dt.strftime("%Y-%m")).size().astype(int).to_dict()
    explore.fig_daily(day)
    explore.fig_heat(clean)

    # 5. Consistency
    std = clean[(clean["trip_distance"] > 0) & (clean["ratecode"] == 1)]
    s = std.sample(1_000_000, random_state=prm["seed"])
    H["spearman"] = {
        "distance_fare": float(s[["trip_distance", "fare_amount"]].corr("spearman").iloc[0, 1]),
        "distance_duration": float(s[["trip_distance", "duration_min"]].corr("spearman").iloc[0, 1]),
        "duration_fare": float(s[["duration_min", "fare_amount"]].corr("spearman").iloc[0, 1]),
    }
    fpm = (s["fare_amount"] / s["trip_distance"])
    H["fare_per_mile_median"] = float(fpm.median())
    H["fare_below_meter_floor_pct"] = float(100 * (s["fare_amount"] < 3.0).mean())
    sp = clean.groupby("hour")["speed_mph"].median()
    H["median_speed_by_hour_min_max"] = [float(sp.min()), int(sp.idxmin()), float(sp.max()), int(sp.idxmax())]
    H["jfk_flat_fare_share"] = float(100 * (clean["ratecode"] == 2).mean())
    explore.fig_consistency(clean)

    # 6. Spatial
    zc = clean.groupby("pu").size().rename("pickups").reset_index().rename(columns={"pu": "zone_id"})
    zc = zc.merge(zones, on="zone_id", how="left")
    known = zc[~zc["zone_id"].isin(checks.UNKNOWN_ZONES)]
    tot = known["pickups"].sum()
    srt = known.sort_values("pickups", ascending=False)
    H["zones_with_pickups"] = int((known["pickups"] > 0).sum())
    H["top10_share"] = float(100 * srt["pickups"].head(10).sum() / tot)
    H["top_zones"] = srt.head(10)[["zone", "borough", "pickups"]].astype(str).to_dict("records")
    H["gini_zones"] = gini(np.r_[known["pickups"].to_numpy(), np.zeros(263 - len(known))])
    H["borough_share_pickup"] = (known.groupby("borough")["pickups"].sum() / tot * 100).round(2).to_dict()
    H["airport_share"] = float(100 * known.loc[known["zone_id"].isin([132, 138]), "pickups"].sum() / tot)
    H["zones_lt1_per_day"] = int(263 - (known["pickups"] / 182 >= 1).sum())
    zc.to_csv(TABLES / "zone_pickups.csv", index=False)
    bmap = zones.set_index("zone_id")["borough"]
    od = pd.crosstab(clean["pu"].map(bmap), clean["do"].map(bmap))
    order = ["Manhattan", "Queens", "Brooklyn", "Bronx", "Staten Island", "EWR", "Unknown", "N/A"]
    od = od.reindex(index=[o for o in order if o in od.index], columns=[o for o in order if o in od.columns], fill_value=0)
    od.to_csv(TABLES / "od_borough.csv")
    H["intra_manhattan_pct"] = float(100 * od.loc["Manhattan", "Manhattan"] / od.values.sum())
    explore.fig_zones(known)
    explore.fig_od(od)

    # 7. Demand panel, split, baselines, leakage
    panel = demand.build_panel(clean)
    act = demand.active_zones(panel)
    H["active_zones"] = int(len(act))
    tr_mask = demand.split_of(panel["ts"]) == "train"
    H["active_zone_pickup_share"] = float(100 * panel.loc[panel["zone_id"].isin(act) & tr_mask, "pickups"].sum()
                                          / panel.loc[tr_mask, "pickups"].sum())
    H["panel_rows"] = len(panel)
    p = demand.add_lags(panel)
    pa = p[p["zone_id"].isin(act)]
    H["active_zero_hours_pct"] = float(100 * (pa["pickups"] == 0).mean())
    H["active_hourly_mean_median_max"] = [float(pa["pickups"].mean()), float(pa["pickups"].median()), int(pa["pickups"].max())]
    H["split"] = demand.split_summary(pa, act).astype(str).to_dict("records")
    base = demand.baselines(pa)
    H["baselines"] = base.round(3).to_dict("records")
    leak = demand.leakage_designs(pa, prm["seed"])
    H["leakage"] = leak.round(3).to_dict("records")
    explore.fig_flow(H["raw_rows"], H["clean_rows"], H["panel_rows"], H["active_zones"])
    explore.fig_series(p, zones, hourly_total)
    explore.fig_split(day, base, prm["split"])
    explore.fig_leak(leak)

    dump(H, "headline.json")
    print(f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
