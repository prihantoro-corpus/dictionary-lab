import duckdb
import math
import re
from pipeline.indexing import get_connection

def parse_collocate_filter(filter_list, alias="t2"):
    """
    Parses a list of filter strings into SQL conditions.
    Returns: (sql_clause, params)
    """
    if not filter_list: return "", []
    
    includes = []
    excludes = []
    params = []
    
    for p in filter_list:
        p = p.strip()
        if not p: continue
        
        # POS Tag Inclusion (_JJ)
        if p.startswith('_'):
            tag = p[1:]
            includes.append(f"{alias}.tag = ?")
            params.append(tag)
            
        # POS Tag Exclusion (-JJ)
        elif p.startswith('-'):
            tag = p[1:]
            excludes.append(f"{alias}.tag = ?")
            params.append(tag)
            
        # Wildcards (car*)
        elif '*' in p:
            pattern = p.replace('*', '%')
            includes.append(f"{alias}.token ILIKE ?")
            params.append(pattern)
            
        # Regex or complex groups ((a|b))
        elif '(' in p and ')' in p:
             # DuckDB regex match
             includes.append(f"regexp_matches({alias}.token, ?)")
             params.append(p)
             
        # Exact match
        else:
            includes.append(f"{alias}.token = ?")
            params.append(p)
    
    # Build Logic
    clauses = []
    if includes:
        or_clause = " OR ".join(includes)
        clauses.append(f"({or_clause})")
        
    if excludes:
        for ex in excludes:
            clauses.append(f"NOT ({ex})")
            
    if not clauses: return "", []
    
    return " AND " + " AND ".join(clauses), params

def get_ngrams(token, limit=10, where_clause="1=1", params=(), stop_words=None, skip_punct=True):
    conn = get_connection()
    if stop_words is None: stop_words = []
    
    results = {}
    
    # Base CTE
    cte_matches = f"matches AS (SELECT id, file_id FROM tokens WHERE token = ? AND {where_clause})"
    
    # Filters for neighbors
    neighbor_filter = ""
    neighbor_params = []
    
    if skip_punct:
        # Simple punctuation check: Token must contain at least one alphanumeric char
        neighbor_filter += " AND regexp_matches(token, '[a-zA-Z0-9]')"
    
    if stop_words:
        placeholders = ",".join(["?"] * len(stop_words))
        neighbor_filter += f" AND token NOT IN ({placeholders})"
        neighbor_params.extend(stop_words)

    # Helper to apply filter to a specific alias
    def apply_filter(alias):
        return neighbor_filter.replace("token", f"{alias}.token")

    # 1. Bigram: Search + Word (Forward)
    results['bi_search_word'] = conn.execute(f"""
        WITH {cte_matches},
        next_tokens AS (
            SELECT t2.token as w2
            FROM matches m
            JOIN tokens t2 ON m.id + 1 = t2.id AND m.file_id = t2.file_id
            WHERE 1=1 {apply_filter('t2')}
        )
        SELECT ? || ' ' || w2, COUNT(*) as freq
        FROM next_tokens
        GROUP BY w2
        ORDER BY freq DESC LIMIT ?
    """, (token, *params, *neighbor_params, token, limit)).fetchall()
    
    # 2. Bigram: Word + Search (Backward)
    results['bi_word_search'] = conn.execute(f"""
        WITH {cte_matches},
        prev_tokens AS (
            SELECT t0.token as w0
            FROM matches m
            JOIN tokens t0 ON m.id - 1 = t0.id AND m.file_id = t0.file_id
            WHERE 1=1 {apply_filter('t0')}
        )
        SELECT w0 || ' ' || ?, COUNT(*) as freq
        FROM prev_tokens
        GROUP BY w0
        ORDER BY freq DESC LIMIT ?
    """, (token, *params, *neighbor_params, token, limit)).fetchall()
    
    # 3. Trigram: Search + Word + Word (s w w)
    results['tri_s_w_w'] = conn.execute(f"""
        WITH {cte_matches},
        next2 AS (
            SELECT t1.token as w1, t2.token as w2
            FROM matches m
            JOIN tokens t1 ON m.id + 1 = t1.id AND m.file_id = t1.file_id
            JOIN tokens t2 ON m.id + 2 = t2.id AND m.file_id = t2.file_id
            WHERE 1=1 {apply_filter('t1')} {apply_filter('t2')}
        )
        SELECT ? || ' ' || w1 || ' ' || w2, COUNT(*) as freq
        FROM next2
        GROUP BY w1, w2
        ORDER BY freq DESC LIMIT ?
    """, (token, *params, *neighbor_params, *neighbor_params, token, limit)).fetchall()
    
    # 4. Trigram: Word + Search + Word (w s w)
    results['tri_w_s_w'] = conn.execute(f"""
        WITH {cte_matches},
        surround AS (
            SELECT t0.token as w0, t2.token as w2
            FROM matches m
            JOIN tokens t0 ON m.id - 1 = t0.id AND m.file_id = t0.file_id
            JOIN tokens t2 ON m.id + 1 = t2.id AND m.file_id = t2.file_id
            WHERE 1=1 {apply_filter('t0')} {apply_filter('t2')}
        )
        SELECT w0 || ' ' || ? || ' ' || w2, COUNT(*) as freq
        FROM surround
        GROUP BY w0, w2
        ORDER BY freq DESC LIMIT ?
    """, (token, *params, *neighbor_params, *neighbor_params, token, limit)).fetchall()

    # 5. Trigram: Word + Word + Search (w w s)
    results['tri_w_w_s'] = conn.execute(f"""
        WITH {cte_matches},
        prev2 AS (
            SELECT t0.token as w0, t1.token as w1
            FROM matches m
            JOIN tokens t0 ON m.id - 2 = t0.id AND m.file_id = t0.file_id
            JOIN tokens t1 ON m.id - 1 = t1.id AND m.file_id = t1.file_id
            WHERE 1=1 {apply_filter('t0')} {apply_filter('t1')}
        )
        SELECT w0 || ' ' || w1 || ' ' || ?, COUNT(*) as freq
        FROM prev2
        GROUP BY w0, w1
        ORDER BY freq DESC LIMIT ?
    """, (token, *params, *neighbor_params, *neighbor_params, token, limit)).fetchall()
    
    conn.close()
    return results

