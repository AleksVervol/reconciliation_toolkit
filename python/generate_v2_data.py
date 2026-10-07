from datetime import datetime
from pathlib import Path
import random
import pandas as pd


SEED = 42
AS_OF_TIMESTAMP = pd.Timestamp("2026-08-17 10:00:00")

START_DATE = pd.Timestamp("2026-05-18")
END_DATE = pd.Timestamp("2026-08-14")

N_TRANSACTIONS = 2000
N_CUSTOMERS = 150

OPENING_BALANCE_MIN_USD = 200
OPENING_BALANCE_MAX_USD = 2_000

PAYOUT_SHARE = 0.15
MIN_PAYOUT_USD = 10
MAX_PAYOUT_USD = 300

SETTLEMENT_HOUR = 7
# [tune] Buffer = (last 7 days' payout amount + PSP fees) × 1.20.
# It remains in the PSP account as liquidity for future client payouts.
PSP_PAYOUT_BUFFER_MULTIPLIER = 1.20

BANK_POSTING_HOUR = 10

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "v2"

CURRENCIES = {
    "INR": {"base_rate": 85.0, "deposit_spread": 0.006, "payout_spread": 0.006,},
    "MYR": {"base_rate": 4.4, "deposit_spread": 0.005, "payout_spread": 0.005,}}

PSP_FEE_RATE = 0.024  # illustrative assumption: 2.4%

def build_business_calendar() -> pd.DataFrame:
    dates = pd.date_range(start=START_DATE, end=AS_OF_TIMESTAMP.normalize() + pd.Timedelta(days=7), freq="D",)
    calendar = pd.DataFrame({"calendar_date": dates})
    calendar["is_business_day"] = calendar["calendar_date"].dt.dayofweek < 5
    return calendar


def build_approved_fx_rates(calendar: pd.DataFrame) -> pd.DataFrame:
    """
    Creates approved platform FX rates for every day when a client
    payment can happen, including weekends.

    Rates are quoted as local currency per 1 USD.
    The platform rate is above market for deposits and below market
    for payouts, so the spread works in the platform's favour.
    """
    rng = random.Random(SEED)
    rows = []
    payment_dates = calendar.loc[calendar["calendar_date"] <= END_DATE, "calendar_date",]

    for rate_date in payment_dates:
        for currency, config in CURRENCIES.items():
            hidden_market_rate = config["base_rate"] * (1 + rng.uniform(-0.004, 0.004))
            approved_deposit_rate = hidden_market_rate * (1 + config["deposit_spread"])
            approved_payout_rate = hidden_market_rate * (1 - config["payout_spread"])
            rows.append({
                    "rate_date": rate_date.date(),
                    "currency": currency,
                    "approved_deposit_rate": round(approved_deposit_rate, 6),
                    "approved_payout_rate": round(approved_payout_rate, 6),})
    return pd.DataFrame(rows)

def get_approved_rate(approved_rates, payment_date, currency, transaction_type,):
    """
    Returns the approved rate for one payment.
    Deposit and payout use different approved rates because the
    platform spread has an opposite direction for the two operations.
    """
    matching_rate = approved_rates[(approved_rates["rate_date"] == payment_date.date()) & (approved_rates["currency"] == currency)]

    if transaction_type == "deposit":
        return matching_rate["approved_deposit_rate"].iloc[0]
    return matching_rate["approved_payout_rate"].iloc[0]


