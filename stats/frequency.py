import duckdb
from pipeline.indexing import get_connection

def get_total_tokens(where_clause="1=1", params=()):
    conn = get_connection()
    res = conn.execute(f"SELECT COUNT(*) FROM tokens WHERE {where_clause}", params).fetchone()
    conn.close()
    return res[0] if res else 0

def get_metrics(token, where_clause="1=1", params=()):
    """
    Returns dict with frequency, pmw, and zipf band.
    """
    conn = get_connection()
    
    # Total tokens in current subset
    total_tokens = conn.execute(f"SELECT COUNT(*) FROM tokens WHERE {where_clause}", params).fetchone()[0]
    if total_tokens == 0:
        conn.close()
        return {'frequency': 0, 'pmw': 0, 'zipf': 0}
        
    # Frequency of specific token
    # We might need to filter by token AND the where_clause
    # Assumption: 'token' arg is the target word.
    count = conn.execute(f"SELECT COUNT(*) FROM tokens WHERE token = ? AND {where_clause}", (token, *params)).fetchone()[0]
    
    pmw = (count / total_tokens) * 1000000
    
    # Zipf Band Logic (Simplified)
    # Band 1: Top 1000
    # Band 2: 1001-3000
    # Band 3: 3001-5000
    # Band 4: 5001-10000
    # Band 5: >10000
    # Ranking is expensive to compute on fly for every word. 
    # Use cached rank or simpler heuristic based on PMW?
    # Let's use PMW thresholds for speed. 
    # Zipf 5 (Highest): > 1000 PMW ??? No Zipf usually 1 is high freq.
    # User said: "1-5 bars, if the zipf band is 3, only 3 of the 5 bars are lighted up"
    # Usually Band 5 = Most Frequent? Let's assume Band 5 is high freq.
    
    if pmw > 1000: band = 5
    elif pmw > 100: band = 4
    elif pmw > 10: band = 3
    elif pmw > 1: band = 2
    else: band = 1
    
    conn.close()
    return {
        'frequency': count,
        'pmw': float(f"{pmw:.2f}"),
        'zipf': band,
        'total_subset': total_tokens
    }
