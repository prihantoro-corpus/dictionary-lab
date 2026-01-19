from pipeline.indexing import get_connection, safe_execute

def debug_counts(token):
    # Try connecting in read-only mode to avoid locking issues
    conn, _ = get_connection(read_only=True)
    
    print(f"--- Debugging '{token}' ---")
    
    # 1. Total Count (ILIKE)
    total = safe_execute(conn, "SELECT COUNT(*) FROM tokens WHERE token ILIKE ?", (token,)).fetchone()[0]
    print(f"Total (ILIKE): {total}")
    
    # 2. Breakdown by Tag
    rows = safe_execute(conn, "SELECT tag, COUNT(*) FROM tokens WHERE token ILIKE ? GROUP BY tag", (token,)).fetchall()
    print("\nBreakdown by Tag:")
    for tag, count in rows:
        print(f"Tag: '{tag}' -> Count: {count}")
        
    conn.close()

if __name__ == "__main__":
    debug_counts("bank")
