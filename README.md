# Multi-Currency Payment Reconciliation & Settlement Control

I built this project to model a payment-operations reconciliation flow: from a customer transaction to the platform ledger, the PSP balance, settlement, and the bank statement.

The data is synthetic, but the control logic is based on payment operations questions: did the customer receive the right balance update, did the PSP confirm the same transaction, is the PSP balance explained, and did a settlement actually arrive at the bank?

## What this version models

- 2,000 customer transactions over three months
- 1,700 deposits and 300 payouts
- Customer balances in USD
- PSP processing in INR and MYR
- Separate platform FX rates for deposits and payouts
- PSP fees and a retained local-currency buffer for future payouts
- Weekly settlements from the PSP balance to the bank
- A banking calendar and timing windows for transactions and settlements

A settlement is not assigned to individual payments. The PSP account accumulates deposits, payouts, and fees; the platform retains enough local currency to support upcoming payouts and settles the remaining balance.

## Data flow

```text
Customer transaction
        ↓
Platform ledger (USD customer balance)
        ↓
PSP transactions and PSP account statement (INR / MYR)
        ↓
Settlement report
        ↓
Bank statement (INR / MYR)
```

## Reconciliation controls

The generated data includes both normal timing differences and deliberately injected breaks.

| Control | Example of a break |
|---|---|
| Ledger ↔ PSP transaction matching | PSP shows success, but the ledger is still pending or declined |
| PSP ↔ ledger completeness | A PSP transaction has no platform ledger record |
| Status validation | PSP failed, but the customer was credited |
| FX validation | A rate is inverted or scaled by 100× |
| PSP balance movement | Deposits, payouts, fees, and settlements do not explain the running balance |
| Settlement ↔ bank matching | A settlement is missing from the bank after its timing window |
| Settlement fee validation | The reported fee total differs from transaction-level fees |

Not every difference is an exception. For example, a recent PSP success can remain pending in the ledger within the agreed T+1 window, and a recent settlement can still be waiting for bank posting.

## Generated files

The generator creates files in `data/v2/`:

- `platform_ledger.csv` — customer balance movements in USD
- `psp_transactions.csv` — PSP transaction confirmations and fees
- `psp_account_statement.csv` — PSP running balance movements
- `psp_settlements.csv` — settlement amounts, retained payout buffer, and fee totals
- `bank_statement.csv` — local-currency settlement receipts
- `approved_fx_rates.csv` — approved platform rates for deposits and payouts
- `business_calendar.csv` — working-day calendar used for timing rules
- `customer_opening_balances.csv` — opening customer balances
- `expected_exceptions.csv` — expected outcomes for control validation only

## Run the generator

```bash
python python/generate_v2_data.py
```

The next step is to build dbt models for the reconciliation controls and an exception queue prioritised by amount at risk and age.