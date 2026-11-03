"""All Phase 1 figures. Each function takes already-computed frames and writes one PNG."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

from .settings import AMBER, PLUM, RED, SEQ, SLATE, TEAL, TABLES, save_fig

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def fig_flow(n_raw: int, n_clean: int, n_panel_rows: int, n_zones: int) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 2.6))
    ax.set_axis_off(); ax.set_xlim(0, 10); ax.set_ylim(0, 2.6)
    boxes = [
        (0.1, "TLC files\n6 monthly Parquet\n+ zone lookup CSV", SLATE),
        (2.1, f"ingest.py\n{n_raw/1e6:.2f}M trips\n19 raw columns", TEAL),
        (4.1, f"checks.py\n17 quality rules\n{n_clean/1e6:.2f}M clean trips", AMBER),
        (6.1, f"demand.py\nzone x hour grid\n{n_zones} active zones", PLUM),
        (8.1, "split + baselines\ntrain Jan-Apr\nvalid May | test Jun", RED),
    ]
    for x, text, c in boxes:
        ax.add_patch(FancyBboxPatch((x, 0.55), 1.75, 1.5, boxstyle="round,pad=0.04,rounding_size=0.12",
                                    fc=c, ec="none", alpha=0.92))
        ax.text(x + 0.875, 1.3, text, ha="center", va="center", color="white", fontsize=7.6, fontweight="bold")
    for x in (1.9, 3.9, 5.9, 7.9):
        ax.annotate("", xy=(x + 0.18, 1.3), xytext=(x - 0.02, 1.3),
                    arrowprops=dict(arrowstyle="-|>", color="#334155", lw=1.4))
    ax.text(5, 0.15, f"panel: {n_panel_rows:,} zone-hours (zeros included); join key PULocationID -> LocationID",
            ha="center", fontsize=8, color=SLATE)
    save_fig(fig, "p1_01_flow.png")


def fig_daily(day: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 3.2))
    ax.plot(day.index, day["trips"] / 1e3, color=TEAL, lw=1.2, label="trips per day")
    ax.plot(day.index, day["expected"] / 1e3, color=SLATE, lw=0.8, ls="--", label="same-weekday median (+-3 wk)")
    hol = day[day["holiday"] != ""]
    ax.scatter(hol.index, hol["trips"] / 1e3, s=36, color=AMBER, zorder=3, label="public holiday")
    an = day[day["anomaly"] & (day["holiday"] == "")]
    ax.scatter(an.index, an["trips"] / 1e3, s=40, facecolors="none", edgecolors=RED, lw=1.5, zorder=4,
               label="anomaly: |z| > 3.5 and >= 10% off (non-holiday)")
    for d, r in an.iterrows():
        ax.annotate(d.strftime("%d %b"), (d, r["trips"] / 1e3), xytext=(0, 7 if r["pct_dev"] > 0 else -12),
                    textcoords="offset points", fontsize=6.5, ha="center", color=RED)
    for d, r in hol.iterrows():
        ax.annotate(r["holiday"], (d, r["trips"] / 1e3), xytext=(0, -14), textcoords="offset points",
                    fontsize=6.5, ha="center", color=AMBER)
    ax.set_ylabel("thousand trips"); ax.set_title("Daily yellow-taxi trips, Jan-Jun 2024")
    ax.legend(ncol=4, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    save_fig(fig, "p1_02_daily.png")


def fig_heat(clean: pd.DataFrame) -> None:
    ndays = clean["pickup"].dt.normalize().groupby(clean["dow"]).nunique()
    m = clean.groupby(["dow", "hour"]).size().unstack() / ndays.values[:, None] / 1e3
    fig, ax = plt.subplots(figsize=(9.6, 2.9))
    im = ax.imshow(m.values, aspect="auto", cmap=SEQ)
    ax.set_yticks(range(7), DOW); ax.set_xticks(range(0, 24, 2), [f"{h:02d}" for h in range(0, 24, 2)])
    ax.grid(False); ax.set_xlabel("pickup hour"); ax.set_title("Mean pickups per hour (thousands) by weekday and hour")
    for (i, j), v in np.ndenumerate(m.values):
        ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=6, color="white" if v > m.values.max() * .55 else "#1e293b")
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    save_fig(fig, "p1_03_hour_weekday.png")


def fig_distributions(clean: pd.DataFrame) -> None:
    s = clean.sample(2_000_000, random_state=0)
    fig, axes = plt.subplots(1, 4, figsize=(9.6, 2.5))
    specs = [("trip_distance", "distance (mi)", np.logspace(-2, 2.3, 60)),
             ("duration_min", "duration (min)", np.logspace(-0.3, 2.5, 60)),
             ("fare_amount", "fare ($)", np.logspace(0, 3, 60)),
             ("speed_mph", "speed (mph)", np.linspace(0, 60, 61))]
    for ax, (c, lab, bins) in zip(axes, specs):
        v = s[c].replace([np.inf, -np.inf], np.nan).dropna()
        ax.hist(v, bins=bins, color=TEAL, alpha=.85)
        if c != "speed_mph":
            ax.set_xscale("log")
        med = v.median()
        ax.axvline(med, color=AMBER, lw=1.3)
        ax.set_title(lab, fontsize=8.5); ax.set_yticks([])
        ax.text(0.97, 0.92, f"median {med:.1f}", transform=ax.transAxes, ha="right", fontsize=7, color=AMBER)
    fig.suptitle("Distributions after cleaning (2M-row sample)", x=0.01, y=1.06, ha="left", fontsize=10, fontweight="bold")
    save_fig(fig, "p1_04_distributions.png")


def fig_consistency(clean: pd.DataFrame) -> None:
    s = clean[(clean["trip_distance"] > 0) & (clean["ratecode"] == 1)].sample(1_000_000, random_state=1)
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.0), layout="constrained")
    hb = axes[0].hexbin(s["trip_distance"], s["fare_amount"], gridsize=60, extent=(0, 25, 0, 120), bins="log", cmap=SEQ, mincnt=1)
    x = np.linspace(0, 25, 50)
    axes[0].plot(x, 3 + 3.5 * x, color=RED, lw=1, ls="--", label=r"\$3 + \$3.50/mi meter (no waiting time)")
    axes[0].set_xlabel("distance (mi)"); axes[0].set_ylabel("fare ($)"); axes[0].legend(fontsize=6.5, loc="upper left")
    axes[0].set_title("Fare vs distance (standard rate)", fontsize=9)
    axes[1].hexbin(s["trip_distance"], s["duration_min"], gridsize=60, extent=(0, 25, 0, 90), bins="log", cmap=SEQ, mincnt=1)
    axes[1].set_xlabel("distance (mi)"); axes[1].set_ylabel("duration (min)"); axes[1].set_title("Duration vs distance", fontsize=9)
    sp = s.groupby("hour")["speed_mph"].quantile([.25, .5, .75]).unstack()
    axes[2].fill_between(sp.index, sp[0.25], sp[0.75], color=TEAL, alpha=.25, label="IQR")
    axes[2].plot(sp.index, sp[0.5], color=TEAL, lw=1.6, label="median")
    axes[2].set_xlabel("pickup hour"); axes[2].set_ylabel("speed (mph)"); axes[2].set_title("Implied speed by hour", fontsize=9)
    axes[2].legend(fontsize=7)
    for ax in axes[:2]:
        ax.grid(False)
    fig.colorbar(hb, ax=axes[1], fraction=0.05, pad=0.02, label="trips (log)")
    save_fig(fig, "p1_05_consistency.png")


def fig_rules(rules: pd.DataFrame) -> None:
    r = rules[rules["rule"] != "q_any_drop"].sort_values("rows")
    colors = [RED if d.startswith("drop") else (SLATE if d.startswith(("treat", "exclude")) else AMBER) for d in r["decision"]]
    fig, ax = plt.subplots(figsize=(9.6, 3.8))
    ax.barh(r["rule"].str.replace("q_", ""), r["rows"].clip(lower=1), color=colors)
    ax.set_xscale("log")
    for i, (n, pct) in enumerate(zip(r["rows"], r["pct"])):
        ax.text(max(n, 1) * 1.15, i, f"{n:,}  ({pct:.3f}%)", va="center", fontsize=7)
    ax.set_xlim(1, r["rows"].max() * 30)
    ax.set_xlabel("rows flagged (log scale)")
    ax.set_title("Quality rules: rows flagged (red = dropped, amber = kept with flag, grey = recoded)")
    save_fig(fig, "p1_06_quality_rules.png")


def fig_missing(trips: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 2.7))
    bm = trips.groupby("file_month", observed=True)["q_no_meta"].mean() * 100
    axes[0].bar(bm.index.astype(str).str[5:], bm.values, color=TEAL); axes[0].set_title("Missing-metadata block by month (%)", fontsize=8.5)
    bh = trips.groupby("hour")["q_no_meta"].mean() * 100
    axes[1].plot(bh.index, bh.values, color=PLUM, marker="o", ms=3); axes[1].set_title("... by pickup hour (%)", fontsize=8.5)
    axes[1].set_xlabel("hour")
    s = trips.sample(1_000_000, random_state=2)
    bins = np.linspace(0, 80, 41)
    axes[2].hist(s.loc[~s["q_no_meta"], "fare_amount"], bins=bins, density=True, alpha=.6, color=SLATE, label="complete")
    axes[2].hist(s.loc[s["q_no_meta"], "fare_amount"], bins=bins, density=True, alpha=.6, color=AMBER, label="missing block")
    axes[2].set_title("Fare distribution ($)", fontsize=8.5); axes[2].legend(fontsize=7); axes[2].set_yticks([])
    save_fig(fig, "p1_07_missing_block.png")


def fig_zones(zone_counts: pd.DataFrame) -> None:
    z = zone_counts.sort_values("pickups", ascending=False)
    share = z["pickups"].cumsum() / z["pickups"].sum()
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4), gridspec_kw={"width_ratios": [1, 1.5]})
    axes[0].plot(np.arange(1, len(z) + 1), 100 * share.values, color=TEAL, lw=2)
    for k in (10, 25, 69):
        axes[0].axvline(k, color="#cbd5e1", lw=.8)
        axes[0].text(k + 3, 100 * share.iloc[k - 1] - 7, f"top {k}: {100*share.iloc[k-1]:.0f}%", fontsize=7)
    axes[0].set_xlabel("zones ranked by pickups"); axes[0].set_ylabel("cumulative % of pickups")
    axes[0].set_title("Concentration of pickups across 263 zones", fontsize=9)
    top = z.head(15).iloc[::-1]
    col = {"Manhattan": TEAL, "Queens": AMBER, "Brooklyn": PLUM, "Bronx": SLATE, "EWR": RED, "Staten Island": RED}
    axes[1].barh(top["zone"], top["pickups"] / 1e6, color=[col.get(b, SLATE) for b in top["borough"]])
    axes[1].set_xlabel("million pickups"); axes[1].set_title("Top 15 pickup zones (colour = borough; amber = Queens airports)", fontsize=9)
    axes[1].tick_params(axis="y", labelsize=7)
    save_fig(fig, "p1_08_zones.png")


def fig_od(od: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(5.6, 3.9))
    im = ax.imshow(np.log10(od.values + 1), cmap=SEQ)
    ax.set_xticks(range(len(od.columns)), od.columns, rotation=35, ha="right", fontsize=7)
    ax.set_yticks(range(len(od.index)), od.index, fontsize=7)
    tot = od.values.sum()
    for (i, j), v in np.ndenumerate(od.values):
        ax.text(j, i, f"{100*v/tot:.2f}" if v / tot < 0.1 else f"{100*v/tot:.1f}", ha="center", va="center", fontsize=6.3,
                color="white" if np.log10(v + 1) > 5.5 else "#1e293b")
    ax.grid(False); ax.set_xlabel("dropoff borough"); ax.set_ylabel("pickup borough")
    ax.set_title("Origin-destination by borough (% of trips)", fontsize=9)
    save_fig(fig, "p1_09_od_borough.png")


def fig_series(p: pd.DataFrame, zones: pd.DataFrame, total_hourly: pd.Series) -> None:
    pick = {132: "JFK Airport", 161: "Midtown Center", 237: "Upper East Side South", 79: "East Village"}
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.0), gridspec_kw={"width_ratios": [1.7, 1]})
    wk = p[(p["ts"] >= "2024-04-08") & (p["ts"] < "2024-04-15")]
    for (zid, name), c in zip(pick.items(), [AMBER, TEAL, PLUM, SLATE]):
        s = wk[wk["zone_id"] == zid]
        axes[0].plot(s["ts"], s["pickups"], lw=1.1, color=c, label=name)
    axes[0].set_title("Hourly pickups, one week (Mon 8 - Sun 14 Apr 2024)", fontsize=9)
    axes[0].legend(fontsize=7, ncol=2)
    days = pd.date_range("2024-04-08", periods=7)
    axes[0].set_xticks(days + pd.Timedelta(hours=12), [d.strftime("%a %d") for d in days], fontsize=7.5)
    x = total_hourly.to_numpy(float) - total_hourly.mean()
    acf = [1.0] + [np.corrcoef(x[:-k], x[k:])[0, 1] for k in range(1, 337)]
    axes[1].plot(range(337), acf, color=TEAL, lw=1)
    axes[1].axhline(0, color=SLATE, lw=.6)
    for k in (24, 168, 336):
        axes[1].axvline(k, color=AMBER, lw=.8, ls="--")
    axes[1].set_xlabel("lag (hours)"); axes[1].set_title("ACF of city-wide hourly pickups", fontsize=9)
    save_fig(fig, "p1_10_series_acf.png")


def fig_split(day: pd.DataFrame, base: pd.DataFrame, split_cfg: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 2.9), gridspec_kw={"width_ratios": [1.5, 1]})
    a = axes[0]
    a.plot(day.index, day["trips"] / 1e3, color=SLATE, lw=1)
    spans = [("2024-01-01", split_cfg["train_end"], TEAL, "train"), (split_cfg["train_end"], split_cfg["valid_end"], AMBER, "valid"),
             (split_cfg["valid_end"], split_cfg["test_end"], RED, "test (locked)")]
    for s, e, c, lab in spans:
        a.axvspan(pd.Timestamp(s), pd.Timestamp(e), color=c, alpha=.15)
        a.text(pd.Timestamp(s) + (pd.Timestamp(e) - pd.Timestamp(s)) / 2, a.get_ylim()[1] * .97, lab, ha="center",
               va="top", fontsize=8, color=c, fontweight="bold")
    a.set_ylabel("thousand trips / day"); a.set_title("Temporal split on pickup time", fontsize=9)
    b = base.sort_values("WAPE_pct", ascending=True)
    axes[1].barh(b["baseline"].str.replace(" (", "\n(", regex=False), b["WAPE_pct"], color=[TEAL] + [SLATE] * (len(b) - 1))
    for i, v in enumerate(b["WAPE_pct"]):
        axes[1].text(v + .5, i, f"{v:.1f}%", va="center", fontsize=7.5)
    axes[1].set_xlabel("WAPE on validation (May), %"); axes[1].tick_params(axis="y", labelsize=6.8)
    axes[1].set_title("Day-ahead baselines", fontsize=9); axes[1].set_xlim(0, b["WAPE_pct"].max() * 1.2)
    save_fig(fig, "p1_11_split_baselines.png")


def fig_leak(leak: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 2.2))
    lab = leak["design"].str.split(", ", n=1).str[0] + "\n" + leak["design"].str.split(", ", n=1).str[1]
    ax.barh(lab[::-1], leak["WAPE_pct"][::-1], color=[TEAL, AMBER, RED])
    for i, v in enumerate(leak["WAPE_pct"][::-1]):
        ax.text(v + .3, i, f"WAPE {v:.1f}%", va="center", fontsize=8)
    ax.set_xlim(0, leak["WAPE_pct"].max() * 1.25); ax.tick_params(axis="y", labelsize=7.5)
    ax.set_xlabel("WAPE, %  (same gradient-boosting model in all three rows)")
    ax.set_title("How the evaluation design changes the error (zone-hour pickups)")
    save_fig(fig, "p1_12_leakage.png")


def fig_payment(clean: pd.DataFrame) -> None:
    s = clean[(clean["fare_amount"] > 0)].sample(2_000_000, random_state=3)
    s = s.assign(tip_pct=100 * s["tip_amount"] / s["fare_amount"])
    names = {1: "credit card", 2: "cash", 3: "no charge", 4: "dispute", 0: "unknown (flex)"}
    g = s.groupby("payment").agg(share=("tip_pct", "size"), tipped=("tip_amount", lambda v: (v > 0).mean()),
                                 med_tip=("tip_pct", "median"))
    g["share"] = 100 * g["share"] / g["share"].sum()
    g.index = [names.get(i, str(i)) for i in g.index]
    g.to_csv(TABLES / "payment_tips.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 2.4))
    axes[0].bar(g.index, g["share"], color=TEAL); axes[0].set_title("Share of trips by payment type (%)", fontsize=9)
    axes[1].bar(g.index, 100 * g["tipped"], color=AMBER); axes[1].set_title("Trips with a recorded tip (%)", fontsize=9)
    for ax in axes:
        ax.tick_params(axis="x", labelsize=7.5)
    save_fig(fig, "p1_13_payment_tips.png")
