# v2 scope: Multi-Currency Payment Reconciliation & Settlement Control

This is a synthetic portfolio project. It models a payments reconciliation flow from a customer transaction to the platform ledger, the PSP account balance, settlement, and the bank statement.

Values marked **[tune]** are starting assumptions for the project, not claims about one universal payment-industry rule.

## The flow being modelled

1. A customer makes a deposit or receives a payout.
2. The platform records the customer balance movement in USD.
3. The PSP processes the transaction in local currency: INR or MYR.
4. Deposits, payouts, and PSP fees change the running PSP balance.
5. On a weekly schedule, the PSP sends a settlement from the available local-currency balance.
6. The bank statement confirms that settlement on the next business day.

A settlement is not a collection of transaction-level payouts. It is a withdrawal of accumulated funds from the PSP balance after retaining a buffer for future customer payouts.

## Currency and FX logic

| Area | Currency |
|---|---|
| Customer balance and platform ledger | USD |
| PSP transactions, PSP balance, settlement, bank receipt | INR or MYR |

The platform applies its own approved rate when calculating a customer balance movement:

- for a **deposit**, `usd credited = local amount / approved_deposit_rate`;
- for a **payout**, `local amount = usd debited × approved_payout_rate`.

The project uses separate approved deposit and payout rates. This reflects that the platform can apply a spread differently for incoming and outgoing customer flows.

Settlement is sent to the bank in the same local currency. FX conversion between the PSP balance and the bank is out of scope: it would be a separately agreed treasury or exchange process.

## Settlement logic

The PSP account statement is a running local-currency balance:

```text
deposit       → increases PSP balance
payout        → decreases PSP balance
PSP fee       → decreases PSP balance
settlement    → decreases PSP balance
```

Before each settlement, the model retains a local-currency payout buffer:

```text
payout buffer = (successful payouts + PSP fees during the previous 7 days) × 1.20
```

The `1.20` multiplier and weekly Monday settlement schedule are **[tune]** assumptions. They exist to create a realistic reason why the PSP balance is not settled to zero.

## In scope

- Customer deposits and payouts;
- Customer opening balances and balance changes in USD;
- PSP transaction confirmations in INR and MYR;
- Separate timestamps for payment creation and status update;
- PSP transaction fees;
- Running PSP account balance;
- Local-currency settlements and bank receipts;
- Business-day calendar and timing windows;
- Approved platform FX rates for deposits and payouts;
- Reconciliation controls and a prioritised exception queue.

## Out of scope

- Real PSP, bank, customer, or employer data;
- Manual ledger adjustments;
- Chargebacks, refunds, and reserve release;
- Automatic FX conversion of settlement funds;
- Treasury hedging or exchange-provider selection;
- Predictive fraud or risk scoring models.

## Reconciliation controls

| Control | Compares | Examples of breaks |
|---|---|---|
| Transaction completeness | Platform ledger ↔ PSP transactions | A PSP success has no ledger record; a ledger payment has no PSP record |
| Status and timing | Platform ledger ↔ PSP transactions | PSP success while ledger is overdue pending or declined; PSP failed while ledger is credited |
| Transaction amounts | Platform ledger ↔ PSP transactions | Local amount differs between the two sources |
| FX validation | Local amount, platform rate, USD balance movement | 100× rate error, inverted rate, arithmetic mismatch |
| PSP balance reconciliation | PSP transactions and settlements ↔ PSP account statement | A movement does not explain the running balance |
| Settlement fee validation | Transaction-level fees ↔ settlement fee total | Settlement reports an incorrect fee total |
| Settlement-to-bank reconciliation | PSP settlements ↔ bank statement | A settlement is missing from the bank after its timing window |

## Timing rules

A difference is not automatically an exception.

- A PSP transaction can be successful while the platform ledger remains `pending` inside the T+1 window **[tune]**.
- A PSP settlement can be absent from the bank statement until the next business-day posting window has passed.
- Weekend payments are valid. The business calendar affects bank posting, not whether customers can make payments.

The controls should identify overdue breaks without flagging expected processing delays.

## Generated scenarios

The generator includes normal and exceptional cases:

- a recent PSP success with a ledger status still `pending` — expected timing, not an exception;
- PSP success with overdue pending or declined ledger status;
- PSP failure while the ledger still credits the customer;
- a PSP transaction absent from the ledger;
- a 100× FX-rate error;
- an inverted FX rate;
- a settlement missing from the bank after its timing window;
- a settlement fee total that does not match the underlying PSP transactions.

`expected_exceptions.csv` is the validation reference for these cases. Reconciliation models must not read it as an input source.

## Delivery stages

1. Generate synthetic sources and expected scenarios — complete.
2. Build dbt staging and reconciliation models.
3. Add data tests and an exception queue prioritised by amount at risk and age.
4. Build a Tableau dashboard and final project documentation.