WITH delivery_summary AS (

    SELECT
        order_id,
        COUNT(*) AS delivery_count,
        MAX(delivered_amount) AS delivered_amount,
        MAX(delivery_date) AS delivery_date

    FROM {{ ref('stg_deliveries') }}

    GROUP BY order_id
),

joined AS (

    SELECT
        o.order_id,
        o.customer,
        o.amount AS order_amount,
        o.order_date,

        d.delivered_amount,
        d.delivery_date,
        COALESCE(d.delivery_count, 0) AS delivery_count

    FROM {{ ref('stg_orders') }} o

    LEFT JOIN delivery_summary d
        ON o.order_id = d.order_id
)

SELECT
    *,

    CASE
        WHEN delivery_count = 0 THEN 1
        ELSE 0
    END AS flag_missing_delivery,

    CASE
        WHEN delivery_count > 1 THEN 1
        ELSE 0
    END AS flag_duplicate_delivery,

    CASE
        WHEN delivered_amount IS NOT NULL
         AND ABS(order_amount - delivered_amount)
             > {{ var('reconciliation_tolerance') }}
        THEN 1
        ELSE 0
    END AS flag_amount_discrepancy,

    CASE
        WHEN delivered_amount IS NOT NULL
        THEN order_amount - delivered_amount
        ELSE NULL
    END AS amount_difference,

    CASE
        WHEN delivered_amount IS NOT NULL
        THEN ABS(order_amount - delivered_amount)
        ELSE NULL
    END AS absolute_difference,

    CASE
        WHEN delivery_count = 0
            THEN 'Missing Delivery'

        WHEN delivery_count > 1
            THEN 'Duplicate Delivery'

        WHEN delivered_amount IS NOT NULL
         AND ABS(order_amount - delivered_amount)
             > {{ var('reconciliation_tolerance') }}
            THEN 'Amount Discrepancy'

        ELSE 'Reconciled'
    END AS exception_type,

    CASE
        WHEN delivery_count = 0
          OR delivery_count > 1
          OR (
              delivered_amount IS NOT NULL
              AND ABS(order_amount - delivered_amount)
                  > {{ var('reconciliation_tolerance') }}
          )
        THEN 1
        ELSE 0
    END AS has_exception

FROM joined