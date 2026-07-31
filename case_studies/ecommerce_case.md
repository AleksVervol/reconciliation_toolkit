# Case Study: Order vs. Delivery Reconciliation

## Hypothesis
When two systems record the same business event independently (an order-management 
system and a delivery/fulfillment system), discrepancies naturally creep in — missing 
records, mismatched amounts, and duplicate entries. A general-purpose reconciliation 
pipeline should be able to surface all three without domain-specific logic.

## Method
A synthetic dataset of 1,000 orders was generated (Faker), with delivery records 
intentionally introduced with three types of discrepancies: missing deliveries, 
amount mismatches, and duplicate delivery entries. The data was loaded into DuckDB 
and processed through a dbt pipeline (staging → prep → mart), with three dedicated 
mart models isolating each discrepancy type.

## Findings

**Missing deliveries** (`mart_missing_deliveries`): 44 orders have no matching 
delivery record at all — roughly 4.4% of all orders. These represent orders that 
may be lost, delayed beyond the tracking window, or never fulfilled.

**Amount discrepancies** (`mart_amount_discrepancies`): 57 orders were delivered, 
but the delivered amount doesn't match the order amount — about 5.7% of orders. 
This could indicate partial refunds, data entry errors, or fulfillment issues.

**Duplicate deliveries** (`mart_duplicate_deliveries`): 36 order IDs appear more 
than once in the delivery records — about 3.6% of orders. Left unresolved, these 
would inflate delivery counts and distort any downstream reporting (e.g. revenue 
recognition, fulfillment KPIs).

Combined, roughly 13-14% of orders in this dataset show some form of discrepancy 
between the two systems — a reminder that reconciliation isn't a one-off check but 
an ongoing data quality concern.

## Recommendation
Each discrepancy type needs a different operational response, not a single blanket 
fix:
- **Missing deliveries** should trigger an investigation workflow (has the order 
  actually shipped, or is it stuck?).
- **Amount discrepancies** should be reviewed against refund/adjustment logs before 
  being treated as errors — some may be legitimate.
- **Duplicate deliveries** should be deduplicated at the reporting layer, with the 
  root cause (e.g. retry logic firing twice) addressed upstream.

This same three-part pattern — missing, mismatched, duplicated — generalizes well 
beyond orders/deliveries; the same mart-model structure was reused for the fintech 
case study with transaction data.