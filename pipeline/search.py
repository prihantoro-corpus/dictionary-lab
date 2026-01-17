import duckdb
from pipeline.indexing import get_connection
import Levenshtein

def autocomplete(prefix, limit=10):
    conn = get_connection()
    # optimized prefix search
    query = "SELECT DISTINCT token FROM tokens WHERE token ILIKE ? LIMIT ?"
    res = conn.execute(query, (f"{prefix}%", limit)).fetchall()
    conn.close()
    return [r[0] for r in res]

def search_exact(token):
    conn = get_connection()
    # Return dataframe of all entries
    query = "SELECT * FROM tokens WHERE token = ?"
    df = conn.execute(query, (token,)).fetchdf()
    conn.close()
    return df

def search_fuzzy(token, limit=5):
    conn = get_connection()
    # Get all unique tokens (expensive if large, maybe limit?)
    # For MVP: Select distinct tokens
    all_tokens_res = conn.execute("SELECT DISTINCT token FROM tokens").fetchall()
    all_tokens = [r[0] for r in all_tokens_res]
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
    conn = get_connection()
    res = conn.execute("""
        SELECT lemma, COUNT(*) as c 
        FROM tokens 
        WHERE token = ? 
        GROUP BY lemma 
        ORDER BY c DESC 
        LIMIT 1
    """, (token,)).fetchone()
    conn.close()
    return res[0] if res else token

def get_forms_by_lemma(lemma):
    """Returns all tokens that share this lemma."""
    conn = get_connection()
    res = conn.execute("SELECT DISTINCT token FROM tokens WHERE lemma = ?", (lemma,)).fetchall()
    conn.close()
    return [r[0] for r in res]

def get_pos_tags(token):
    """Returns all unique POS tags for this token."""
    conn = get_connection()
    res = conn.execute("SELECT DISTINCT tag FROM tokens WHERE token = ?", (token,)).fetchall()
    conn.close()
    return [r[0] for r in res]