def get_collocates(token, window=5, limit=20, where_clause="1=1", params=(), stop_words=None, allowed_words=None, skip_punct=True):
    conn = get_connection()
    if stop_words is None: stop_words = []
    
    # Allowed words is now a list of filter expressions (strings)
    # We need to parse this into SQL
    
    filter_sql, filter_params = parse_collocate_filter(allowed_words, alias="t2")
    
    base_filter_sql = ""
    base_filter_params = []
    
    if stop_words:
        placeholders = ",".join(["?"] * len(stop_words))
        base_filter_sql += f" AND t2.token NOT IN ({placeholders})"
        base_filter_params.extend(stop_words)

    if skip_punct:
         # exclude punctuation tokens
         base_filter_sql += " AND regexp_matches(t2.token, '[a-zA-Z0-9]')"

    N = conn.execute(f"SELECT COUNT(*) FROM tokens WHERE {where_clause}", params).fetchone()[0]
    if N == 0: return []
    
    node_freq = conn.execute(f"SELECT COUNT(*) FROM tokens WHERE token = ? AND {where_clause}", (token, *params)).fetchone()[0]
    if node_freq == 0: return []
    
    # Calculate Co-occurrences
    # combining standard filters + advanced filters
    final_filter_sql = base_filter_sql + filter_sql
    final_params = base_filter_params + filter_params
    
    collocan_counts = conn.execute(f"""
        WITH node_ids AS (
            SELECT id, file_id FROM tokens WHERE token = ? AND {where_clause}
        )
        SELECT t2.token, COUNT(*) as O11
        FROM node_ids n
        JOIN tokens t2 ON t2.file_id = n.file_id 
            AND t2.id BETWEEN n.id - ? AND n.id + ?
            AND t2.id != n.id
        WHERE {where_clause} {final_filter_sql}
        GROUP BY t2.token
        ORDER BY O11 DESC
        LIMIT 200 
    """, (token, *params, window, window, *params, *final_params)).fetchall()
    
    results = []
    for collocate, O11 in collocan_counts:
        # We need freq of collocate globally in the corpus (respecting where_clause but NOT the collocate filters?)
        # Usually standard LogLikelihood compares O11 (co-occurrence) vs Collocate Global Freq.
        col_freq = conn.execute(f"SELECT COUNT(*) FROM tokens WHERE token = ? AND {where_clause}", (collocate, *params)).fetchone()[0]
        
        try:
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
