SELECT
    order_id,
    customer,
    order_amount,
    order_date
FROM {{ ref('prep_orders_deliveries_merged') }}
WHERE flag_missing_delivery = 1