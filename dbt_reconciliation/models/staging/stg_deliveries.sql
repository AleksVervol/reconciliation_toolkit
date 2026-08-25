SELECT
    order_id,
    CAST(delivered_amount AS DECIMAL(18, 2)) AS delivered_amount,
    CAST(delivery_date AS DATE) AS delivery_date
FROM {{ source('raw', 'deliveries') }}