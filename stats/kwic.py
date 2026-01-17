from pipeline.indexing import get_connection

def get_kwic_lines(token, window=7, limit=50, where_clause="1=1", params=()):
    """
    Returns list of dicts: {left, node, right, metadata}
    """
    conn = get_connection()
    
    # 1. Find IDs of the token matching filters
    matches = conn.execute(f"""
        SELECT id, file_id 
        FROM tokens 
        WHERE token = ? AND {where_clause} 
        LIMIT ?
    """, (token, *params, limit)).fetchall()
    
    results = []
    
    for match_id, file_id in matches:
        # 2. For each match, get window
        # Ensure we stay within same file!
        start_id = match_id - window
        end_id = match_id + window
        
        window_tokens = conn.execute("""
            SELECT token, id, file_id
            FROM tokens 
            WHERE id BETWEEN ? AND ? AND file_id = ?
            ORDER BY id
        """, (start_id, end_id, file_id)).fetchall()
        
        # Assemble
        left = []
        node = token
        right = []
        
        for t, tid, tfid in window_tokens:
            if tid < match_id:
                left.append(t)
            elif tid > match_id:
                right.append(t)
                
        results.append({
            'left': " ".join(left),
            'node': node,
            'right': " ".join(right),
            # 'metadata': ... fetch distinct metadata for this line? 
            # ideally metadata is same for the whole sentence/segment.
        })
        
    conn.close()
    return results

def get_collocate_kwic(token, collocate, window=7, limit=5, where_clause="1=1", params=()):
    """
    Returns KWIC lines where BOTH token and collocate appear in the window.
    """
    conn = get_connection()
    
    # Search for pairs
    query = f"""
        SELECT t1.id, t1.file_id, t2.id as col_id
        FROM tokens t1
        JOIN tokens t2 ON t1.file_id = t2.file_id AND t2.id BETWEEN t1.id - ? AND t1.id + ? AND t1.id != t2.id
        WHERE t1.token = ? AND t2.token = ? AND {where_clause}
        LIMIT ?
    """
    matches = conn.execute(query, (window, window, token, collocate, *params, limit)).fetchall()
    
    results = []
    for match_id, file_id, col_id in matches:
        # Context window around the primary match_id
        start = match_id - window
        end = match_id + window
        
        tokens = conn.execute("""
            SELECT id, token FROM tokens 
            WHERE file_id = ? AND id BETWEEN ? AND ?
            ORDER BY id
        """, (file_id, start, end)).fetchall()
        
        left = []
        node = ""
        right = []
        
        found_node = False
        for tid, t in tokens:
            if tid == match_id:
                node = t
                found_node = True
            elif tid == col_id:
                # Mark collocate for highlighting if needed, 
                # but KWIC standard is usually just highlighting the node.
                # User asked to highlight BOTH. 
                # We can wrap in special marker or just return the IDs.
                # Let's return as a list of tokens/is_highlight dicts? 
                # For simplicity in current UI: return raw strings and let UI handle?
                # Actually KWIC UI uses left/node/right.
                # We can't easily highlight with left/node/right.
                # Let's add a "marked_tokens" list.
                pass
            
            if tid < match_id:
                left.append(t)
            elif tid > match_id:
                right.append(t)
                
        results.append({
            'left': left, # List for easier highlighting
            'node': node,
            'right': right,
            'col_id': col_id, # Absolute ID of collocate in this window
            'match_id': match_id,
            'file_id': file_id,
            'col_token': collocate
        })
        
    conn.close()
    return results
