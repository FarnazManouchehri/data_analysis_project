PY ?= python

all: data audit report

data:
	$(PY) -m taxidemand.fetch

audit:
	$(PY) -m taxidemand.run_all

report:
	$(PY) tools/render_pdf.py writeup/phase1_fa.md reports/phase1.pdf

.PHONY: all data audit report
