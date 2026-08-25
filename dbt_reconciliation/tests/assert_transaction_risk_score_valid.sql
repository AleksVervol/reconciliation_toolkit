SELECT *
FROM {{ ref('mart_transaction_risk_dashboard') }}

WHERE risk_score !=
      (flag_risky_type::INT * 2 + flag_large_amount::INT)