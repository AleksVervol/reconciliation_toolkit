SELECT *
FROM {{ ref('mart_reconciliation_dashboard') }}

WHERE
    flag_missing_delivery !=
        CASE
            WHEN delivery_count = 0 THEN 1
            ELSE 0
        END

    OR flag_duplicate_delivery !=
        CASE
            WHEN delivery_count > 1 THEN 1
            ELSE 0
        END

    OR flag_amount_discrepancy !=
        CASE
            WHEN delivered_amount IS NOT NULL
             AND absolute_difference > {{ var('reconciliation_tolerance') }}
            THEN 1
            ELSE 0
        END

    OR has_exception !=
        CASE
            WHEN flag_missing_delivery = 1
              OR flag_duplicate_delivery = 1
              OR flag_amount_discrepancy = 1
            THEN 1
            ELSE 0
        END