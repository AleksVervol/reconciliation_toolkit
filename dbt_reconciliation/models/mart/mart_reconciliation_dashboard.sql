SELECT
    order_id,
    customer,
    order_date,
    order_amount,

    delivered_amount,
    delivery_date,
    delivery_count,

    flag_missing_delivery,
    flag_duplicate_delivery,
    flag_amount_discrepancy,

    amount_difference,
    absolute_difference,

    has_exception,
    exception_type,

    CASE
        WHEN flag_amount_discrepancy = 1
        THEN absolute_difference
        ELSE 0
    END AS discrepancy_amount,

    CASE
        WHEN flag_missing_delivery = 1
        THEN order_amount
        ELSE 0
    END AS affected_order_value

FROM {{ ref('prep_orders_deliveries_merged') }}