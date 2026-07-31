SELECT
    sender_id,
    receiver_id,
    type,
    amount,
    sender_balance_before,
    sender_balance_after,
    sender_balance_before - amount AS expected_balance_after,
    sender_balance_after - (sender_balance_before - amount) AS balance_diff,
    is_fraud
FROM {{ ref('stg_transactions') }}
WHERE sender_balance_before - amount != sender_balance_after