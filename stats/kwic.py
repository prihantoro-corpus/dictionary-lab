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
