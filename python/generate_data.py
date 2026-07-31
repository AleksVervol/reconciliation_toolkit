import pandas as pd
from faker import Faker
import random

fake = Faker()
Faker.seed(42)      #makes the same data per each 'run'
random.seed(42)

N = 1000  #number of orders that will be generated

orders = []
deliveries = []

for i in range(N):
    order_id = f"ORD{i:05d}"
    amount = round(random.uniform(10, 500), 2)
    order_date = fake.date_between(start_date="-90d", end_date="today")

    orders.append({
        "order_id": order_id,
        "customer": fake.name(),
        "amount": amount,
        "order_date": order_date
    })

    # --- adding discrepancy ---
    roll = random.random()

    if roll < 0.05:
        # 5% without delivery (lost orders)
        continue
    elif roll < 0.10:
        # 5% wrong order amount (incorrect input / partial refund)
        delivered_amount = round(amount - random.uniform(1, 50), 2)
    elif roll < 0.13:
        # 3% duplicated orders
        deliveries.append({
            "order_id": order_id,
            "delivered_amount": amount,
            "delivery_date": fake.date_between(start_date=order_date, end_date="today")
        })
        delivered_amount = amount
    else:
        delivered_amount = amount

    deliveries.append({
        "order_id": order_id,
        "delivered_amount": delivered_amount,
        "delivery_date": fake.date_between(start_date=order_date, end_date="today")
    })

orders_df = pd.DataFrame(orders)
deliveries_df = pd.DataFrame(deliveries)

orders_df.to_csv("./data/orders.csv", index=False)
deliveries_df.to_csv("./data/deliveries.csv", index=False)

print(f"Done: {len(orders_df)} orders, {len(deliveries_df)} delivers")