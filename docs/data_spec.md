# v2 data specification

All values synthetic. Illustrative rates only (about 85 INR and 4.4 MYR per
USD); they exist to make errors visible, not to match any real period.

**Rate convention, fixed everywhere:** `local per USD` (for example 85.0 INR
per 1 USD). USD credited = local amount / rate. A rate typed in the opposite
convention is exactly how inversion errors happen, so the convention is part
of the spec.

## Run date

Each generated dataset is one reconciliation run at a fixed `as_of_timestamp`
(a constant in the generator, for example 2026-08-15 10:00:00). Every timing
window (T+1, T+2, pending vs exception) is measured against it, so results
are reproducible.

## Input files

Five files, not four: the PSP settlement report (batch totals, reserve, PSP
rate) is a separate document from the transaction report, so it needs its
own file.

### 1. `platform_ledger.csv`  (what the platform believes)

| Column | Type | Note |
|---|---|---|
| ledger_id | string | primary key |
| customer_id | string | |
| created_at | timestamp | |
| provider_transaction_id | string | join key to PSP; required for PSP deposits in this scope |
| currency | string | INR or MYR |
| local_amount | decimal | amount the customer paid |
| platform_fx_rate | decimal | local per USD, platform's own rate |
| credited_usd | decimal(2) | what the customer received |
| status | string | credited / pending |

### 2. `psp_transactions.csv`  (what the provider confirmed)

| Column | Type | Note |
|---|---|---|
| psp_record_id | string | primary key |
| provider_transaction_id | string | should be unique; duplicates are an exception |
| confirmed_at | timestamp | |
| currency | string | |
| local_amount | decimal | confirmed amount, local currency |
| fee_local | decimal | PSP fee on this transaction |
| status | string | success / failed |
| settlement_batch_id | string | null until included in a batch |

### 3. `psp_settlement_batches.csv`  (the provider's settlement report)

| Column | Type | Note |
|---|---|---|
| settlement_batch_id | string | primary key |
| currency | string | one batch per currency |
| cutoff_at | timestamp | |
| settlement_date | date | |
| txn_count | integer | |
| gross_local | decimal | |
| fees_local | decimal | |
| reserve_local | decimal | withheld, not released in this scope |
| net_local | decimal | gross - fees - reserve |
| settlement_fx_rate | decimal | local per USD, PSP's rate, shown only here |
| net_usd | decimal(2) | net_local / settlement_fx_rate |

### 4. `bank_statement.csv`  (what actually arrived)

| Column | Type | Note |
|---|---|---|
| bank_line_id | string | primary key |
| value_date | date | |
| amount_usd | decimal(2) | |
| reference | string | free text, should contain batch id; sometimes truncated or missing |

Matching batch to bank line, recorded as `match_method`:

1. batch ID found in `reference` -> `reference`;
2. no ID: look up by amount and date; exactly one candidate -> `fallback`;
3. more than one candidate -> `ambiguous`, never merged silently;
4. no candidate -> `unmatched`.

Imperfect references are realistic and are part of the exercise.

### 5. `approved_fx_rates.csv`  (the approved policy rate)

| Column | Type | Note |
|---|---|---|
| rate_date | date | |
| currency | string | |
| approved_platform_rate | decimal | local per USD; the rate approved for customer credit, with the permitted spread already applied |

The generator derives this from a hidden market rate plus a policy spread
(a generator parameter). The platform may fetch its rate at a different
moment than the daily approved rate, so a small tolerance band is still
needed; it covers timing, not margin.

## Controls and starting tolerances

Tolerances are config (`dbt_project.yml` vars) and are **starting values to
tune against the noise**, not facts.

### Level 1: ledger <-> PSP

