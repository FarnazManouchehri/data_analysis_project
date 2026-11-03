# NYC yellow-taxi zone demand — Data Analysis course project (Track A)

Day-ahead forecasting of hourly pickups per taxi zone, from the NYC TLC Trip Record Data (yellow taxi, January–June 2024).

**Status:** Phase 1 done: problem framing, provenance, structure and quality audit, time/space EDA, leakage analysis, split and baselines.

## Phase 1 deliverables
| Path | What it is |
|---|---|
| `reports/phase1.pdf` | Phase 1 report (Persian), built from `writeup/phase1_fa.md` |
| `PROJECT_CARD.md` | The 14 required project-card items |
| `taxidemand/` | Python package: download, loading, audit, figures, zone-hour panel, baselines |
| `artifacts/phase1/` | Everything the package writes: `headline.json`, `tables/*.csv`, `figures/*.png` (13) |
| `tlc/SOURCES.md` | Data source, files, checksums, schema, known issues |
| `AI_USAGE.md` | AI usage log |

## Reproduce
Python 3.11+ (tested with 3.13.1), about 400 MB of disk and 8 GB of RAM.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
make all
```

`make all` runs three steps, which can also be run one at a time:

```bash
python -m taxidemand.fetch      # download 6 Parquet files + zone lookup into tlc/downloads, verify SHA-256
python -m taxidemand.run_all    # audit, tables, figures, panel, baselines -> artifacts/phase1 (~1.5 min)
python tools/render_pdf.py writeup/phase1_fa.md reports/phase1.pdf   # needs Google Chrome
```

All parameters (months, split dates, plausibility limits, seed = 7) are in `params.toml`. The June test month is never scored in Phase 1.

## Layout
```
params.toml              every fixed choice: months, URLs + SHA-256, split dates, rule limits, seed
pyproject.toml           package metadata and pinned dependencies
Makefile                 data -> audit -> report
taxidemand/
  settings.py            paths, params loader, plot theme
  fetch.py               download + checksum
  ingest.py              raw Parquet -> compact DataFrame (no filtering)
  checks.py              17 quality rules, schema, missingness tests, univariate stats
  demand.py              zone x hour panel, temporal split, baselines, leakage designs, daily anomalies
  explore.py             figures
  run_all.py             runs everything, writes headline.json
tlc/
  SOURCES.md             provenance and schema
  downloads/             raw TLC files (git-ignored)
  derived/               zone_hour_panel.parquet (git-ignored)
artifacts/phase1/        headline.json, tables/, figures/
writeup/phase1_fa.md     report source (Markdown, RTL)
tools/render_pdf.py      Markdown -> HTML -> PDF with headless Chrome
reports/phase1.pdf       the submitted report
```
