SELECT *
FROM {{ ref('prep_orders_deliveries_merged') }}
WHERE delivered_amount IS NULL