| Check | Logic | Starting value |
|---|---|---|
| Missing at PSP | ledger credited, no PSP record, older than window | window T+1 |
| Pending, not exception | same, but inside window | |
| Missing in ledger | PSP success, no ledger record, older than window | window T+1 |
| Duplicate PSP ID | count of provider_transaction_id > 1 | |
| Amount mismatch | local amount differs ledger vs PSP | exact (same currency) |
| Failed at PSP, credited in ledger | PSP status failed, ledger status credited | |

### Level 2: FX credit validation

| Check | Logic | Starting value |
|---|---|---|
| Arithmetic | credited_usd vs local_amount / platform_fx_rate | 0.01 USD |
| Rate drift | abs(platform_rate / approved_platform_rate - 1) | 0.5% band **[tune]** |
| Scale error (100x) | platform_rate / approved_platform_rate close to 100 or to 0.01 | ratio within 5% **[tune]**, own exception type |
| Inverted rate | platform_rate * approved_platform_rate close to 1 | product within 5% **[tune]**, own exception type |
| Missing approved rate | no approved rate for date and currency | data-quality exception |

Drift inside the band is not an exception. Scale and inversion errors are
separated from ordinary drift because the cause, the risk, and the fix differ.

The arithmetic check catches a wrong crediting formula even when the ledger
rate looks normal; the rate checks catch a wrong rate even when the
arithmetic is consistent. Each covers the other's blind spot.

### Level 3: PSP batch <-> bank

Expected net, written once and reused everywhere:

```
net_local = gross_local - fees_local - reserve_local
net_usd   = net_local / settlement_fx_rate
```

| Check | Logic | Starting value |
|---|---|---|
| Batch composition | sum of psp_transactions in batch vs batch gross_local | exact |
| Fee composition | sum of fee_local in batch vs batch fees_local | exact; reserve exists only at batch level |
| Report arithmetic | net_usd vs formula above | 0.01 USD |
| Payout vs report | bank amount_usd vs batch net_usd | 0.01 USD **[confirm bank charges]** |
| Batch not received | batch settlement_date plus payout window, no bank line | window T+2 |
| Unmatched bank line | bank line with no batch | |
| Ambiguous bank match | more than one candidate batch by amount and date | flagged, not guessed |

### Customer-credit vs settlement FX variance (metric, not an exception)

```
fx_variance_usd = sum(credited_usd of transactions in batch)
             - gross_local / settlement_fx_rate
```

Positive value: customers were credited more USD than the PSP's rate returns.
This may be a cost to the platform, but it can equally reflect the intended
margin or market movement between the two moments, so it prompts an
investigation and does not deliver a verdict. Fees are excluded to isolate
the FX effect. Reported per batch and per day; alert only above a
configurable threshold.

## Noise and anomalies in the generator

| Type | Treatment |
|---|---|
| Confirmation lag within window | noise, must not be flagged |
| Rounding up to 0.01 USD | noise |
| Rate within drift band | noise |
| Rate outside band for a window of hours or a day | anomaly, clustered |
| Inverted rate, 100x rate, or wrong crediting formula | anomaly, clustered |
| Missing PSP record, missing ledger record, duplicate ID | anomaly, scattered |
| Short or wrong bank payout, missing payout | anomaly, batch level |entity_type | entity_id | anomaly_type | injected_value

Every injected anomaly is written to `_truth.csv` (record id, type, injected
value). dbt never reads it. Report precision and recall per control, with the
false positive count. Run the Level 2 band at several values (for example
0.1%, 0.5%, 1%, 2%) and show how false positives and misses trade off.

## dbt layers

| Layer | Models |
|---|---|
| staging | stg_platform_ledger, stg_psp_transactions, stg_psp_settlement_batches, stg_bank_statement, stg_approved_fx_rates |
| prep | prep_txn_reconciliation (L1), prep_fx_validation (L2), prep_batch_reconciliation (L3, with `match_method`), prep_fx_variance |
| mart | mart_exception_queue (one row per exception), mart_fx_variance_daily, mart_control_summary |

Exception priority: USD at risk x age in days, so the queue answers
"what burns first". Each row carries the action the team would take, as in
the scope table.
