# Universal Reconciliation & Anomaly Detection Toolkit

A reusable method for comparing two data sources and surfacing where they
disagree, plus a lightweight rule-based anomaly scoring layer validated
against ground-truth fraud labels — built with DuckDB and dbt. The same
pipeline is applied to two different domains: order/delivery reconciliation
(e-commerce/logistics) and transaction anomaly scoring (fintech/fraud).

## Why this exists

Reconciliation — checking whether two systems agree — is a recurring problem
across industries: orders vs. deliveries, transactions vs. confirmations,
payroll vs. attendance. This project builds one general-purpose reconciliation
pipeline for that problem, then goes a step further on the fintech side:
combining multiple weak signals into an anomaly score, and validating each
signal against real fraud labels rather than assuming it works.

## Architecture

Raw data → dbt staging (cleaned/typed) → prep (merged) → mart
(business-ready reconciliation + anomaly-scoring tables), all running on
DuckDB, with built-in data quality tests (uniqueness, not-null, referential
integrity).

![Lineage graph](docs/lineage_graph.png)

## Case studies

- [`case_studies/ecommerce_case.md`](case_studies/ecommerce_case.md) —
  synthetic orders vs. deliveries (Faker-generated): reconciliation only
- [`case_studies/fintech_case.md`](case_studies/fintech_case.md) —
  transaction anomaly scoring (PaySim / Kaggle sample), validated against
  the `isFraud` ground-truth label

## Key finding (fintech case)

An initial 4-signal anomaly score included balance mismatch as a fraud
indicator — the intuitive choice. Per-signal validation against ground truth
showed it actually *inversely* correlated with fraud, a known PaySim data
artifact rather than a real signal. After removing it, a 2-signal score
(large transaction amount + risky transaction type) produced a fraud rate
that increases monotonically with score. Full write-up, including why the
"obvious" signal failed, in the case study.

## Design decision: Python functions vs. dbt models

The reconciliation logic was first implemented as parameterized Python
functions (see `python/reconciliation.py`) operating directly on DuckDB via
f-string SQL. This was later migrated to a dbt project (staging → prep →
mart) because dbt provides built-in data quality tests, auto-generated
documentation, and a clearer separation between raw data, merged data, and
business-ready output — better suited to a project meant to demonstrate a
reusable, maintainable pipeline rather than a one-off script.

## Tech stack

- **DuckDB** — embedded analytical database
- **dbt-core** (dbt-duckdb adapter) — staging → prep → mart modeling,
  with data quality tests
- **Python** (pandas, Faker) — synthetic data generation

## Project structure

```
reconciliation-toolkit/
├── data/                     # input CSVs (generated + sampled)
├── python/                   # data generation scripts, notebook
├── dbt_reconciliation/       # dbt project (staging/prep/mart models, tests)
├── case_studies/             # hypothesis → finding → recommendation
├── docs/                     # lineage graph screenshot
└── reconciliation.duckdb     # database file
```

## How to run

```bash
pip install duckdb faker pandas dbt-core dbt-duckdb

cd python
python generate_data.py   # generates orders.csv, deliveries.csv
python setup_db.py        # loads raw tables into reconciliation.duckdb

cd ../dbt_reconciliation
dbt run                   # builds staging/prep/mart models
dbt test                  # runs data quality tests
dbt docs generate && dbt docs serve   # view lineage graph + docs
```

Note: `transactions_sample.csv` (PaySim data) is included directly since
it's already a sampled subset; the full PaySim dataset is available on
[Kaggle](https://www.kaggle.com/datasets/ealaxi/paysim1) if needed.