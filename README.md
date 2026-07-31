# Universal Reconciliation & Anomaly Detection Toolkit

A reusable method for comparing two data sources and surfacing where they
disagree — built with DuckDB and dbt. The same pipeline is applied to two
different domains to demonstrate that the underlying logic generalizes:
order/delivery reconciliation (e-commerce/logistics) and transaction
balance anomalies (fintech/fraud).

## Why this exists

Reconciliation — checking whether two systems agree — is a recurring problem
across industries: orders vs. deliveries, transactions vs. confirmations,
payroll vs. attendance. This project builds one general-purpose pipeline for
that problem, then applies it to two concrete cases to show it holds up
beyond a single domain.

## Architecture

Raw data → dbt staging (cleaned/typed) → prep (merged) → mart
(business-ready reconciliation tables), all running on DuckDB, with
built-in data quality tests (uniqueness, not-null, referential integrity).

![Lineage graph](docs/lineage_graph.png)

## Case studies

- [`case_studies/ecommerce_case.md`](case_studies/ecommerce_case.md) —
  synthetic orders vs. deliveries (Faker-generated)
- [`case_studies/fintech_case.md`](case_studies/fintech_case.md) —
  transaction balance discrepancies (PaySim / Kaggle sample)

## Key finding (fintech case)

Out of 39,105 transactions with a balance discrepancy, only 5 were confirmed
fraud — showing that balance mismatch alone is a weak fraud signal and
needs further segmentation. Full write-up in the case study.

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

\```bash
pip install duckdb faker pandas dbt-core dbt-duckdb

cd python
python generate_data.py   # generates orders.csv, deliveries.csv
python setup_db.py        # loads raw tables into reconciliation.duckdb

cd ../dbt_reconciliation
dbt run                   # builds staging/prep/mart models
dbt test                  # runs data quality tests
dbt docs generate && dbt docs serve   # view lineage graph + docs
\```

Note: `transactions_sample.csv` (PaySim data) is included directly since
it's already a sampled subset; the full PaySim dataset is available on
[Kaggle](https://www.kaggle.com/datasets/ealaxi/paysim1) if needed.