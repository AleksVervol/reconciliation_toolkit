SELECT 
    order_id,
    order_amount,
    delivered_amount,
    order_amount - delivered_amount AS difference
FROM {{ ref('prep_orders_deliveries_merged') }}
WHERE delivered_amount IS NOT NULL 
  AND order_amount != delivered_amount