def build_clean_payments(calendar, approved_rates, opening_balances,):
    """
    Generates clean customer deposits and payouts.
    Every payout is limited by the customer's available USD balance.
    The function returns two source files:
    - platform ledger records;
    - PSP transaction records.
    """
    rng = random.Random(SEED)

    # Client payments can happen on any calendar day.
    # The business calendar is used later for settlements and bank postings.
    payment_dates = calendar.loc[calendar["calendar_date"] <= END_DATE, "calendar_date",].tolist()

    # This dictionary stores the current USD balance of every customer.
    # It starts with the snapshot created before the reporting period.
    customer_balances = {}

    for _, customer in opening_balances.iterrows():
        customer_balances[customer["customer_id"]] = (customer["opening_balance_usd"])

    customer_ids = list(customer_balances.keys())

    # Create exactly 15% payouts and 85% deposits, then mix their order.
    payout_count = int(N_TRANSACTIONS * PAYOUT_SHARE)

    transaction_types = (["payout"] * payout_count + ["deposit"] * (N_TRANSACTIONS - payout_count))
    rng.shuffle(transaction_types)

    # Create and sort timestamps so balance changes follow one timeline.
    payment_timestamps = []

    for _ in range(N_TRANSACTIONS):
        payment_date = rng.choice(payment_dates)
        payment_timestamps.append(payment_date + pd.Timedelta(hours=rng.randint(8, 20), minutes=rng.randint(0, 59),))

    payment_timestamps.sort()

    ledger_rows = []
    psp_rows = []

    for number, (transaction_type, payment_created_at) in enumerate(zip(transaction_types, payment_timestamps), start=1,):
        payment_date = payment_created_at.normalize()
        currency = rng.choice(["INR", "MYR"])

        approved_rate = get_approved_rate(approved_rates, payment_date, currency, transaction_type,)

        # The platform rate differs slightly from the daily policy rate.
        # This is normal timing variation, not an injected error.
        platform_fx_rate = round(approved_rate * (1 + rng.uniform(-0.002, 0.002)), 6,)

        if transaction_type == "deposit":
            # A deposit increases the customer's USD balance.
            customer_id = rng.choice(customer_ids)

            if currency == "INR":
                local_amount = round(rng.uniform(500, 50_000), 2)
            else:
                local_amount = round(rng.uniform(30, 2_000), 2)

            usd_amount = round(local_amount / platform_fx_rate, 2)
            customer_balance_change_usd = usd_amount
            ledger_status = "credited"

        else:
            # A payout is allowed only for a customer with enough USD.
            eligible_customers = [customer_id for customer_id, balance_usd in customer_balances.items() if balance_usd >= MIN_PAYOUT_USD]

            customer_id = rng.choice(eligible_customers)
            available_balance_usd = customer_balances[customer_id]

            # The payout cannot exceed the customer's current balance.
            max_payout_usd = min(MAX_PAYOUT_USD, available_balance_usd,)

            usd_amount = round(rng.uniform(MIN_PAYOUT_USD, max_payout_usd), 2,)

            local_amount = round(usd_amount * platform_fx_rate, 2)
            customer_balance_change_usd = -usd_amount
            ledger_status = "debited"

        # Save the customer balance before and after this operation.
        customer_balance_before_usd = round(customer_balances[customer_id], 2,)

        customer_balance_after_usd = round(customer_balance_before_usd + customer_balance_change_usd, 2,)

        customer_balances[customer_id] = customer_balance_after_usd

        # A PSP status arrives first; the platform updates its own status later.
        psp_status_updated_at = payment_created_at + pd.Timedelta(minutes=rng.randint(5, 180))

        ledger_status_updated_at = psp_status_updated_at + pd.Timedelta(minutes=rng.randint(1, 60))

        provider_transaction_id = f"PAY{number:06d}"

        ledger_rows.append({
                "ledger_id": f"LED{number:06d}",
                "customer_id": customer_id,
                "transaction_type": transaction_type,
                "payment_created_at": payment_created_at,
                "ledger_status_updated_at": ledger_status_updated_at,
                "provider_transaction_id": provider_transaction_id,
                "currency": currency,
                "local_amount": local_amount,
                "platform_fx_rate": platform_fx_rate,
                "customer_balance_change_usd": (customer_balance_change_usd),
                "customer_balance_before_usd": (customer_balance_before_usd),
                "customer_balance_after_usd": (customer_balance_after_usd),
                "status": ledger_status,
                "decline_reason": None,
            })

        psp_rows.append({
                "psp_record_id": f"PSP{number:06d}",
                "provider_transaction_id": provider_transaction_id,
                "transaction_type": transaction_type,
                "psp_status_updated_at": psp_status_updated_at,
                "currency": currency,
                "local_amount": local_amount,
                "fee_local": round(local_amount * PSP_FEE_RATE, 2),
                "status": "success",
            })

    return pd.DataFrame(ledger_rows), pd.DataFrame(psp_rows)

