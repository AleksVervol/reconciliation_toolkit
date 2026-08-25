SELECT
    order_id,
    customer,
    order_amount,
    order_date,
    delivery_count
FROM {{ ref('prep_orders_deliveries_merged') }}
WHERE flag_duplicate_delivery = 1