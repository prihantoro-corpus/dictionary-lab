from pipeline.indexing import get_connection, safe_execute

def get_kwic_lines(token, window=7, limit=50, where_clause="1=1", params=(), pos_tag=None):
    """
    Returns list of dicts: {left, node, right, metadata}
    """
    conn, is_shared = get_connection()
    
    # 1. Find IDs of the token matching filters
    if pos_tag:
        matches = safe_execute(conn, f"""
            SELECT id, file_id 
            FROM tokens 
            WHERE token ILIKE ? AND tag = ? AND {where_clause} 
            ORDER BY id
            LIMIT ?
        """, (token, pos_tag, *params, limit)).fetchall()
    else:
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

def get_phrase_kwic_lines(phrase, window=7, limit=50, where_clause="1=1", params=(), skip_punct=True):
    """
    Returns KWIC lines for a multi-word phrase.
    """
    conn, is_shared = get_connection()
    parts = phrase.split()
    length = len(parts)

    # Re-use CTE join pattern
    joins = []
    conditions = []
    q_params = []
    
    for i, p in enumerate(parts):
        alias = f"t{i}"
        conditions.append(f"{alias}.token ILIKE ?")
        q_params.append(p)
        if i > 0:
            prev = f"t{i-1}"
            if skip_punct:
                # Flexible window + negation check
                joins.append(f"JOIN tokens {alias} ON {alias}.file_id = {prev}.file_id AND {alias}.id > {prev}.id AND {alias}.id <= {prev}.id + 4")
            else:
                joins.append(f"JOIN tokens {alias} ON {prev}.id + 1 = {alias}.id AND {prev}.file_id = {alias}.file_id")

    # Extra WHERE for skip_punct gap checks
    gap_checks = ""
    if skip_punct and len(parts) > 1:
        checks = []
        for i in range(1, len(parts)):
            prev = f"t{i-1}"
            curr = f"t{i}"
            checks.append(f"""
                NOT EXISTS (
                    SELECT 1 FROM tokens GAP_{i} 
                    WHERE GAP_{i}.file_id = t0.file_id 
                    AND GAP_{i}.id > {prev}.id 
                    AND GAP_{i}.id < {curr}.id 
                    AND regexp_matches(GAP_{i}.token, '[a-zA-Z0-9]')
                )
            """)
        gap_checks = " AND " + " AND ".join(checks)

    query = f"""
        WITH start_tokens AS (
            SELECT id, file_id 
            FROM tokens 
            WHERE token ILIKE ? AND {where_clause}
        )
        SELECT t0.id, t0.file_id, t{length-1}.id as final_id
        FROM start_tokens t0
        {" ".join(joins)}
    """
    remaining = " AND ".join(conditions[1:])
    if remaining:
        query += f" WHERE {remaining}"
    else:
        query += " WHERE 1=1"
        
    query += gap_checks
    query += f" ORDER BY t0.id LIMIT ?"
    full_params = (parts[0], *params, *q_params[1:], limit)
    
    matches = safe_execute(conn, query, full_params).fetchall()
    
    results = []
    for match_id, file_id, final_id in matches:
        seq_start = match_id
        seq_end = final_id
        
        win_start = seq_start - window
        win_end = seq_end + window
        
        tokens = safe_execute(conn, """
            SELECT token, id 
            FROM tokens 
            WHERE file_id = ? AND id BETWEEN ? AND ? 
            ORDER BY id
        """, (file_id, win_start, win_end)).fetchall()
        
        left, node, right = [], [], []
        for t, tid in tokens:
            if tid < seq_start:
                left.append(t)
            elif tid > seq_end:
                right.append(t)
            else:
                node.append(t)
        
        results.append({
            'left': " ".join(left),
            'node': " ".join(node),
            'right': " ".join(right)
        })

    if not is_shared: conn.close()
    return results

