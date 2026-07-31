import duckdb

def find_missing(con, table_a, table_b, key):
    """Find records from table_a, that have no pair in table_b."""
    query = f"""
        SELECT a.*
        FROM {table_a} a
        LEFT JOIN {table_b} b ON a.{key} = b.{key}
        WHERE b.{key} IS NULL
    """
    return con.sql(query)


def find_amount_discrepancies(con, table_a, table_b, key, amount_a, amount_b):
    """Find matched records, where amounts in both tables not equal."""
    query = f"""
        SELECT 
            a.{key},
            a.{amount_a} AS amount_a,
            b.{amount_b} AS amount_b,
            a.{amount_a} - b.{amount_b} AS difference
        FROM {table_a} a
        JOIN {table_b} b ON a.{key} = b.{key}
        WHERE a.{amount_a} != b.{amount_b}
    """
    return con.sql(query)


def find_duplicates(con, table, key):
    """Finds keys that appear in the table more than once."""
    query = f"""
        SELECT {key}, COUNT(*) AS record_count
        FROM {table}
        GROUP BY {key}
        HAVING COUNT(*) > 1
    """
    return con.sql(query)