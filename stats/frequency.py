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

def get_phrase_metrics(phrase, where_clause="1=1", params=(), skip_punct=True):
    """
    Returns metrics (Frequency, PMW, Zipf) for a multi-word phrase.
    """
    conn, is_shared = get_connection()
    parts = phrase.split()
    
    # Total tokens (N)
    res = safe_execute(conn, f"SELECT COUNT(*) FROM tokens WHERE {where_clause}", params).fetchone()
    total_tokens = res[0] if res else 0
    if total_tokens == 0:
        if not is_shared: conn.close()
        return {'frequency': 0, 'pmw': 0, 'zipf': 0}

    # Construct Phrase Query
    joins = []
    conditions = []
    q_params = []
    
    # Base match on t0
    
    for i, p in enumerate(parts):
        alias = f"t{i}"
        conditions.append(f"{alias}.token ILIKE ?")
        q_params.append(p)
        
        if i > 0:
            prev = f"t{i-1}"
            if skip_punct:
                # Flexible join: Next word follows previous word (id > prev), 
                # but distance is small (<= 4 to allow 3 punct marks max),
                # AND no other words in between (handled by ensuring continuity of valid tokens? 
                # actually, 'tokens' contains punctuation. 
                # So we just say: t(i) > t(i-1) AND NOT EXISTS (token between them matching alphanumeric regex)
                # But 'NOT EXISTS' in a JOIN can be tricky or slow.
                # A simpler heuristic for "phrase with punctuation" is max distance.
                # E.g. "central, bank" -> dist 2. "central - bank" -> dist 2.
                # "central ... bank" -> if ... is punct, ok.
                # Let's use a max window of 4 tokens.
                joins.append(f"JOIN tokens {alias} ON {alias}.file_id = {prev}.file_id AND {alias}.id > {prev}.id AND {alias}.id <= {prev}.id + 4")
                
                # Check for intervening alphanumeric?
                # Using a WHERE clause on the whole result?
                # "AND NOT EXISTS (SELECT 1 FROM tokens x WHERE x.file_id = t0.file_id AND x.id > t{i-1}.id AND x.id < t{i}.id AND regexp_matches(x.token, '[a-zA-Z0-9]'))"
                # This ensures only punctuation is between them.
            else:
                joins.append(f"JOIN tokens {alias} ON {prev}.id + 1 = {alias}.id AND {prev}.file_id = {alias}.file_id")
    
    join_clause = " ".join(joins)
    cond_clause = " AND ".join(conditions)
    
    query = f"""
        WITH start_tokens AS (
            SELECT id, file_id 
            FROM tokens 
            WHERE token ILIKE ? AND {where_clause}
        )
        SELECT COUNT(*)
        FROM start_tokens t0
        {join_clause}
    """
    
    remaining_conditions = " AND ".join(conditions[1:])
    if remaining_conditions:
        query += f" WHERE {remaining_conditions}"
        
    full_params = (parts[0], *params, *q_params[1:])

    # If parsing with strict punct skipping, we need to enforce that too.
    # The pure 'joins' approach above with dist check is loose.
    # We can add the enforcement as an additional WHERE clause if skip_punct is True.
    if skip_punct and len(parts) > 1:
        # Construct checks for each gap
        gap_checks = []
        for i in range(1, len(parts)):
            prev = f"t{i-1}"
            curr = f"t{i}"
            # Ensure no alphanumeric tokens between prev and curr
            gap_checks.append(f"""
                NOT EXISTS (
                    SELECT 1 FROM tokens GAP_{i} 
                    WHERE GAP_{i}.file_id = t0.file_id 
                    AND GAP_{i}.id > {prev}.id 
                    AND GAP_{i}.id < {curr}.id 
                    AND regexp_matches(GAP_{i}.token, '[a-zA-Z0-9]')
                )
            """)
        query += " AND " + " AND ".join(gap_checks)
    
    count_res = safe_execute(conn, query, full_params).fetchone()
    count = count_res[0] if count_res else 0
    
    pmw = (count / total_tokens) * 1000000
    
    if pmw > 1000: band = 5
    elif pmw > 100: band = 4
    elif pmw > 10: band = 3
    elif pmw > 1: band = 2
    else: band = 1
    
    if not is_shared: conn.close()
    
    return {
        'frequency': count,
        'pmw': float(f"{pmw:.2f}"),
        'zipf': band,
        'total_subset': total_tokens,
        'is_phrase': True
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
