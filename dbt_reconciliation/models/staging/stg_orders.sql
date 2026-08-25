SELECT
    order_id,
    customer,
    CAST(amount AS DECIMAL(18, 2)) AS amount,
    CAST(order_date AS DATE) AS order_date
FROM {{ source('raw', 'orders') }}