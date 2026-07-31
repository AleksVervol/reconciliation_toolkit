SELECT
    order_id,
    delivered_amount,
    delivery_date
FROM {{ source('raw', 'deliveries') }}