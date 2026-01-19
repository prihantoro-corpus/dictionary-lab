from pipeline.indexing import get_connection, safe_execute

def get_total_tokens(where_clause="1=1", params=()):
    conn, is_shared = get_connection()
    res = safe_execute(conn, f"SELECT COUNT(*) FROM tokens WHERE {where_clause}", params).fetchone()
    if not is_shared:
        conn.close()
    return res[0] if res else 0

def get_metrics(token, where_clause="1=1", params=(), pos_tag=None):
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
            f.write(f"FREQ: token='{token}', tag='{pos_tag}', where='{where_clause}', params={params}\n")
    except:
        pass
    
    if pos_tag:
        query = f"SELECT COUNT(*) FROM tokens WHERE token ILIKE ? AND tag = ? AND {where_clause}"
        query_params = (token, pos_tag, *params)
    else:
        query = f"SELECT COUNT(*) FROM tokens WHERE token ILIKE ? AND {where_clause}"
        query_params = (token, *params)
        
    result = safe_execute(conn, query, query_params).fetchone()
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

def get_max_frequency(where_clause="1=1", params=()):
    """Returns the count of the most frequent token in the filtered corpus."""
    conn, is_shared = get_connection()
    # Find max frequency
    query = f"""
        SELECT COUNT(*) as cnt 
        FROM tokens 
        WHERE {where_clause} 
        GROUP BY token 
        ORDER BY cnt DESC 
        LIMIT 1
    """
    res = safe_execute(conn, query, params).fetchone()
    if not is_shared:
        conn.close()
    return res[0] if res else 1  # Avoid div by zero

def get_pmw_range(where_clause="1=1", params=()):
    """Returns the min and max PMW values in the filtered corpus."""
    conn, is_shared = get_connection()
    
    # Get total tokens for PMW calculation
    result = safe_execute(conn, f"SELECT COUNT(*) FROM tokens WHERE {where_clause}", params).fetchone()
    total_tokens = result[0] if result else 0
    
    if total_tokens == 0:
        if not is_shared:
            conn.close()
        return {'min_pmw': 0, 'max_pmw': 0}
    
    # Get max frequency token
    query_max = f"""
        SELECT COUNT(*) as cnt 
        FROM tokens 
        WHERE {where_clause} 
        GROUP BY token 
        ORDER BY cnt DESC 
        LIMIT 1
    """
    res_max = safe_execute(conn, query_max, params).fetchone()
    max_freq = res_max[0] if res_max else 0
    
    # Get min frequency token (minimum should be 1 if token exists)
    query_min = f"""
        SELECT COUNT(*) as cnt 
        FROM tokens 
        WHERE {where_clause} 
        GROUP BY token 
        ORDER BY cnt ASC 
        LIMIT 1
    """
    res_min = safe_execute(conn, query_min, params).fetchone()
    min_freq = res_min[0] if res_min else 1
    
    if not is_shared:
        conn.close()
    
    max_pmw = (max_freq / total_tokens) * 1000000
    min_pmw = (min_freq / total_tokens) * 1000000
    
    return {
        'min_pmw': float(f"{min_pmw:.2f}"),
        'max_pmw': float(f"{max_pmw:.2f}")
    }
