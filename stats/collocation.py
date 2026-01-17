import duckdb
import math
from pipeline.indexing import get_connection

def get_ngrams(token, limit=10, where_clause="1=1", params=()):
    conn = get_connection()
    results = {}
    
    # Common CTE for matches
    cte_matches = f"matches AS (SELECT id, file_id FROM tokens WHERE token = ? AND {where_clause})"
    
    # 1. Bigram: Search + Word (Forward)
    results['bi_search_word'] = conn.execute(f"""
        WITH {cte_matches},
        next_tokens AS (
            SELECT t2.token as w2
            FROM matches m
            JOIN tokens t2 ON m.id + 1 = t2.id AND m.file_id = t2.file_id
        )
        SELECT ? || ' ' || w2, COUNT(*) as freq
        FROM next_tokens
        GROUP BY w2
        ORDER BY freq DESC LIMIT ?
    """, (token, token, limit)).fetchall()
    
    # 2. Bigram: Word + Search (Backward)
    results['bi_word_search'] = conn.execute(f"""
        WITH {cte_matches},
        prev_tokens AS (
            SELECT t0.token as w0
            FROM matches m
            JOIN tokens t0 ON m.id - 1 = t0.id AND m.file_id = t0.file_id
        )
        SELECT w0 || ' ' || ?, COUNT(*) as freq
        FROM prev_tokens
        GROUP BY w0
        ORDER BY freq DESC LIMIT ?
    """, (token, token, limit)).fetchall()
    
    # 3. Trigram: Search + Word + Word (s w w)
    results['tri_s_w_w'] = conn.execute(f"""
        WITH {cte_matches},
        next2 AS (
            SELECT t1.token as w1, t2.token as w2
            FROM matches m
            JOIN tokens t1 ON m.id + 1 = t1.id AND m.file_id = t1.file_id
            JOIN tokens t2 ON m.id + 2 = t2.id AND m.file_id = t2.file_id
        )
        SELECT ? || ' ' || w1 || ' ' || w2, COUNT(*) as freq
        FROM next2
        GROUP BY w1, w2
        ORDER BY freq DESC LIMIT ?
    """, (token, token, limit)).fetchall()
    
    # 4. Trigram: Word + Search + Word (w s w)
    results['tri_w_s_w'] = conn.execute(f"""
        WITH {cte_matches},
        surround AS (
            SELECT t0.token as w0, t2.token as w2
            FROM matches m
            JOIN tokens t0 ON m.id - 1 = t0.id AND m.file_id = t0.file_id
            JOIN tokens t2 ON m.id + 1 = t2.id AND m.file_id = t2.file_id
        )
        SELECT w0 || ' ' || ? || ' ' || w2, COUNT(*) as freq
        FROM surround
        GROUP BY w0, w2
        ORDER BY freq DESC LIMIT ?
    """, (token, token, limit)).fetchall()

    # 5. Trigram: Word + Word + Search (w w s)
    results['tri_w_w_s'] = conn.execute(f"""
        WITH {cte_matches},
        prev2 AS (
            SELECT t0.token as w0, t1.token as w1
            FROM matches m
            JOIN tokens t0 ON m.id - 2 = t0.id AND m.file_id = t0.file_id
            JOIN tokens t1 ON m.id - 1 = t1.id AND m.file_id = t1.file_id
        )
        SELECT w0 || ' ' || w1 || ' ' || ?, COUNT(*) as freq
        FROM prev2
        GROUP BY w0, w1
        ORDER BY freq DESC LIMIT ?
    """, (token, token, limit)).fetchall()
    
    conn.close()
    return results

def get_collocates(token, window=5, limit=20, where_clause="1=1", params=(), stop_words=None, allowed_words=None):
    conn = get_connection()
    if stop_words is None: stop_words = []
    if allowed_words is None: allowed_words = []
    
    # Prepare Filters
    # Allowed words: If present, only look for these.
    # Stop words: Exclude these.
    
    filter_sql = ""
    filter_params = []
    
    if allowed_words:
        # If allowed words list is huge, this is inefficient. Assuming user types a few.
        placeholders = ",".join(["?"] * len(allowed_words))
        filter_sql += f" AND t2.token IN ({placeholders})"
        filter_params.extend(allowed_words)
    
    if stop_words:
        placeholders = ",".join(["?"] * len(stop_words))
        filter_sql += f" AND t2.token NOT IN ({placeholders})"
        filter_params.extend(stop_words)

    N = conn.execute(f"SELECT COUNT(*) FROM tokens WHERE {where_clause}", params).fetchone()[0]
    if N == 0: return []
    
    node_freq = conn.execute(f"SELECT COUNT(*) FROM tokens WHERE token = ? AND {where_clause}", (token, *params)).fetchone()[0]
    if node_freq == 0: return []
    
    # Calculate Co-occurrences
    # Combining the node query and collocate filter
    collocan_counts = conn.execute(f"""
        WITH node_ids AS (
            SELECT id, file_id FROM tokens WHERE token = ? AND {where_clause}
        )
        SELECT t2.token, COUNT(*) as O11
        FROM node_ids n
        JOIN tokens t2 ON t2.file_id = n.file_id 
            AND t2.id BETWEEN n.id - ? AND n.id + ?
            AND t2.id != n.id
        WHERE {where_clause} {filter_sql}
        GROUP BY t2.token
        ORDER BY O11 DESC
        LIMIT 200 
    """, (token, *params, window, window, *params, *filter_params)).fetchall()
    
    results = []
    for collocate, O11 in collocan_counts:
        col_freq = conn.execute(f"SELECT COUNT(*) FROM tokens WHERE token = ? AND {where_clause}", (collocate, *params)).fetchone()[0]
        
        try:
            # Simple Log Likelihood approximation
            E11 = (node_freq * col_freq) / N
            if E11 == 0: continue
            
            def safe_x_log_x_y(x, y):
                if x == 0 or y == 0: return 0
                return x * math.log(x / y)
            
            O12 = node_freq - O11
            O21 = col_freq - O11
            O22 = N - (node_freq + col_freq - O11)
            
            E12 = (node_freq * (N - col_freq)) / N
            E21 = ((N - node_freq) * col_freq) / N
            E22 = ((N - node_freq) * (N - col_freq)) / N
            
            LL = 2 * (safe_x_log_x_y(O11, E11) + 
                      safe_x_log_x_y(O12, E12) + 
                      safe_x_log_x_y(O21, E21) + 
                      safe_x_log_x_y(O22, E22))
            
            results.append({'collocate': collocate, 'freq': O11, 'score': LL})
        except:
            continue
            
    results.sort(key=lambda x: x['score'], reverse=True)
    conn.close()
    return results[:limit]
