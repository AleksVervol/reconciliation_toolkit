## Objective

Build a simple rule-based framework for prioritizing transactions for
operational review and validate whether the selected risk signals are
supported by observed fraud patterns.

The analysis uses a 50,000-transaction sample from the PaySim synthetic
financial transaction dataset.

## Method

Candidate transaction characteristics were explored against the
ground-truth `isFraud` label before being included in the final risk score.

Two signals were selected for operational prioritization:

- **Risky transaction type** — `CASH_OUT` or `TRANSFER`
- **Large transaction amount** — amount above the 95th percentile of the sample

Transaction type showed a stronger relationship with observed fraud than
large transaction size, so the signals were intentionally given different
weights:

- risky transaction type = **2 points**
- large transaction amount = **1 point**

This produces a rule-based risk score from 0 to 3.

## Signal Validation

Balance mismatch was also evaluated as a candidate signal by comparing the
sender's expected post-transaction balance with the recorded balance.

However, the signal showed an inverse relationship with the fraud label in
this sample and was therefore excluded from the final risk score.

This illustrates an important modelling principle: an intuitively plausible
rule should not be included in a composite score without first validating
its observed behaviour.

## Findings

The final weighted score produced the following distribution:

| Risk Score | Transactions | Fraud Cases | Fraud Rate |
|---|---:|---:|---:|
| 0 | 31,440 | 0 | 0.000% |
| 1 | 104 | 0 | 0.000% |
| 2 | 16,060 | 85 | 0.529% |
| 3 | 2,396 | 15 | 0.626% |

All observed fraud cases in the sample fall within scores 2 and 3.

The difference in fraud rate between scores 2 and 3 is modest, so the score
should not be interpreted as a predictive fraud model. Instead, it provides
a transparent rule-based mechanism for prioritizing transactions for
operational review.

## Operational Use

The risk score is translated into review priorities for the monitoring
dashboard:

- **0 — No Risk Signals**
- **1 — Large Amount**
- **2 — Review**
- **3 — High Priority**

This allows an operations or risk team to move from an overall transaction
population to a smaller review queue and investigate higher-priority
transactions first.

## Recommendation

Use the score as an operational prioritization layer rather than an automated
fraud decision.

The analysis demonstrates why candidate signals should be validated
individually before being combined: adding an intuitive but poorly behaving
signal can make a rule-based monitoring framework less meaningful rather
than more effective.