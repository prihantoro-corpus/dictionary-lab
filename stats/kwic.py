from pipeline.indexing import get_connection, safe_execute

def get_kwic_lines(token, window=7, limit=50, where_clause="1=1", params=()):
    """
    Returns list of dicts: {left, node, right, metadata}
    """
    conn, is_shared = get_connection()
    
    # 1. Find IDs of the token matching filters
    matches = safe_execute(conn, f"""
        SELECT id, file_id 
        FROM tokens 
        WHERE token ILIKE ? AND {where_clause} 
        ORDER BY id
        LIMIT ?
    """, (token, *params, limit)).fetchall()
    
    results = []
    
    for match_id, file_id in matches:
        # 2. For each match, get window
        start_id = match_id - window
        end_id = match_id + window
        
        window_tokens = safe_execute(conn, """
            SELECT token, id, file_id
            FROM tokens 
            WHERE id BETWEEN ? AND ? AND file_id = ?
            ORDER BY id
        """, (start_id, end_id, file_id)).fetchall()
        
        # Assemble
        left = []
        node = ""
        right = []
        
        for t, tid, tfid in window_tokens:
            if tid == match_id:
                node = t
            elif tid < match_id:
                left.append(t)
            elif tid > match_id:
                right.append(t)
                
        results.append({
            'left': " ".join(left),
            'node': node,
            'right': " ".join(right),
        })
        
    if not is_shared:
        conn.close()
    return results

def get_collocate_kwic(token, collocate, window=7, limit=5, where_clause="1=1", params=()):
    """
    Returns KWIC lines where BOTH token and collocate appear in the window.
    """
    conn, is_shared = get_connection()
    
    # Search for pairs - use subquery for t1 to avoid ambiguous columns in where_clause
    query = f"""
        SELECT t1.id, t1.file_id, t2.id as col_id
        FROM (SELECT id, file_id, token FROM tokens WHERE {where_clause}) t1
        JOIN tokens t2 ON t1.file_id = t2.file_id AND t2.id BETWEEN t1.id - ? AND t1.id + ? AND t1.id != t2.id
        WHERE t1.token ILIKE ? AND t2.token ILIKE ?
        ORDER BY t1.id
        LIMIT ?
    """
    matches = safe_execute(conn, query, (*params, window, window, token, collocate, limit)).fetchall()
    
    results = []
    for match_id, file_id, col_id in matches:
        start = match_id - window
        end = match_id + window
        
        tokens = safe_execute(conn, """
            SELECT id, token FROM tokens 
            WHERE file_id = ? AND id BETWEEN ? AND ?
            ORDER BY id
        """, (file_id, start, end)).fetchall()
        
        left = []
        node = ""
        right = []
        
        for tid, t in tokens:
            if tid == match_id:
                node = t
            if tid < match_id:
                left.append(t)
            elif tid > match_id:
                right.append(t)
                
        results.append({
            'left': left,
            'node': node,
            'right': right,
            'col_id': col_id,
            'match_id': match_id,
            'file_id': file_id,
            'col_token': collocate
        })
        
    if not is_shared:
        conn.close()
    return results