def find_last_deposit_for_customer(ledger, excluded_transaction_ids, latest_payment_time=None,):
    """
    Finds a deposit that is the customer's last ledger operation.

    This lets us change its status to pending or declined without
    rewriting later balances for the same customer.
    """
    candidates = ledger.loc[
        (ledger["transaction_type"] == "deposit")
        & (~ledger["provider_transaction_id"].isin(excluded_transaction_ids))].copy()

    if latest_payment_time is not None:
        candidates = candidates.loc[candidates["payment_created_at"] <= latest_payment_time]

    candidates = candidates.sort_values("payment_created_at", ascending=False,)

    for row_index, candidate in candidates.iterrows():
        later_customer_operations = ledger.loc[
            (ledger["customer_id"] == candidate["customer_id"])
            & (ledger["payment_created_at"] > candidate["payment_created_at"])]

        if later_customer_operations.empty:
            return row_index

    raise ValueError("Could not find a suitable deposit scenario.")


def find_psp_row(psp_transactions, provider_transaction_id):
    """Returns the PSP row that belongs to one platform payment."""
    matching_rows = psp_transactions.index[psp_transactions["provider_transaction_id"] == provider_transaction_id]

    return matching_rows[0]


def set_unfinished_ledger_status(ledger, row_index, status, decline_reason=None,):
    """
    Marks a deposit as pending or declined.

    An unfinished deposit must not change the customer's available
    USD balance, so its balance before and after stays the same.
    """
    balance_before_usd = ledger.at[row_index, "customer_balance_before_usd",]

    ledger.at[row_index, "status"] = status
    ledger.at[row_index, "decline_reason"] = decline_reason
    ledger.at[row_index, "customer_balance_change_usd"] = 0.0
    ledger.at[row_index, "customer_balance_after_usd"] = (balance_before_usd)

def find_deposit_for_fx(ledger, excluded_transaction_ids, currency, target_local_amount,):
    """
    Finds a normal credited deposit for an FX scenario.

    target_local_amount keeps the synthetic error noticeable but not
    absurdly large.
    """
    candidates = ledger.loc[(ledger["transaction_type"] == "deposit")
        & (ledger["status"] == "credited")
        & (ledger["currency"] == currency)
        & (~ledger["provider_transaction_id"].isin(excluded_transaction_ids))].copy()

    distance_from_target = (candidates["local_amount"] - target_local_amount).abs()

    return distance_from_target.idxmin()


def apply_deposit_fx_error(ledger, row_index, wrong_fx_rate):
    """
    Applies a wrong FX rate to one credited deposit.

    The PSP local amount stays correct. Only the platform's USD credit
    is wrong. The difference is carried into later balances of the
    same customer, because the platform would continue from its own
    incorrect balance.
    """
    customer_id = ledger.at[row_index, "customer_id"]
    payment_created_at = ledger.at[row_index, "payment_created_at",]

    local_amount = ledger.at[row_index, "local_amount"]
    old_usd_credit = ledger.at[row_index, "customer_balance_change_usd",]
    balance_before_usd = ledger.at[row_index, "customer_balance_before_usd",]

    new_usd_credit = round(local_amount / wrong_fx_rate, 2,)
    balance_difference_usd = round(new_usd_credit - old_usd_credit, 2,)

    # Change the affected deposit itself.
    ledger.at[row_index, "platform_fx_rate"] = wrong_fx_rate
    ledger.at[row_index, "customer_balance_change_usd"] = (new_usd_credit)
    ledger.at[row_index, "customer_balance_after_usd"] = round(balance_before_usd + new_usd_credit, 2,)

    # Later operations for the same customer start from the wrong
    # balance, so both their before and after balances move by delta.
    later_rows = ledger.index[(ledger["customer_id"] == customer_id) & (ledger["payment_created_at"] > payment_created_at)]

    ledger.loc[later_rows, "customer_balance_before_usd",] = (
        ledger.loc[later_rows, "customer_balance_before_usd",] + balance_difference_usd).round(2)

    ledger.loc[later_rows, "customer_balance_after_usd",] = (
        ledger.loc[later_rows, "customer_balance_after_usd",] + balance_difference_usd).round(2)

