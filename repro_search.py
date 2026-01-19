import duckdb
import os

def check_db():
    if not os.path.exists("dictionary.duckdb"):
        print("dictionary.duckdb not found")
        return

    conn = duckdb.connect("dictionary_copy.duckdb", read_only=True)
    
    # Check 'central'
    res = conn.execute("SELECT COUNT(*) FROM tokens WHERE token ILIKE 'central'").fetchone()
    print(f"Count 'central': {res[0]}")

    # Check 'bank'
    res = conn.execute("SELECT COUNT(*) FROM tokens WHERE token ILIKE 'bank'").fetchone()
    print(f"Count 'bank': {res[0]}")

    # Check 'central bank'
    query = """
    SELECT COUNT(*) 
    FROM tokens t0
    JOIN tokens t1 ON t0.id + 1 = t1.id AND t0.file_id = t1.file_id
    WHERE t0.token ILIKE 'central' AND t1.token ILIKE 'bank'
    """
    res = conn.execute(query).fetchone()
    print(f"Count 'central bank': {res[0]}")

    # Check what corpora are available
    res = conn.execute("SELECT DISTINCT corpus FROM tokens").fetchall()
    print(f"Corpora: {[r[0] for r in res]}")

    conn.close()

if __name__ == "__main__":
    check_db()
