from pathlib import Path

import duckdb


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = PROJECT_DIR / "reconciliation.duckdb"


def main():
    con = duckdb.connect(str(DB_PATH))

    con.execute(
        """
        CREATE OR REPLACE TABLE orders AS
        SELECT * FROM read_csv_auto(?)
        """,
        [str(DATA_DIR / "orders.csv")],
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE deliveries AS
        SELECT * FROM read_csv_auto(?)
        """,
        [str(DATA_DIR / "deliveries.csv")],
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE transactions AS
        SELECT * FROM read_csv_auto(?)
        """,
        [str(DATA_DIR / "transactions_sample.csv")],
    )

    con.close()

    print("Database setup completed successfully.")


if __name__ == "__main__":
    main()