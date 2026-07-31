## Hypothesis
A discrepancy between the sender's expected and actual balance after a transaction
is a potential indicator of fraud.

## Method
Based on the dbt mart model `mart_balance_discrepancies`: comparing the sender's
balance before/after each transaction against the expected value (balance before
minus transaction amount), on a 50,000-transaction sample from PaySim.

## Finding (updated)
An initial 4-signal anomaly score (balance mismatch, large amount, risky 
transaction type, system-flagged) was tested against the ground-truth 
`isFraud` label. Per-signal validation revealed that balance mismatch — 
intuitively the strongest signal — actually *inversely* correlated with 
fraud (0.013% fraud rate when mismatched vs. 0.872% when balances matched). 
This is a known PaySim artifact: destination balances for CASH_OUT 
transactions (typically merchants) are often recorded as zero regardless 
of fraud status, making balance mismatch a data quality artifact rather 
than a fraud signal.

After removing this signal, a 2-signal score (large transaction amount + 
risky transaction type) produced a fraud rate that increases with score: 
0% at score 0, 0.53% at score 1, 0.63% at score 2 — on a 50,000-row sample. 
The separation between score 1 and 2 is modest at this sample size and 
would likely sharpen on the full 6M-row dataset.

## Recommendation
Not every intuitive rule is a good signal — each one needs to be validated 
against ground truth before being combined into a composite score. In this 
case, a naive balance-mismatch rule would have actively hurt detection 
accuracy rather than helped it.