def get_collocate_kwic(token, collocate, window=7, limit=5, where_clause="1=1", params=(), pos_tag=None):
    """
    Returns KWIC lines where BOTH token and collocate appear in the window.
    """
    conn, is_shared = get_connection()
    
    # Search for pairs - use subquery for t1 to avoid ambiguous columns in where_clause
    if pos_tag:
         query = f"""
            SELECT t1.id, t1.file_id, t2.id as col_id
            FROM (SELECT id, file_id, token, tag FROM tokens WHERE {where_clause}) t1
            JOIN tokens t2 ON t1.file_id = t2.file_id AND t2.id BETWEEN t1.id - ? AND t1.id + ? AND t1.id != t2.id
            WHERE t1.token ILIKE ? AND t1.tag = ? AND t2.token ILIKE ?
            ORDER BY t1.id
            LIMIT ?
        """
         matches = safe_execute(conn, query, (*params, window, window, token, pos_tag, collocate, limit)).fetchall()
    else:
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

def get_phrase_collocate_kwic(phrase, collocate, window=7, limit=5, where_clause="1=1", params=(), skip_punct=True):
    """
    Returns KWIC lines where BOTH phrase and collocate appear in the window.
    """
    conn, is_shared = get_connection()
    parts = phrase.split()
    length = len(parts)

    # Re-use CTE join pattern
    joins = []
    conditions = []
    q_params = []
    
    for i, p in enumerate(parts):
        alias = f"t{i}"
        conditions.append(f"{alias}.token ILIKE ?")
        q_params.append(p)
        if i > 0:
            prev = f"t{i-1}"
            if skip_punct:
                joins.append(f"JOIN tokens {alias} ON {alias}.file_id = {prev}.file_id AND {alias}.id > {prev}.id AND {alias}.id <= {prev}.id + 4")
            else:
                joins.append(f"JOIN tokens {alias} ON {prev}.id + 1 = {alias}.id AND {prev}.file_id = {alias}.file_id")

    # Extra WHERE for skip_punct gap checks
    gap_checks = ""
    if skip_punct and len(parts) > 1:
        checks = []
        for i in range(1, len(parts)):
            prev = f"t{i-1}"
            curr = f"t{i}"
            checks.append(f"""
                NOT EXISTS (
                    SELECT 1 FROM tokens GAP_{i} 
                    WHERE GAP_{i}.file_id = t0.file_id 
                    AND GAP_{i}.id > {prev}.id 
                    AND GAP_{i}.id < {curr}.id 
                    AND regexp_matches(GAP_{i}.token, '[a-zA-Z0-9]')
                )
            """)
        gap_checks = " AND " + " AND ".join(checks)

    # We need to find occurrences where 'collocate' is within window of the phrase bounds
    # t0.id is start, t{length-1}.id is end.
    query = f"""
        WITH start_tokens AS (
            SELECT id, file_id 
            FROM tokens 
            WHERE token ILIKE ? AND {where_clause}
        ),
        matches AS (
            SELECT t0.id as start_id, t{length-1}.id as final_id, t0.file_id
            FROM start_tokens t0
            {" ".join(joins)}
            {"WHERE " + " AND ".join(conditions[1:]) if len(conditions) > 1 else "WHERE 1=1"}
            {gap_checks}
        )
        SELECT m.start_id, m.final_id, m.file_id, t2.id as col_id
        FROM matches m
        JOIN tokens t2 ON m.file_id = t2.file_id 
             AND t2.id BETWEEN m.start_id - ? AND m.final_id + ? 
             AND (t2.id < m.start_id OR t2.id > m.final_id)
        WHERE t2.token ILIKE ?
        ORDER BY m.start_id
        LIMIT ?
    """
    
    full_params = (parts[0], *params, *q_params[1:], window, window, collocate, limit)
    matches = safe_execute(conn, query, full_params).fetchall()
    
    results = []
    for seq_start, seq_end, file_id, col_id in matches:
        win_start = seq_start - window
        win_end = seq_end + window
        
        tokens = safe_execute(conn, """
            SELECT id, token FROM tokens 
            WHERE file_id = ? AND id BETWEEN ? AND ?
            ORDER BY id
        """, (file_id, win_start, win_end)).fetchall()
        
        left, node, right = [], [], []
        for tid, t in tokens:
            if tid < seq_start:
                left.append(t)
            elif tid > seq_end:
                right.append(t)
            else:
                node.append(t)
                
        results.append({
            'left': left,
            'node': " ".join(node),
            'right': right,
            'col_id': col_id,
            'match_id': seq_start,
            'file_id': file_id,
            'col_token': collocate
        })
        
    if not is_shared: conn.close()
    return results
