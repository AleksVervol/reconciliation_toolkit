SELECT *
FROM {{ ref('mart_reconciliation_dashboard') }}

WHERE exception_type !=
    CASE
        WHEN flag_missing_delivery = 1
            THEN 'Missing Delivery'

        WHEN flag_duplicate_delivery = 1
            THEN 'Duplicate Delivery'

        WHEN flag_amount_discrepancy = 1
            THEN 'Amount Discrepancy'

        ELSE 'Reconciled'
    END