def inject_scenarios(ledger, psp_transactions):
    """
    Adds controlled reconciliation scenarios after the clean payment flow has been created.

    The expected_exceptions table is only a QA reference for us.
    Future dbt models must never use it as an input source.
    """
    ledger = ledger.copy()
    psp_transactions = psp_transactions.copy()
    scenarios = []
    used_transaction_ids = set()

    # 1. PSP succeeded, but an old deposit is still pending in the ledger.
    overdue_index = find_last_deposit_for_customer(ledger, used_transaction_ids, latest_payment_time=pd.Timestamp("2026-08-12 23:59:59"),)
    overdue_id = ledger.at[overdue_index, "provider_transaction_id"]

    set_unfinished_ledger_status(ledger, overdue_index, status="pending",)

    used_transaction_ids.add(overdue_id)
    scenarios.append({
            "scenario": "psp_success_ledger_pending_overdue",
            "provider_transaction_id": overdue_id,
            "expected_result": "exception",
            "control": "ledger_psp_status_timing",
        })

    # 2. PSP succeeded only recently, so ledger pending is still normal.
    recent_pending_index = find_last_deposit_for_customer(ledger, used_transaction_ids,)
    recent_pending_id = ledger.at[recent_pending_index, "provider_transaction_id",]
    recent_psp_index = find_psp_row(psp_transactions, recent_pending_id,)

    psp_transactions.at[recent_psp_index, "psp_status_updated_at",] = AS_OF_TIMESTAMP - pd.Timedelta(minutes=45)

    ledger.at[recent_pending_index, "ledger_status_updated_at",] = AS_OF_TIMESTAMP - pd.Timedelta(minutes=15)

    set_unfinished_ledger_status(ledger, recent_pending_index, status="pending",)

    used_transaction_ids.add(recent_pending_id)
    scenarios.append({
            "scenario": "psp_success_ledger_pending_within_t1",
            "provider_transaction_id": recent_pending_id,
            "expected_result": "normal_timing",
            "control": "ledger_psp_status_timing",
        })

    # 3. PSP succeeded, but the platform declined the deposit.
    declined_index = find_last_deposit_for_customer(ledger, used_transaction_ids, latest_payment_time=pd.Timestamp("2026-08-13 23:59:59"),)
    declined_id = ledger.at[declined_index, "provider_transaction_id",]

    set_unfinished_ledger_status(ledger, declined_index, status="declined", decline_reason="risk_rule_after_psp_success",)

    used_transaction_ids.add(declined_id)
    scenarios.append({
            "scenario": "psp_success_ledger_declined",
            "provider_transaction_id": declined_id,
            "expected_result": "exception",
            "control": "ledger_psp_status_match",
        })

    # 4. The platform credited a deposit, although PSP reports failure.
    failed_psp_candidates = ledger.loc[(ledger["transaction_type"] == "deposit")
        & (~ledger["provider_transaction_id"].isin(used_transaction_ids))].sort_values("payment_created_at")

    failed_psp_id = failed_psp_candidates.iloc[100]["provider_transaction_id"]
    failed_psp_index = find_psp_row(psp_transactions, failed_psp_id,)

    psp_transactions.at[failed_psp_index, "status"] = "failed"
    psp_transactions.at[failed_psp_index, "fee_local"] = 0.0

    scenarios.append({
            "scenario": "psp_failed_ledger_credited",
            "provider_transaction_id": failed_psp_id,
            "expected_result": "exception",
            "control": "ledger_psp_status_match",
        })
    
    # 5. PSP shows a successful deposit missing from the platform ledger.
    # The money is visible at the PSP, but no customer credit was created.
    psp_only_provider_id = "PAY002001"

    psp_only_transaction = pd.DataFrame([{
                "psp_record_id": "PSP002001",
                "provider_transaction_id": psp_only_provider_id,
                "transaction_type": "deposit",
                "psp_status_updated_at": pd.Timestamp("2026-08-13 14:20:00"),
                "currency": "INR",
                "local_amount": 25000.00,
                "fee_local": 600.00,
                "status": "success",
            }])

    psp_transactions = pd.concat([psp_transactions, psp_only_transaction], ignore_index=True,)

    scenarios.append({
            "scenario": "psp_success_missing_from_ledger",
            "provider_transaction_id": psp_only_provider_id,
            "expected_result": "exception",
            "control": "ledger_psp_1_to_1",
        })
    
    # 6. A deposit uses a rate 100 times too small.
    # The client receives about 100 times too much USD.
    scenario_transaction_ids = {scenario["provider_transaction_id"] for scenario in scenarios}

    rate_100x_index = find_deposit_for_fx(ledger, scenario_transaction_ids, currency="INR", target_local_amount=1000,)
    rate_100x_id = ledger.at[rate_100x_index, "provider_transaction_id",]
    original_rate = ledger.at[rate_100x_index, "platform_fx_rate",]

    apply_deposit_fx_error(ledger, rate_100x_index, wrong_fx_rate=round(original_rate / 100, 6),)

    scenarios.append({
            "scenario": "fx_rate_scaled_by_100",
            "provider_transaction_id": rate_100x_id,
            "expected_result": "exception",
            "control": "fx_rate_validation",
        })

    # 7. A deposit stores the FX rate in the opposite direction.
    scenario_transaction_ids.add(rate_100x_id)

    inverted_rate_index = find_deposit_for_fx(ledger, scenario_transaction_ids, currency="MYR", target_local_amount=30,)
    inverted_rate_id = ledger.at[inverted_rate_index, "provider_transaction_id",]
    original_rate = ledger.at[inverted_rate_index, "platform_fx_rate",]

    apply_deposit_fx_error(ledger, inverted_rate_index, wrong_fx_rate=round(1 / original_rate, 6),)

    scenarios.append({
            "scenario": "fx_rate_inverted",
            "provider_transaction_id": inverted_rate_id,
            "expected_result": "exception",
            "control": "fx_rate_validation",
        })
    return ledger, psp_transactions, pd.DataFrame(scenarios)

