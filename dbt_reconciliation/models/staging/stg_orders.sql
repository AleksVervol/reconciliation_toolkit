SELECT
    order_id,
    customer,
    amount,
    order_date
FROM {{ source('raw', 'orders') }}