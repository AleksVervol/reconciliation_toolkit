SELECT 
    order_id, 
    COUNT(*) AS delivery_count
FROM {{ ref('stg_deliveries') }}
GROUP BY order_id
HAVING COUNT(*) > 1