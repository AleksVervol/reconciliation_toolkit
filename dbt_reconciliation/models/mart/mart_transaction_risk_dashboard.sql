SELECT
    step,
    type,
    amount,
    sender_id,
    sender_balance_before,
    sender_balance_after,
    receiver_id,

    flag_large_amount,
    flag_risky_type,
    flag_balance_mismatch,

    risk_score,

    CASE
        WHEN risk_score = 3 THEN 'High Priority'
        WHEN risk_score = 2 THEN 'Review'
        WHEN risk_score = 1 THEN 'Large Amount'
        ELSE 'No Risk Signals'
    END AS review_priority

FROM {{ ref('mart_transaction_risk_scores') }}