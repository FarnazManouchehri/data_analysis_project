"""Structure and quality audit of the raw trips.

Every rule produces a boolean flag column on the trips frame (prefix `q_`), and one row in
`tables/quality_rules.csv` giving its count, share and the Phase 1 decision.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .settings import TABLES, params

UNKNOWN_ZONES = (264, 265)  # "Unknown" / "Outside of NYC" in the lookup

# Rule id -> (description, decision). Kept next to the flag code so they cannot drift apart.
RULES = {
    "q_outside_window": ("Pickup outside 2024-01-01 .. 2024-06-30 (clock or file error)", "drop"),
    "q_wrong_file": ("Pickup month differs from the monthly file it was published in", "keep if inside window"),
    "q_exact_dup": ("Exact duplicate of another row on all raw columns", "drop the copy"),
    "q_reversal": ("Negative fare/total: refund or void record", "drop the negative row; keep its positive twin as a trip"),
    "q_no_meta": ("passenger_count, RatecodeID, store_and_fwd, congestion and airport fee all missing (payment_type 0)", "keep for demand; exclude from fare models"),
    "q_dur_nonpos": ("Dropoff at or before pickup", "drop"),
    "q_dur_short": ("Duration under 1 minute with distance > 0", "flag; keep for demand"),
    "q_dur_long": ("Duration over 5 hours (meter left running)", "drop"),
    "q_dist_zero": ("trip_distance = 0", "keep for demand; exclude from speed/fare analysis"),
    "q_dist_huge": ("trip_distance > 200 miles", "drop"),
    "q_speed": ("Implied speed > 80 mph", "drop"),
    "q_fare_huge": ("fare_amount > $1,000", "drop"),
    "q_pass_zero": ("passenger_count = 0", "keep; treat as unknown"),
    "q_pass_many": ("passenger_count > 6", "keep; treat as unknown"),
    "q_ratecode_99": ("RatecodeID = 99 (not in data dictionary)", "treat as missing"),
    "q_zone_unknown": ("Pickup zone 264/265 (unknown / outside NYC)", "exclude from zone panel"),
    "q_total_mismatch": ("total_amount differs from its components by > $0.05 (after vendor conventions)", "flag only"),
}


def add_flags(t: pd.DataFrame) -> pd.DataFrame:
    p = params()
    r, w = p["rules"], p["window"]
    t["q_outside_window"] = (t["pickup"] < pd.Timestamp(w["start"])) | (t["pickup"] >= pd.Timestamp(w["end"]))
    t["q_wrong_file"] = t["pickup"].dt.strftime("%Y-%m").values != t["file_month"].astype(str).values
    raw_cols = ["vendor", "pickup", "dropoff", "passengers", "ratecode", "pu", "do", "payment",
                "trip_distance", "fare_amount", "tip_amount", "tolls_amount", "total_amount"]
    t["q_exact_dup"] = t.duplicated(subset=raw_cols)
    t["q_reversal"] = (t["fare_amount"] < 0) | (t["total_amount"] < 0)
    t["q_no_meta"] = t["passengers"].isna()
    t["q_dur_nonpos"] = t["duration_min"] <= 0
    t["q_dur_short"] = (t["duration_min"] > 0) & (t["duration_min"] < r["min_duration_min"]) & (t["trip_distance"] > 0)
    t["q_dur_long"] = t["duration_min"] > r["max_duration_min"]
    t["q_dist_zero"] = t["trip_distance"] == 0
    t["q_dist_huge"] = t["trip_distance"] > r["max_distance_mi"]
    t["q_speed"] = (t["speed_mph"] > r["max_speed_mph"]) & ~t["q_dur_nonpos"]
    t["q_fare_huge"] = t["fare_amount"] > r["max_fare_usd"]
    t["q_pass_zero"] = t["passengers"].eq(0).fillna(False).astype(bool)
    t["q_pass_many"] = t["passengers"].gt(r["max_passengers"]).fillna(False).astype(bool)
    t["q_ratecode_99"] = t["ratecode"].eq(99).fillna(False).astype(bool)
    t["q_zone_unknown"] = t["pu"].isin(UNKNOWN_ZONES)
    t["q_total_mismatch"] = (total_residual(t, vendor_aware=True)).abs() > 0.05
    drop = ["q_outside_window", "q_exact_dup", "q_reversal", "q_dur_nonpos", "q_dur_long",
            "q_dist_huge", "q_speed", "q_fare_huge"]
    t["q_any_drop"] = t[drop].any(axis=1)
    return t


def total_residual(t: pd.DataFrame, vendor_aware: bool) -> pd.Series:
    """total_amount minus the sum of its components.

    Naively every component is added. With `vendor_aware`, two encodings found in the audit are
    respected: vendor 1 already folds the congestion and airport fees into `extra`, and rows of the
    missing-metadata block charge the $2.50 congestion fee without recording it.
    """
    base = t[["fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount", "improvement_surcharge"]].sum(axis=1)
    fees = t["congestion_surcharge"].fillna(0) + t["airport_fee"].fillna(0)
    if not vendor_aware:
        return t["total_amount"] - base - fees
    res = t["total_amount"] - base - np.where(t["vendor"] == 1, 0, fees)
    unrecorded = t["passengers"].isna().to_numpy() & np.isclose(res, 2.5, atol=0.05)
    return res.where(~unrecorded, 0)


def reversal_pairs(t: pd.DataFrame) -> dict:
    """How many negative records have a positive twin (same vendor, times, zones, |fare|)."""
    neg = t.loc[t["q_reversal"], ["vendor", "pickup", "dropoff", "pu", "do", "fare_amount"]].copy()
    neg["fare_amount"] = neg["fare_amount"].abs()
    key = ["vendor", "pickup", "dropoff", "pu", "do", "fare_amount"]
    pos = t.loc[~t["q_reversal"], key].drop_duplicates()
    m = neg.merge(pos, on=key, how="left", indicator=True)
    return {"negative_rows": int(len(neg)), "with_positive_twin": int((m["_merge"] == "both").sum())}


def rule_table(t: pd.DataFrame) -> pd.DataFrame:
    n = len(t)
    rows = [{"rule": k, "description": d, "rows": int(t[k].sum()), "pct": 100 * t[k].mean(), "decision": dec}
            for k, (d, dec) in RULES.items()]
    rows.append({"rule": "q_any_drop", "description": "Union of all 'drop' rules", "rows": int(t["q_any_drop"].sum()),
                 "pct": 100 * t["q_any_drop"].mean(), "decision": "removed from the clean frame"})
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "quality_rules.csv", index=False)
    assert out["rows"].max() <= n
    return out


def schema_table(t: pd.DataFrame) -> pd.DataFrame:
    raw = ["vendor", "pickup", "dropoff", "passengers", "ratecode", "store_fwd", "pu", "do", "payment",
           "trip_distance", "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
           "improvement_surcharge", "total_amount", "congestion_surcharge", "airport_fee"]
    rows = []
    for c in raw:
        s = t[c]
        rows.append({"column": c, "dtype": str(s.dtype), "missing_pct": 100 * s.isna().mean(),
                     "n_unique": int(s.nunique()),
                     "min": s.min() if s.dtype != "category" else "", "max": s.max() if s.dtype != "category" else ""})
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "schema.csv", index=False)
    return out


def missingness_mechanism(t: pd.DataFrame) -> dict:
    """Is the 'no metadata' block random? Compare its rate across vendors, hours and boroughs."""
    by_vendor = t.groupby("vendor", observed=True)["q_no_meta"].mean()
    by_hour = t.groupby("hour")["q_no_meta"].mean()
    tab = pd.crosstab(t["vendor"], t["q_no_meta"])
    chi2, pval, _, _ = stats.chi2_contingency(tab)
    by_month = t.groupby("file_month", observed=True)["q_no_meta"].mean()
    pd.DataFrame({"no_meta_rate": by_hour}).to_csv(TABLES / "missing_by_hour.csv")
    # Fare level of the missing block vs the rest (Mann-Whitney on a sample).
    rng = np.random.default_rng(params()["seed"])
    a = t.loc[t["q_no_meta"], "fare_amount"].to_numpy()
    b = t.loc[~t["q_no_meta"], "fare_amount"].to_numpy()
    a, b = rng.choice(a, 50_000, replace=False), rng.choice(b, 50_000, replace=False)
    mw = stats.mannwhitneyu(a, b)
    return {
        "no_meta_rows": int(t["q_no_meta"].sum()),
        "no_meta_pct": float(100 * t["q_no_meta"].mean()),
        "no_meta_payment_type_0_only": bool((t.loc[t["q_no_meta"], "payment"] == 0).all()),
        "rate_by_vendor": {int(k): float(v) for k, v in by_vendor.items()},
        "rate_by_month": {str(k): float(v) for k, v in by_month.items()},
        "hour_rate_min_max": [float(by_hour.min()), float(by_hour.max())],
        "chi2_vendor_p": float(pval),
        "median_fare_missing_vs_rest": [float(np.median(a)), float(np.median(b))],
        "mannwhitney_fare_p": float(mw.pvalue),
    }


def univariate(clean: pd.DataFrame) -> pd.DataFrame:
    cols = ["trip_distance", "duration_min", "speed_mph", "fare_amount", "tip_amount", "total_amount", "passengers"]
    rows = []
    for c in cols:
        s = clean[c].astype("float64").replace([np.inf, -np.inf], np.nan).dropna()
        rows.append({"variable": c, "n": len(s), "mean": s.mean(), "median": s.median(), "std": s.std(),
                     "iqr": s.quantile(.75) - s.quantile(.25), "p01": s.quantile(.01), "p99": s.quantile(.99),
                     "skew": stats.skew(s.sample(500_000, random_state=0))})
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "univariate.csv", index=False)
    return out


def categorical_shares(clean: pd.DataFrame) -> dict:
    res = {}
    for c in ("vendor", "payment", "ratecode"):
        vc = clean[c].value_counts(normalize=True, dropna=False)
        res[c] = {str(k): float(v) for k, v in vc.items()}
    return res
