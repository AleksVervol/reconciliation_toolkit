# v2 scope: Multi-Currency Payment Reconciliation & Settlement Control

Working document. Not the README. Assumptions marked **[confirm]** are my
reading of how the flow works and should be corrected against real practice.

## The flow being modelled

1. A customer pays in a local currency (INR or MYR) through a PSP.
2. The PSP confirms the payment **in local currency**. It does not convert.
3. The platform converts at **its own rate** and credits the customer in USD.
4. The PSP groups confirmed payments into settlement batches. The settlement
   report shows batch totals, fees, reserve, and the **PSP's own FX rate**
   (this is the only place the PSP shows a rate).
5. The net amount arrives in USD on the bank statement.

## Core principle

A payment can reconcile by transaction ID and still be financially wrong if
the customer was credited using an incorrect FX rate.
For this project, T+1 and T+2 mean business days. Public holidays are out
of scope and documented as a limitation.

## In scope

- customer deposits in INR and MYR;
- customer balances and settlement reporting in USD;
- Level 1: transaction reconciliation, platform ledger <-> PSP report;
- Level 2: FX credit validation against an approved daily platform rate;
- Level 3: batch reconciliation, PSP settlement report <-> bank statement;
- FX variance: platform credit rate vs PSP settlement rate (monitored as a
  metric, not an exception, see below);
- PSP fees, reserves, timing windows, exception prioritisation.

## Out of scope

- real PSP, bank, or employer data (all data is synthetic);
- refunds, reserve release and chargeback lifecycles;
- manual ledger adjustments (every PSP deposit has a provider transaction ID);
- payouts to customers, crypto conversion, treasury hedging;
- a predictive model: controls are explicit rules with stated tolerances.

## Two rates, two different jobs

| Rate | Where it comes from | Used for |
|---|---|---|
| Platform rate | Platform ledger, applied per transaction | What the customer was credited with |
| Approved platform rate | Daily file: market rate with the spread the policy allows already applied | Level 2: was the platform rate within policy? |
| PSP settlement rate | PSP settlement report, per batch | Level 3 expected USD and the FX variance metric |

The platform rate and the PSP settlement rate are expected to differ.
That difference is the **customer-credit vs settlement FX variance**. It can
reflect an intended margin, market movement between the two moments, or an
error, so it is a prompt to investigate, not a verdict. It is tracked per
batch and per day, and alerted only above a threshold. **[confirm]**

## Three controls and one metric

| Level | Compares | Typical breaks |
|---|---|---|
| 1. Payment confirmation | ledger <-> PSP transactions | missing on one side, duplicate ID, amount or status mismatch |
| 1. Ledger posting overdue | PSP status is success, ledger status is pending, older than window | window T+1 |
| 2. FX credit validation | local amount and platform rate <-> credited USD, platform rate <-> approved rate | wrong, inverted or 100x rate, wrong crediting formula, missing approved rate |
| 3. Settlement | PSP batch net <-> bank payout | batch not received, fee or reserve wrong, payout does not match report |
| FX variance (metric) | credited USD <-> USD at PSP settlement rate | systematic gap between the two rates |

## What must NOT be flagged (deliberate noise)

The controls are judged on what they leave alone as much as what they catch:

- confirmation lag inside the timing window (pending, not an exception);
- rounding differences up to 0.01 USD per transaction;
- platform rate within the tolerance band of the reference rate;
- batch totals that differ only by rounding.

## Data generation rules

- Each dataset is one reconciliation run at a fixed `as_of_timestamp`
  (a constant in the generator). All timing checks are evaluated relative to
  it, so results are reproducible.
- Anomalies are **clustered**, as in reality: a bad rate stays wrong for a
  window and hits many rows, rather than random single rows.
- Anomaly rates are not round numbers and differ by currency and period.
- Ground truth lives in a separate `_truth` file that dbt models never read.
  It is used only to report precision, recall, and false positives.

## Delivery stages

1. Generator, schemas, and Level 1 + Level 2 (the $1 -> $100 case).
2. Level 3, FX variance, exception queue.
3. Tableau dashboard and README.
