import duckdb
import os

DB_PATH = "dictionary.duckdb"

def check_lock():
    print(f"Checking for lock on {DB_PATH}...")
    if not os.path.exists(DB_PATH):
        print("Database file does not exist.")
        return

    # Try Read-Only
    try:
        conn_ro = duckdb.connect(DB_PATH, read_only=True)
        print("SUCCESS: Read-Only connection established.")
        conn_ro.close()
    except Exception as e:
        print(f"FAILURE: Read-Only connection failed: {e}")

    # Try Read-Write
    try:
        conn_rw = duckdb.connect(DB_PATH, read_only=False)
        print("SUCCESS: Read-Write connection established.")
        conn_rw.close()
    except Exception as e:
        print(f"FAILURE: Read-Write connection failed: {e}")

if __name__ == "__main__":
    check_lock()
