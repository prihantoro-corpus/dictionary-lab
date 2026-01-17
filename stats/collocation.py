import duckdb
import math
from pipeline.indexing import get_connection

def get_ngrams(token, n=2, limit=10, where_clause="1=1", params=()):
    """
    Returns top N-grams containing the token.
    Direction: Forward and Backward? 
    User req: "word search_word", "search_word word".
    """
    conn = get_connection()
    
    # We can use window functions to generate n-grams on the fly or joining.
    # Generating on fly might be slow if scanning whole table.
    # Better to filter by token first then look around.
    
    # Simple approach: Find token ID, get adjacent words.
    
    results = {}
    
    # Bigrams: Forward (SearchWord + Word)
    fw = conn.execute(f"""
        WITH matches AS (
            SELECT id, file_id FROM tokens WHERE token = ? AND {where_clause}
        ),
        next_tokens AS (
            SELECT t1.token as w1, t2.token as w2
            FROM matches m
            JOIN tokens t1 ON m.id = t1.id
            JOIN tokens t2 ON m.id + 1 = t2.id AND t1.file_id = t2.file_id
        )
        SELECT w1 || ' ' || w2 as bigram, COUNT(*) as freq
        FROM next_tokens
        GROUP BY bigram
        ORDER BY freq DESC
        LIMIT ?
    """, (token, *params, limit)).fetchall()
    
    results['forward_bigrams'] = fw
    
    # Bigrams: Backward (Word + SearchWord)
    bw = conn.execute(f"""
        WITH matches AS (
            SELECT id, file_id FROM tokens WHERE token = ? AND {where_clause}
        ),
        prev_tokens AS (
            SELECT t0.token as w0, t1.token as w1
            FROM matches m
            JOIN tokens t1 ON m.id = t1.id
            JOIN tokens t0 ON m.id - 1 = t0.id AND t1.file_id = t0.file_id
        )
        SELECT w0 || ' ' || w1 as bigram, COUNT(*) as freq
        FROM prev_tokens
        GROUP BY bigram
        ORDER BY freq DESC
        LIMIT ?
    """, (token, *params, limit)).fetchall()
    
    results['backward_bigrams'] = bw
    
    # TODO: Trigrams (similar pattern)
    
    conn.close()
    return results

def get_collocates(token, window=5, limit=20, where_clause="1=1", params=()):
    """
    Calculates top collocates using Log-Likelihood.
    """
    conn = get_connection()
    
    # 1. Total tokens (N)
    N = conn.execute(f"SELECT COUNT(*) FROM tokens WHERE {where_clause}", params).fetchone()[0]
    
    if N == 0: return []

    # 2. Count of Node (NodeFreq)
    node_freq = conn.execute(f"SELECT COUNT(*) FROM tokens WHERE token = ? AND {where_clause}", (token, *params)).fetchone()[0]
    
    # 3. Find co-occurrences (O11)
    # This is expensive. Optimize by filtering only relevant IDs.
    
    # Get IDs of node
    # Then range join?
    # Or self-join: t1=node, t2=collocate, abs(t1.id - t2.id) <= window
    
    collocan_counts = conn.execute(f"""
        WITH node_ids AS (
            SELECT id, file_id FROM tokens WHERE token = ? AND {where_clause}
        )
        SELECT t2.token, COUNT(*) as O11
        FROM node_ids n
        JOIN tokens t2 ON t2.file_id = n.file_id 
            AND t2.id BETWEEN n.id - ? AND n.id + ?
            AND t2.id != n.id
        WHERE {where_clause}
        GROUP BY t2.token
        ORDER BY O11 DESC
        LIMIT 100 
    """, (token, *params, window, window, *params)).fetchall()
    
    results = []
    for collocate, O11 in collocan_counts:
        # 4. Count of Collocate (ColFreq)
        col_freq = conn.execute(f"SELECT COUNT(*) FROM tokens WHERE token = ? AND {where_clause}", (collocate, *params)).fetchone()[0]
        
        # Log-Likelihood Calc
        # E11 = (NodeFreq * ColFreq) / N
        try:
            E11 = (node_freq * col_freq) / N
            if E11 == 0: continue
            
            # Simple LL formula (Dunning): 2 * (O11 * ln(O11/E11)) ... (simplified, needs 4 cells for accuracy)
            # Full formula:
            # L = 2 * (O11 * log(O11/E11) + O12 * log(O12/E12) + O21 * log(O21/E21) + O22 * log(O22/E22))
            
            # For efficiency/simplicity here, keeping it basic or use a library if available.
            # Let's approximate roughly or just return Frequency + MI?
            # User specifically asked for Log-Likelihood.
            
            def safe_x_log_x_y(x, y):
                if x == 0 or y == 0: return 0
                return x * math.log(x / y)

            O12 = node_freq - O11
            O21 = col_freq - O11
            O22 = N - (node_freq + col_freq - O11) # approx N
            
            E12 = (node_freq * (N - col_freq)) / N
            E21 = ((N - node_freq) * col_freq) / N
            E22 = ((N - node_freq) * (N - col_freq)) / N
            
            LL = 2 * (safe_x_log_x_y(O11, E11) + 
                      safe_x_log_x_y(O12, E12) + 
                      safe_x_log_x_y(O21, E21) + 
                      safe_x_log_x_y(O22, E22))
            
            results.append({
                'collocate': collocate,
                'freq': O11,
                'score': LL
            })
        except:
            continue
            
    # Sort by Score
    results.sort(key=lambda x: x['score'], reverse=True)
    conn.close()
    return results[:limit]
