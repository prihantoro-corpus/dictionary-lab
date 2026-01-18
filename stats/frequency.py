from pipeline.indexing import get_connection, safe_execute

def get_total_tokens(where_clause="1=1", params=()):
    conn, is_shared = get_connection()
    res = safe_execute(conn, f"SELECT COUNT(*) FROM tokens WHERE {where_clause}", params).fetchone()
    if not is_shared:
        conn.close()
    return res[0] if res else 0

def get_metrics(token, where_clause="1=1", params=()):
    """
    Returns dict with frequency, pmw, and zipf band.
    """
    conn, is_shared = get_connection()
    
    # Total tokens in current subset
    result = safe_execute(conn, f"SELECT COUNT(*) FROM tokens WHERE {where_clause}", params).fetchone()
    total_tokens = result[0] if result else 0
    if total_tokens == 0:
        if not is_shared:
            conn.close()
        return {'frequency': 0, 'pmw': 0, 'zipf': 0}
        
    # Frequency of specific token (case-insensitive for dictionary overview)
    try:
        with open("debug_queries.log", "a", encoding="utf-8") as f:
            f.write(f"FREQ: token='{token}', where='{where_clause}', params={params}\n")
    except:
        pass
    result = safe_execute(conn, f"SELECT COUNT(*) FROM tokens WHERE token ILIKE ? AND {where_clause}", (token, *params)).fetchone()
    count = result[0] if result else 0
    
    pmw = (count / total_tokens) * 1000000
    
    if pmw > 1000: band = 5
    elif pmw > 100: band = 4
    elif pmw > 10: band = 3
    elif pmw > 1: band = 2
    else: band = 1
    
    if not is_shared:
        conn.close()
    return {
        'frequency': count,
        'pmw': float(f"{pmw:.2f}"),
        'zipf': band,
        'total_subset': total_tokens
    }
