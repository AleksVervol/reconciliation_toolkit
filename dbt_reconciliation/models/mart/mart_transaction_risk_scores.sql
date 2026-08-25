WITH thresholds AS (
    SELECT 
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY amount) AS amount_p95
    FROM {{ ref('stg_transactions') }}
),

flagged AS (
    SELECT
        t.*,
    ABS((t.sender_balance_before - t.amount) - t.sender_balance_after) > 0.01 AS flag_balance_mismatch,
        t.amount > th.amount_p95 AS flag_large_amount,
        t.type IN ('CASH_OUT', 'TRANSFER') AS flag_risky_type,
        t.is_flagged_fraud = 1 AS flag_system_flagged
    FROM {{ ref('stg_transactions') }} t
    CROSS JOIN thresholds th
)
SELECT
    *,
    (flag_risky_type::INT * 2)
        + flag_large_amount::INT AS risk_score
FROM flagged