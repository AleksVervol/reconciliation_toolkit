SELECT
    step,
    type,
    amount,
    nameOrig AS sender_id,
    oldbalanceOrg AS sender_balance_before,
    newbalanceOrig AS sender_balance_after,
    nameDest AS receiver_id,
    oldbalanceDest AS receiver_balance_before,
    newbalanceDest AS receiver_balance_after,
    isFraud AS is_fraud,
    isFlaggedFraud AS is_flagged_fraud
FROM {{ source('raw', 'transactions') }}