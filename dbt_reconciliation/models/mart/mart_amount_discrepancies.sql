SELECT
    order_id,
    order_amount,
    delivered_amount,
    amount_difference AS difference,
    absolute_difference
FROM {{ ref('prep_orders_deliveries_merged') }}
WHERE flag_amount_discrepancy = 1