def build_customer_opening_balances():
    """
    Creates the USD balances customers had before the reporting period.
    The snapshot is taken at the start of 18 May. It lets the project
    model valid early payouts without pretending every customer starts
    with a zero balance.
    """
    rng = random.Random(SEED + 1)
    rows = []

    for number in range(1, N_CUSTOMERS + 1):
        opening_balance_usd = round(rng.uniform(OPENING_BALANCE_MIN_USD, OPENING_BALANCE_MAX_USD,), 2,)
        rows.append({"snapshot_date": START_DATE.date(), "customer_id": f"CUS{number:04d}", "opening_balance_usd": opening_balance_usd,})
    return pd.DataFrame(rows)

def get_payout_buffer(psp_transactions, settlement_timestamp, currency,):
    """
    Estimates how much local balance should stay in the PSP account.
    The buffer equals the previous seven days of successful payouts,
    including PSP fees, plus a 20% safety margin.
    """
    window_start = settlement_timestamp - pd.Timedelta(days=7)
    recent_payouts = psp_transactions.loc[
        (psp_transactions["transaction_type"] == "payout")
        & (psp_transactions["currency"] == currency)
        & (psp_transactions["psp_status_updated_at"] >= window_start)
        & (psp_transactions["psp_status_updated_at"] < settlement_timestamp)]

    payout_cost_local = (recent_payouts["local_amount"] + recent_payouts["fee_local"]).sum()

    return round(payout_cost_local * PSP_PAYOUT_BUFFER_MULTIPLIER, 2,)

def get_settlement_fees(psp_transactions, settlement_timestamp, currency,):
    """
    Returns total PSP fees for the seven-day settlement period.

    Weekly settlement happens on Monday, so the period starts seven
    days earlier. This amount is later compared with transaction fees.
    """
    window_start = settlement_timestamp - pd.Timedelta(days=7)

    period_transactions = psp_transactions.loc[(psp_transactions["status"] == "success")
        & (psp_transactions["currency"] == currency)
        & (psp_transactions["psp_status_updated_at"] >= window_start)
        & (psp_transactions["psp_status_updated_at"] < settlement_timestamp)]

    return round(period_transactions["fee_local"].sum(), 2)

