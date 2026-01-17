import duckdb
from .indexing import get_connection

def autocomplete(query, limit=10):
    """Returns a list of suggested tokens based on prefix."""
    conn = get_connection()
    # ILIKE for case-insensitive
    # Group by token to avoid duplicates in suggestion
    query_str = f"{query}%"
    results = conn.execute("""
        SELECT DISTINCT token 
        FROM tokens 
        WHERE token ILIKE ? 
        LIMIT ?
    """, (query_str, limit)).fetchall()
    conn.close()
    return [r[0] for r in results]

def search_exact(query):
    """Returns all occurrences of a token exactly matching the query."""
    conn = get_connection()
    results = conn.execute("""
        SELECT * 
        FROM tokens 
        WHERE token = ?
    """, (query,)).fetchall()
    # Convert to list of dicts ? Or dataframe? 
    # For now, return raw rows, handling in app logic likely better with DF
    df = conn.execute("""
        SELECT * 
        FROM tokens 
        WHERE token = ?
    """, (query,)).df()
    conn.close()
    return df

def search_fuzzy(query, limit=50):
    """Returns tokens similar to the query using Levenshtein distance."""
    conn = get_connection()
    # DuckDB has levenshtein function
    results = conn.execute("""
        SELECT DISTINCT token, levenshtein(token, ?) as dist
        FROM tokens 
        WHERE dist < 3
        ORDER BY dist ASC
        LIMIT ?
    """, (query, limit)).fetchall()
    conn.close()
    return [r[0] for r in results]
