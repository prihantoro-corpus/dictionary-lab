from pipeline.indexing import get_connection, safe_execute
import Levenshtein

def autocomplete(prefix, where_clause="1=1", params=(), limit=10):
    conn, is_shared = get_connection()
    query = f"SELECT DISTINCT token FROM tokens WHERE token ILIKE ? AND {where_clause} LIMIT ?"
    res = safe_execute(conn, query, (f"{prefix}%", *params, limit)).fetchall()
    if not is_shared:
        conn.close()
    return [r[0] for r in res]

def search_exact(token, where_clause="1=1", params=()):
    conn, is_shared = get_connection()
    query = f"SELECT * FROM tokens WHERE token ILIKE ? AND {where_clause}"
    df = safe_execute(conn, query, (token, *params)).fetchdf()
    if not is_shared:
        conn.close()
    return df

def search_fuzzy(token, limit=5):
    conn, is_shared = get_connection()
    all_tokens_res = safe_execute(conn, "SELECT DISTINCT token FROM tokens").fetchall()
    all_tokens = [r[0] for r in all_tokens_res]
    if not is_shared:
        conn.close()
    
    # Calculate distance
    # Filter close matches
    matches = []
    for t in all_tokens:
        dist = Levenshtein.distance(token.lower(), t.lower())
        if dist <= 2 and dist > 0: # 0 is exact
            matches.append((t, dist))
            
    matches.sort(key=lambda x: x[1])
    return [m[0] for m in matches[:limit]]

def get_lemma(token):
    """Returns the most frequent lemma for this token."""
    conn, is_shared = get_connection()
    res = safe_execute(conn, """
        SELECT lemma, COUNT(*) as c 
        FROM tokens 
        WHERE token ILIKE ? 
        GROUP BY lemma 
        ORDER BY c DESC 
        LIMIT 1
    """, (token,)).fetchone()
    if not is_shared:
        conn.close()
    return res[0] if res else token

def get_forms_by_lemma(lemma):
    """Returns all tokens that share this lemma."""
    conn, is_shared = get_connection()
    res = safe_execute(conn, "SELECT DISTINCT token FROM tokens WHERE lemma = ?", (lemma,)).fetchall()
    if not is_shared:
        conn.close()
    return [r[0] for r in res]

def get_pos_tags(token):
    """Returns all unique POS tags for this token."""
    conn, is_shared = get_connection()
    res = safe_execute(conn, "SELECT DISTINCT tag FROM tokens WHERE token ILIKE ?", (token,)).fetchall()
    if not is_shared:
        conn.close()
    return [r[0] for r in res]

def get_related_words(token, limit=20):
    """Returns tokens containing the search token as a substring (infix), excluding the token itself."""
    conn, is_shared = get_connection()
    query = "SELECT DISTINCT token FROM tokens WHERE token ILIKE ? AND token NOT ILIKE ? LIMIT ?"
    res = safe_execute(conn, query, (f"%{token}%", token, limit)).fetchall()
    if not is_shared:
        conn.close()
    return [r[0] for r in res]

def get_corpus_stats(where_clause="1=1", params=()):
    """Returns basic stats for the Entry tab."""
    conn, is_shared = get_connection()
    
    stats = {}
    
    # Total Token Count
    res = safe_execute(conn, f"SELECT COUNT(*) FROM tokens WHERE {where_clause}", params).fetchone()
    stats['total_tokens'] = res[0] if res else 0
    
    # Total Lemma Count
    res = safe_execute(conn, f"SELECT COUNT(DISTINCT lemma) FROM tokens WHERE {where_clause}", params).fetchone()
    stats['total_lemmas'] = res[0] if res else 0
    
    # List of POS Tags
    res = safe_execute(conn, f"SELECT DISTINCT tag FROM tokens WHERE {where_clause} ORDER BY tag", params).fetchall()
    stats['pos_tags'] = [r[0] for r in res if r[0]]
    
    if not is_shared:
        conn.close()
    return stats

def get_full_frequency_list(where_clause="1=1", params=()):
    """Returns a DataFrame of all tokens and their frequencies."""
    conn, is_shared = get_connection()
    df = safe_execute(conn, f"""
        SELECT token, COUNT(*) as freq 
        FROM tokens 
        WHERE {where_clause}
        GROUP BY token 
        ORDER BY freq DESC
    """, params).fetchdf()
    
    if not is_shared:
        conn.close()
    return df
