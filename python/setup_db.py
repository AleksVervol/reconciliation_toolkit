import duckdb

# creating db file
con = duckdb.connect("../reconciliation.duckdb")

con.execute("""
    CREATE OR REPLACE TABLE orders AS 
    SELECT * FROM read_csv_auto('../data/orders.csv')
""")

con.execute("""
    CREATE OR REPLACE TABLE deliveries AS 
    SELECT * FROM read_csv_auto('../data/deliveries.csv')
""")

con.execute("""
    CREATE OR REPLACE TABLE transactions AS 
    SELECT * FROM read_csv_auto('../data/transactions_sample.csv')
""")

print("success")
