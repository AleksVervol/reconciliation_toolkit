SELECT
    o.order_id,
    o.customer,
    o.amount AS order_amount,
    o.order_date,
    d.delivered_amount,
    d.delivery_date
FROM {{ ref('stg_orders') }} o
LEFT JOIN {{ ref('stg_deliveries') }} d ON o.order_id = d.order_id