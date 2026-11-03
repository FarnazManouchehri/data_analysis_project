"""Zone x hour demand panel, temporal split, simple baselines and a leakage demonstration."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split

from .checks import UNKNOWN_ZONES
from .settings import STAGED, TABLES, params

HOLIDAYS = {
    "2024-01-01": "New Year's Day", "2024-01-15": "MLK Day", "2024-02-19": "Presidents' Day",
    "2024-03-31": "Easter Sunday", "2024-05-27": "Memorial Day", "2024-06-19": "Juneteenth",
}


def build_panel(clean: pd.DataFrame) -> pd.DataFrame:
    """Complete zone x hour grid of pickups (zeros included), written to tlc/derived."""
    w = params()["window"]
    t = clean.loc[~clean["pu"].isin(UNKNOWN_ZONES), ["pickup", "pu"]]
    hour = t["pickup"].dt.floor("h")
    counts = t.groupby([t["pu"].rename("zone_id"), hour.rename("ts")]).size().rename("pickups")
    hours = pd.date_range(w["start"], w["end"], freq="h", inclusive="left")
    zones = np.arange(1, 264, dtype="int16")
    grid = pd.MultiIndex.from_product([zones, hours], names=["zone_id", "ts"])
    panel = counts.reindex(grid, fill_value=0).astype("int32").reset_index()
    panel.to_parquet(STAGED / "zone_hour_panel.parquet", index=False)
    return panel


def split_of(ts: pd.Series) -> pd.Series:
    s = params()["split"]
    lab = np.where(ts < pd.Timestamp(s["train_end"]), "train",
                   np.where(ts < pd.Timestamp(s["valid_end"]), "valid", "test"))
    return pd.Series(lab, index=ts.index)


def active_zones(panel: pd.DataFrame) -> pd.Index:
    f = params()["forecast"]
    tr = panel[split_of(panel["ts"]) == "train"]
    daily = tr.groupby("zone_id")["pickups"].sum() / tr["ts"].dt.normalize().nunique()
    return daily[daily >= f["active_zone_min_daily"]].index


def add_lags(panel: pd.DataFrame) -> pd.DataFrame:
    p = panel.sort_values(["zone_id", "ts"]).copy()
    g = p.groupby("zone_id")["pickups"]
    for lag in (1, 24, 168):
        p[f"lag_{lag}"] = g.shift(lag)
    p["lead_1"] = g.shift(-1)  # only used to show what an interpolating (leaky) model can do
    p["hour"] = p["ts"].dt.hour
    p["dow"] = p["ts"].dt.dayofweek
    p["split"] = split_of(p["ts"]).values
    return p


def metrics(y: np.ndarray, yhat: np.ndarray) -> dict:
    err = yhat - y
    return {"MAE": float(np.mean(np.abs(err))), "RMSE": float(np.sqrt(np.mean(err ** 2))),
            "WAPE_pct": float(100 * np.abs(err).sum() / y.sum()), "bias": float(err.mean())}


def baselines(p: pd.DataFrame) -> pd.DataFrame:
    """Score day-ahead baselines on the validation month only."""
    tr, va = p[p["split"] == "train"], p[p["split"] == "valid"].copy()
    zone_mean = tr.groupby("zone_id")["pickups"].mean()
    profile = tr.groupby(["zone_id", "dow", "hour"])["pickups"].mean().rename("profile")
    va = va.join(profile, on=["zone_id", "dow", "hour"])
    preds = {
        "Zone mean (train)": va["zone_id"].map(zone_mean).to_numpy(),
        "Same hour yesterday (lag 24)": va["lag_24"].to_numpy(),
        "Same hour last week (lag 168)": va["lag_168"].to_numpy(),
        "Zone x weekday x hour profile (train)": va["profile"].to_numpy(),
    }
    y = va["pickups"].to_numpy()
    rows = [{"baseline": k, **metrics(y, v)} for k, v in preds.items()]
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "baselines_valid.csv", index=False)
    return out


def leakage_designs(p: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Same model, three evaluation designs. Only the last is honest for a day-ahead forecast."""
    d = p[p["split"].isin(["train", "valid"])].dropna(subset=["lag_1", "lag_24", "lag_168", "lead_1"])
    model = lambda: HistGradientBoostingRegressor(max_iter=200, learning_rate=0.1, random_state=seed)  # noqa: E731
    rows = []

    def run(name, feats, tr, te):
        m = model().fit(tr[feats], tr["pickups"])
        rows.append({"design": name, "features": ", ".join(feats),
                     **metrics(te["pickups"].to_numpy(), np.clip(m.predict(te[feats]), 0, None))})

    base = ["zone_id", "hour", "dow"]
    tr_r, te_r = train_test_split(d, test_size=0.2, random_state=seed)
    run("A. Random row split, neighbours t-1 and t+1", base + ["lag_1", "lead_1"], tr_r, te_r)
    run("B. Random row split, day-ahead lags", base + ["lag_24", "lag_168"], tr_r, te_r)
    tr_t, te_t = d[d["split"] == "train"], d[d["split"] == "valid"]
    run("C. Temporal split (train Jan-Apr, valid May), day-ahead lags", base + ["lag_24", "lag_168"], tr_t, te_t)
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "leakage_designs.csv", index=False)
    return out


def daily_anomalies(clean: pd.DataFrame) -> pd.DataFrame:
    """Robust z-score of each day's trips against the median of the same weekday (+-3 weeks)."""
    day = clean["pickup"].dt.normalize().value_counts().sort_index().rename("trips").to_frame()
    day["dow"] = day.index.dayofweek
    ref, mad = [], []
    for ts, row in day.iterrows():
        same = day[(day["dow"] == row["dow"]) & (abs((day.index - ts).days) <= 21) & (day.index != ts)]["trips"]
        med = same.median()
        ref.append(med)
        mad.append(1.4826 * np.median(np.abs(same - med)))
    day["expected"] = ref
    day["robust_z"] = (day["trips"] - day["expected"]) / np.maximum(mad, 1)
    day["pct_dev"] = 100 * (day["trips"] / day["expected"] - 1)
    day["holiday"] = [HOLIDAYS.get(str(d.date()), "") for d in day.index]
    # A day is a candidate anomaly only if it is both unusual (robust z) and material (>= 10% off).
    day["anomaly"] = (day["robust_z"].abs() > 3.5) & (day["pct_dev"].abs() >= 10)
    day.to_csv(TABLES / "daily_anomalies.csv", index_label="date")
    return day


def split_summary(p: pd.DataFrame, zones: pd.Index) -> pd.DataFrame:
    rows = []
    for s in ("train", "valid", "test"):
        q = p[p["split"] == s]
        rows.append({"split": s, "start": q["ts"].min(), "end": q["ts"].max(), "hours": q["ts"].nunique(),
                     "pickups": int(q["pickups"].sum()),
                     "mean_hourly_per_active_zone": float(q.loc[q["zone_id"].isin(zones), "pickups"].mean())})
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "split_summary.csv", index=False)
    return out
