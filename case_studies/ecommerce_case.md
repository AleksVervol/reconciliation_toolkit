# Case Study: Order-to-Delivery Reconciliation

## Objective

Build a reproducible reconciliation pipeline that compares records from
two systems and identifies common operational exceptions: missing records,
amount discrepancies, and duplicate entries.

## Method

A synthetic dataset of 1,000 orders was generated with Faker, with three
types of reconciliation exceptions intentionally introduced:

- missing delivery records;
- mismatched order and delivered amounts;
- duplicate delivery records.

The data is loaded into DuckDB and transformed through a dbt pipeline:

`raw → staging → reconciliation prep → marts`

The reconciliation logic is centralized at order level, where each order
is assigned exception flags and an overall reconciliation status.
Dedicated marts expose each exception type for analysis, while a final
dashboard mart provides one row per order for operational monitoring.

A configurable tolerance of 0.01 is applied when identifying material
amount discrepancies.

## Findings

The final reconciliation mart contains 1,000 unique orders and identifies
137 orders with at least one exception (13.7%).

| Exception Type | Orders | Share of Orders |
|---|---:|---:|
| Missing Delivery | 44 | 4.4% |
| Amount Discrepancy | 57 | 5.7% |
| Duplicate Delivery | 36 | 3.6% |
| **Total Exceptions** | **137** | **13.7%** |

In the generated dataset, the three exception categories are mutually
exclusive.

### Financial relevance

The 57 amount discrepancies represent a total absolute discrepancy volume
of **3,106.54**.

The 44 orders without a matching delivery record represent **10,075.78**
in affected order value.

Affected order value should not be interpreted as confirmed financial loss.
It represents transaction value requiring investigation.

## Operational Use

Each exception type supports a different review workflow:

- **Missing Delivery** — investigate why no corresponding delivery record
  exists.
- **Amount Discrepancy** — review the difference between order and delivered
  values and determine whether an adjustment is expected.
- **Duplicate Delivery** — investigate multiple delivery records associated
  with the same order before using the data for downstream reporting.

The Tableau dashboard provides an operational control layer where users can
monitor overall reconciliation status, filter exception categories, and
prioritize individual records for investigation.

## Recommendation

Reconciliation rules should be defined once and reused consistently across
downstream outputs.

In this project, exception logic is centralized in the dbt preparation
layer, while dedicated marts and the Tableau dashboard consume the same
validated definitions. This avoids different reports applying different
rules to the same reconciliation problem.