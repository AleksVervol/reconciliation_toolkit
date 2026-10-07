# v2 data specification

All files are synthetic and are generated into `data/v2/`.

## Shared conventions

- Customer balances are held in USD.
- PSP transactions, PSP account balances, settlements, and bank receipts are in local currency: INR or MYR.
- FX-rate convention is always **local currency per 1 USD**.
- `provider_transaction_id` is mandatory for every customer payment in scope.
- `local_amount` and `fee_local` are stored as positive values in transaction files. Signs appear only in `psp_account_statement.csv`, where an entry changes the PSP balance.
- Timestamps are used for reconciliation timing. `AS_OF_TIMESTAMP` is the fixed point at which controls are run.

## 1. `business_calendar.csv`

Bank-calendar input used for settlement-to-bank timing.

| Column | Type | Description |
|---|---|---|
| `calendar_date` | date | Calendar date |
| `is_business_day` | boolean | Whether the bank can post a settlement on that date |

Customer payments can happen on weekends. This calendar is used for bank posting only.

## 2. `approved_fx_rates.csv`

Approved platform rates used to calculate customer balance changes.

| Column | Type | Description |
|---|---|---|
| `rate_date` | date | Date of the approved rate |
| `currency` | string | `INR` or `MYR` |
| `approved_deposit_rate` | decimal | Approved local-per-USD rate for deposits |
| `approved_payout_rate` | decimal | Approved local-per-USD rate for payouts |

The deposit and payout rates are separate because the platform can apply a different spread to incoming and outgoing customer flows.

## 3. `customer_opening_balances.csv`

Customer balances immediately before the reporting period begins.

| Column | Type | Description |
|---|---|---|
| `snapshot_date` | date | Date of the opening-balance snapshot |
| `customer_id` | string | Customer identifier |
| `opening_balance_usd` | decimal | Customer balance in USD before generated payments |

Opening balances make early-period payouts possible without assuming that every customer starts at zero.

## 4. `platform_ledger.csv`

The platform’s view of customer balance movements.

| Column | Type | Description |
|---|---|---|
| `ledger_id` | string | Primary key |
| `customer_id` | string | Customer identifier |
| `transaction_type` | string | `deposit` or `payout` |
| `payment_created_at` | timestamp | When the customer payment was created |
| `ledger_status_updated_at` | timestamp | When the platform last updated its status |
| `provider_transaction_id` | string | Join key to the PSP transaction |
| `currency` | string | Transaction currency: `INR` or `MYR` |
| `local_amount` | decimal | Payment amount in local currency |
| `platform_fx_rate` | decimal | Local currency per 1 USD, applied by the platform |
| `customer_balance_change_usd` | decimal | Positive for a deposit, negative for a payout |
| `customer_balance_before_usd` | decimal | Customer balance before this movement |
| `customer_balance_after_usd` | decimal | Customer balance after this movement |
| `status` | string | Usually `credited` for a deposit or `debited` for a payout; scenarios can also be `pending` or `declined` |
| `decline_reason` | string / null | Reason for a declined ledger payment |

Core arithmetic:

```text
customer_balance_after_usd =
    customer_balance_before_usd + customer_balance_change_usd
```

For a deposit:

```text
customer_balance_change_usd = local_amount / platform_fx_rate
```

For a payout:

```text
local_amount = abs(customer_balance_change_usd) × platform_fx_rate
```

## 5. `psp_transactions.csv`

The PSP’s confirmation of customer payments.

| Column | Type | Description |
|---|---|---|
| `psp_record_id` | string | PSP-record primary key |
| `provider_transaction_id` | string | Join key to the platform ledger |
| `transaction_type` | string | `deposit` or `payout` |
| `psp_status_updated_at` | timestamp | When the PSP confirmed or failed the payment |
| `currency` | string | `INR` or `MYR` |
| `local_amount` | decimal | Payment amount in local currency |
| `fee_local` | decimal | PSP fee in local currency |
| `status` | string | `success` or `failed` |

A successful PSP transaction normally produces two PSP account-statement movements: the payment itself and its fee.

## 6. `psp_account_statement.csv`

Running local-currency balance of the platform’s PSP account.

| Column | Type | Description |
|---|---|---|
| `statement_entry_id` | string | Primary key |
| `event_timestamp` | timestamp | Time of the balance movement |
| `currency` | string | `INR` or `MYR` |
| `transaction_type` | string | `deposit`, `payout`, or `settlement` |
| `entry_type` | string | `deposit_received`, `payout_sent`, `psp_fee`, or `settlement` |
| `reference_id` | string | Payment ID or settlement ID that caused the movement |
| `psp_record_id` | string / null | Related PSP transaction record; null for settlement |
| `entry_amount_local` | decimal | Signed local-currency movement |
| `balance_before_local` | decimal | PSP balance before the movement |
| `balance_after_local` | decimal | PSP balance after the movement |

Signs in `entry_amount_local`:

| Entry type | Sign |
|---|---|
| `deposit_received` | positive |
| `payout_sent` | negative |
| `psp_fee` | negative |
| `settlement` | negative |

Core arithmetic:

```text
balance_after_local = balance_before_local + entry_amount_local
```

## 7. `psp_settlements.csv`

Settlement instructions created from the accumulated PSP balance.

| Column | Type | Description |
|---|---|---|
| `settlement_id` | string | Primary key |
| `settlement_timestamp` | timestamp | When the PSP sends the settlement |
| `currency` | string | Settlement currency: `INR` or `MYR` |
| `balance_before_local` | decimal | PSP balance before settlement |
| `payout_buffer_local` | decimal | Local balance retained for future payouts |
| `settlement_local_amount` | decimal | Local-currency amount sent to the bank |
| `balance_after_local` | decimal | PSP balance after settlement |
| `fees_local` | decimal | Transaction-level PSP fees for the settlement review period |

The settlement is not linked to individual transactions. It is the balance surplus after the payout buffer:

```text
settlement_local_amount =
    max(0, balance_before_local - payout_buffer_local)
```

## 8. `bank_statement.csv`

Bank confirmation of received settlements.

| Column | Type | Description |
|---|---|---|
| `bank_entry_id` | string | Primary key |
| `bank_booked_at` | timestamp | When the bank booked the settlement |
| `currency` | string | `INR` or `MYR` |
| `amount_local` | decimal | Amount received by the bank in local currency |
| `entry_type` | string | `psp_settlement_received` |
| `bank_reference` | string | Expected to contain `settlement_id` |

A settlement normally appears on the next business day. Its absence before that window expires is not an exception.

## 9. `expected_exceptions.csv`

Validation reference for generated scenarios. This file is not an input to reconciliation models.

| Column | Type | Description |
|---|---|---|
| `scenario` | string | Name of the generated scenario |
| `provider_transaction_id` | string | Related payment ID or settlement ID |
| `expected_result` | string | `exception` or `normal_timing` |
| `control` | string | Control expected to evaluate the scenario |

The file validates whether controls catch the intended breaks without flagging expected timing noise.