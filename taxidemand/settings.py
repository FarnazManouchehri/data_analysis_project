"""Project paths, parameters and the shared plotting theme."""
from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HOME = Path(__file__).resolve().parents[1]
RAW = HOME / "tlc" / "downloads"
STAGED = HOME / "tlc" / "derived"
OUT = HOME / "artifacts" / "phase1"
FIGS = OUT / "figures"
TABLES = OUT / "tables"

# Palette used in every figure (teal / amber / plum / slate).
TEAL, AMBER, PLUM, SLATE, RED = "#0f766e", "#d97706", "#7c3aed", "#475569", "#b91c1c"
SEQ = "YlGnBu"


@dataclass(frozen=True)
class Params:
    raw: dict

    def __getitem__(self, key):
        return self.raw[key]


def params() -> Params:
    with open(HOME / "params.toml", "rb") as f:
        return Params(tomllib.load(f))


def prepare_dirs() -> None:
    for d in (RAW, STAGED, FIGS, TABLES):
        d.mkdir(parents=True, exist_ok=True)


def theme() -> None:
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 170, "savefig.bbox": "tight",
        "font.family": "DejaVu Sans", "font.size": 9,
        "axes.facecolor": "#f8fafc", "axes.edgecolor": "#cbd5e1", "axes.grid": True,
        "grid.color": "white", "grid.linewidth": 1.1,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.titleweight": "bold", "axes.titlesize": 10, "axes.titlelocation": "left",
        "axes.prop_cycle": plt.cycler(color=[TEAL, AMBER, PLUM, SLATE, RED]),
        "legend.frameon": False, "axes.axisbelow": True,
    })


def save_fig(fig, name: str) -> None:
    fig.savefig(FIGS / name)
    plt.close(fig)


def dump(obj, name: str) -> None:
    with open(OUT / name, "w") as f:
        json.dump(obj, f, indent=2, default=str)
