from pathlib import Path
from datetime import date
import random

import pandas as pd
from faker import Faker


SEED = 42
N_ORDERS = 1000

START_DATE = date(2026, 5, 1)
END_DATE = date(2026, 7, 31)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def generate_data():
    fake = Faker()
    Faker.seed(SEED)
    random.seed(SEED)

    orders = []
    deliveries = []

    for i in range(N_ORDERS):
        order_id = f"ORD{i:05d}"
        amount = round(random.uniform(10, 500), 2)

        order_date = fake.date_between(
            start_date=START_DATE,
            end_date=END_DATE,
        )

        orders.append(
            {
                "order_id": order_id,
                "customer": fake.name(),
                "amount": amount,
                "order_date": order_date,
            }
        )

        roll = random.random()

        # 5%: no matching delivery record
        if roll < 0.05:
            continue

        delivery_date = fake.date_between(
            start_date=order_date,
            end_date=END_DATE,
        )

        # 5%: partial delivery / amount discrepancy
        if roll < 0.10:
            delivered_amount = round(
                amount * random.uniform(0.60, 0.95),
                2,
            )

        # 3%: duplicated delivery record
        elif roll < 0.13:
            delivered_amount = amount

            duplicate_record = {
                "order_id": order_id,
                "delivered_amount": delivered_amount,
                "delivery_date": delivery_date,
            }

            deliveries.append(duplicate_record.copy())

        else:
            delivered_amount = amount

        deliveries.append(
            {
                "order_id": order_id,
                "delivered_amount": delivered_amount,
                "delivery_date": delivery_date,
            }
        )

    return pd.DataFrame(orders), pd.DataFrame(deliveries)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    orders_df, deliveries_df = generate_data()

    orders_df.to_csv(DATA_DIR / "orders.csv", index=False)
    deliveries_df.to_csv(DATA_DIR / "deliveries.csv", index=False)

    print(
        f"Done: {len(orders_df)} orders, "
        f"{len(deliveries_df)} delivery records"
    )


if __name__ == "__main__":
    main()