def build_psp_account_statement(psp_transactions, calendar):
    """
    Creates a PSP account statement and weekly settlements.

    Every Monday at 07:00, the PSP sends only the local-currency
    balance above the payout buffer. Automatic settlements do not
    convert INR or MYR to USD.
    """
    transactions = psp_transactions.loc[psp_transactions["status"] == "success"].copy()
    transactions["psp_status_updated_at"] = pd.to_datetime(transactions["psp_status_updated_at"])

    events = []

    # Add deposit, payout and fee movements to the PSP statement.
    for _, transaction in transactions.iterrows():
        if transaction["transaction_type"] == "deposit":
            payment_amount_local = transaction["local_amount"]
            payment_entry_type = "deposit_received"
        else:
            payment_amount_local = -transaction["local_amount"]
            payment_entry_type = "payout_sent"

        events.append({
                "event_timestamp": transaction["psp_status_updated_at"],
                "currency": transaction["currency"],
                "transaction_type": transaction["transaction_type"],
                "entry_type": payment_entry_type,
                "reference_id": transaction["provider_transaction_id"],
                "psp_record_id": transaction["psp_record_id"],
                "entry_amount_local": payment_amount_local,
                "is_settlement": False,
            })

        events.append({
                "event_timestamp": (transaction["psp_status_updated_at"] + pd.Timedelta(minutes=1)),
                "currency": transaction["currency"],
                "transaction_type": transaction["transaction_type"],
                "entry_type": "psp_fee",
                "reference_id": transaction["provider_transaction_id"],
                "psp_record_id": transaction["psp_record_id"],
                "entry_amount_local": -transaction["fee_local"],
                "is_settlement": False,
            })

    # Plan one possible settlement for each currency every Monday morning.
    settlement_dates = calendar.loc[(calendar["is_business_day"])
        & (calendar["calendar_date"].dt.dayofweek == 0)
        & (calendar["calendar_date"] <= AS_OF_TIMESTAMP.normalize()), "calendar_date",]

    for settlement_date in settlement_dates:
        for currency in CURRENCIES:
            events.append({
                    "event_timestamp": settlement_date + pd.Timedelta(hours=SETTLEMENT_HOUR),
                    "currency": currency,
                    "transaction_type": "settlement",
                    "entry_type": "settlement",
                    "reference_id": None,
                    "psp_record_id": None,
                    "entry_amount_local": None,
                    "is_settlement": True,
                })

    events.sort(key=lambda event: event["event_timestamp"])

    psp_balances = {"INR": 0.0, "MYR": 0.0}
    statement_rows = []
    settlement_rows = []

    for event in events:
        currency = event["currency"]
        balance_before_local = psp_balances[currency]

        if event["is_settlement"]:
            payout_buffer_local = get_payout_buffer(transactions, event["event_timestamp"], currency,)
            fees_local = get_settlement_fees(transactions, event["event_timestamp"], currency,)
            # Only the surplus is sent to the bank.
            settlement_local_amount = round(max(0, balance_before_local - payout_buffer_local), 2,)

            # No surplus means no settlement record.
            if settlement_local_amount == 0:
                continue

            settlement_id = (f"SET{event['event_timestamp'].strftime('%Y%m%d')}_{currency}")

            entry_amount_local = -settlement_local_amount
            balance_after_local = round(balance_before_local + entry_amount_local, 2,)

            event["reference_id"] = settlement_id

            settlement_rows.append({
                    "settlement_id": settlement_id,
                    "settlement_timestamp": event["event_timestamp"],
                    "currency": currency,
                    "fees_local": fees_local,
                    "balance_before_local": balance_before_local,
                    "payout_buffer_local": payout_buffer_local,
                    "settlement_local_amount": settlement_local_amount,
                    "balance_after_local": balance_after_local,
                })

        else:
            entry_amount_local = event["entry_amount_local"]
            balance_after_local = round(balance_before_local + entry_amount_local, 2,)

            if balance_after_local < 0:
                raise ValueError(f"Negative PSP balance in {currency} after {event['reference_id']}")

        psp_balances[currency] = balance_after_local

        statement_rows.append({
                "statement_entry_id": (f"STM{len(statement_rows) + 1:06d}"),
                "event_timestamp": event["event_timestamp"],
                "currency": currency,
                "transaction_type": event["transaction_type"],
                "entry_type": event["entry_type"],
                "reference_id": event["reference_id"],
                "psp_record_id": event["psp_record_id"],
                "entry_amount_local": entry_amount_local,
                "balance_before_local": balance_before_local,
                "balance_after_local": balance_after_local,})

    return pd.DataFrame(statement_rows), pd.DataFrame(settlement_rows)

def get_next_business_day(calendar, current_timestamp):
    """
    Returns the first business day after a timestamp.

    The project uses this small calendar instead of assuming that every
    weekday is automatically a bank working day.
    """
    future_business_days = calendar.loc[(calendar["calendar_date"] > current_timestamp.normalize())
        & calendar["is_business_day"], "calendar_date",]

    return future_business_days.iloc[0]


