# AI usage log

The course allows AI tools if their use is transparent and the student can explain and defend every result.

## Phase 1
| Item | Details |
|---|---|
| Tool | Claude (Anthropic) via Claude Code, model Claude Opus 5.5 |
| What it did | Chose the subset (yellow taxi, H1 2024), wrote the `taxidemand/` code, ran it, inspected the figures, and drafted the Persian report, `PROJECT_CARD.md`, `README.md` and `tlc/SOURCES.md` from the pipeline outputs. |
| Where numbers come from | Every number in the report is copied from `artifacts/phase1/headline.json` or `artifacts/phase1/tables/*.csv`, which `python -m taxidemand.run_all` writes. |
| Corrections made during the work | (1) A naive "total ≠ sum of parts" rule flagged 29.1% of rows. The assistant traced this to vendor-specific fee encoding and made the rule vendor-aware (0.19% remain). (2) The first anomaly rule used only a robust z-score and flagged days only 5–7% off, so a minimum 10% deviation was added. |
| Used inside the analysis? | No. No LLM is used as a model, feature extractor or labeller. |
| Unverified statements | Explanations for anomalous days (snow on 13 Feb, Valentine's Day, unexplained early-April rise) are hypotheses; they have not been checked against external data such as weather. |

> **Student action required:** re-run the pipeline, check each design choice (subset, active-zone threshold, split dates, rules), and describe your own review here before submission.