def build_bank_statement(settlements, calendar):
    """
    Creates bank entries for settlements received from the PSP.

    A settlement arrives on the next business day in the same local
    currency. Settlements not yet expected in the bank at AS_OF_TIMESTAMP
    are deliberately excluded from this report.
    """
    rows = []

    for number, settlement in settlements.iterrows():
        settlement_timestamp = pd.Timestamp(settlement["settlement_timestamp"])
        bank_business_day = get_next_business_day(calendar, settlement_timestamp,)

        bank_booked_at = bank_business_day + pd.Timedelta(hours=BANK_POSTING_HOUR)

        # Keep only bank entries that are known at the reconciliation time.
        if bank_booked_at > AS_OF_TIMESTAMP:
            continue

        rows.append({
                "bank_entry_id": f"BNK{number + 1:06d}",
                "bank_booked_at": bank_booked_at,
                "currency": settlement["currency"],
                "amount_local": settlement["settlement_local_amount"],
                "entry_type": "psp_settlement_received",
                "bank_reference": settlement["settlement_id"],
            })

    return pd.DataFrame(rows)

def inject_settlement_scenarios(settlements, bank_statement, expected_exceptions,):
    """
    Adds controlled reconciliation breaks after settlement and bank
    reports have been created.

    One settlement is missing from the bank after T+1. Another has an
    incorrect reported fee total while underlying PSP transactions
    remain unchanged.
    """
    settlements = settlements.copy()
    bank_statement = bank_statement.copy()
    expected_exceptions = expected_exceptions.copy()

    # 8. A completed PSP settlement is missing from the bank after T+1.
    missing_bank_entry = bank_statement.sort_values("bank_booked_at", ascending=False,).iloc[0]

    missing_settlement_id = missing_bank_entry["bank_reference"]

    bank_statement = bank_statement.loc[bank_statement["bank_reference"] != missing_settlement_id].copy()

    # 9. The PSP settlement report shows a wrong total fee.
    fee_candidates = settlements.loc[settlements["settlement_id"] != missing_settlement_id].sort_values("settlement_timestamp", ascending=False,)

    fee_row_index = fee_candidates.index[0]
    fee_settlement_id = settlements.at[fee_row_index, "settlement_id",]

    correct_fee_local = settlements.at[fee_row_index, "fees_local",]

    settlements.at[fee_row_index, "fees_local"] = round(correct_fee_local * 1.12, 2,)

    new_scenarios = pd.DataFrame([{
                "scenario": "settlement_missing_from_bank_after_t1",
                "provider_transaction_id": missing_settlement_id,
                "expected_result": "exception",
                "control": "psp_settlement_to_bank",},
            {
                "scenario": "settlement_fee_total_mismatch",
                "provider_transaction_id": fee_settlement_id,
                "expected_result": "exception",
                "control": "settlement_fee_reconciliation",
            },])

    expected_exceptions = pd.concat([expected_exceptions, new_scenarios], ignore_index=True,)

    return settlements, bank_statement, expected_exceptions

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    calendar = build_business_calendar()
    approved_rates = build_approved_fx_rates(calendar)
    opening_balances = build_customer_opening_balances()
    ledger, psp_transactions = build_clean_payments(calendar, approved_rates, opening_balances,)
    ledger, psp_transactions, expected_exceptions = (inject_scenarios(ledger, psp_transactions,))
    psp_statement, settlements = build_psp_account_statement(psp_transactions, calendar,)
    bank_statement = build_bank_statement(settlements, calendar,)
    settlements, bank_statement, expected_exceptions = (inject_settlement_scenarios(settlements, bank_statement, expected_exceptions,))

    calendar.to_csv(DATA_DIR / "business_calendar.csv", index=False)
    approved_rates.to_csv(DATA_DIR / "approved_fx_rates.csv", index=False)
    ledger.to_csv(DATA_DIR / "platform_ledger.csv", index=False)
    psp_transactions.to_csv(DATA_DIR / "psp_transactions.csv", index=False,)
    opening_balances.to_csv(DATA_DIR / "customer_opening_balances.csv", index=False,)
    psp_statement.to_csv(DATA_DIR / "psp_account_statement.csv", index=False,)
    settlements.to_csv(DATA_DIR / "psp_settlements.csv", index=False,)
    bank_statement.to_csv(DATA_DIR / "bank_statement.csv", index=False,)
    expected_exceptions.to_csv(DATA_DIR / "expected_exceptions.csv", index=False,)

    deposit_count = (ledger["transaction_type"] == "deposit").sum()
    payout_count = (ledger["transaction_type"] == "payout").sum()

    print(f"Created {len(ledger)} payments: {deposit_count} deposits "
        f"and {payout_count} payouts. Created {len(psp_statement)} PSP statement entries. Created {len(bank_statement)} bank entries.")    
    print(f"Added {len(expected_exceptions)} reconciliation scenarios.")

if __name__ == "__main__":
    main()