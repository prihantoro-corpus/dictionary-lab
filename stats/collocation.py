from pipeline.indexing import get_connection, safe_execute
import math
import os

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

def get_ngrams(token, limit=10, where_clause="1=1", params=(), stop_words=None, skip_punct=True, pos_tag=None):
    conn, is_shared = get_connection()
    if stop_words is None: stop_words = []
    
    results = {}
    
    # Base CTE (case-insensitive for broad coverage)
    if pos_tag:
        cte_matches = f"matches AS (SELECT id, file_id FROM tokens WHERE token ILIKE ? AND tag = ? AND {where_clause})"
        base_params = (token, pos_tag)
    else:
        cte_matches = f"matches AS (SELECT id, file_id FROM tokens WHERE token ILIKE ? AND {where_clause})"
        base_params = (token,)
    
    # Filters for neighbors
    neighbor_filter = ""
    neighbor_params = []
    
    if skip_punct:
        # Match alphanumeric OR any non-ASCII character (to support intl scripts)
        neighbor_filter += " AND regexp_matches(token, '([a-zA-Z0-9]|[^\\x00-\\x7F])')"
    
    if stop_words:
        placeholders = ",".join(["?"] * len(stop_words))
        neighbor_filter += f" AND token NOT IN ({placeholders})"
        neighbor_params.extend(stop_words)

    # Helper to apply filter to a specific alias
    def apply_filter(alias):
        return neighbor_filter.replace("token", f"{alias}.token")

    # 1. Bigram: Search + Word (Forward)
    results['bi_search_word'] = safe_execute(conn, f"""
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
    """, (*base_params, *params, *neighbor_params, token, limit)).fetchall()
    
    # 2. Bigram: Word + Search (Backward)
    results['bi_word_search'] = safe_execute(conn, f"""
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
    """, (*base_params, *params, *neighbor_params, token, limit)).fetchall()
    
    # 3. Trigram: Search + Word + Word (s w w)
    results['tri_s_w_w'] = safe_execute(conn, f"""
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
    """, (*base_params, *params, *neighbor_params, *neighbor_params, token, limit)).fetchall()
    
    # 4. Trigram: Word + Search + Word (w s w)
    results['tri_w_s_w'] = safe_execute(conn, f"""
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
    """, (*base_params, *params, *neighbor_params, *neighbor_params, token, limit)).fetchall()

    # 5. Trigram: Word + Word + Search (w w s)
    results['tri_w_w_s'] = safe_execute(conn, f"""
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
    """, (*base_params, *params, *neighbor_params, *neighbor_params, token, limit)).fetchall()
    
    if not is_shared:
        conn.close()
    return results

def _get_ll_sql(o11, e11, o12, e12, o21, e21, o22, e22):
    """Returns the SQL fragment for calculating Log-Likelihood."""
    return f"""
        2 * (
            (CASE WHEN {o11} > 0 AND {e11} > 0 THEN {o11} * LN({o11}/{e11}) ELSE 0 END) +
            (CASE WHEN {o12} > 0 AND {e12} > 0 THEN {o12} * LN({o12}/{e12}) ELSE 0 END) +
            (CASE WHEN {o21} > 0 AND {e21} > 0 THEN {o21} * LN({o21}/{e21}) ELSE 0 END) +
            (CASE WHEN {o22} > 0 AND {e22} > 0 THEN {o22} * LN({o22}/{e22}) ELSE 0 END)
        )
    """

def get_collocates(token, window=5, limit=20, where_clause="1=1", params=(), stop_words=None, allowed_words=None, skip_punct=True, pos_tag=None):
    conn, is_shared = get_connection()
    if stop_words is None: stop_words = []
    
    filter_sql, filter_params = parse_collocate_filter(allowed_words, alias="t2")
    
    base_filter_sql = ""
    base_filter_params = []
    if stop_words:
        placeholders = ",".join(["?"] * len(stop_words))
        base_filter_sql += f" AND t2.token NOT IN ({placeholders})"
        base_filter_params.extend(stop_words)
    if skip_punct:
         # Match alphanumeric OR any non-ASCII character
         base_filter_sql += " AND regexp_matches(t2.token, '([a-zA-Z0-9]|[^\\x00-\\x7F])')"

    # 1. Get Node Freq and Total N
    N = safe_execute(conn, f"SELECT COUNT(*) FROM tokens WHERE {where_clause}", params).fetchone()[0]
    if N == 0:
        if not is_shared: conn.close()
        return []
    
    if pos_tag:
        node_freq = safe_execute(conn, f"SELECT COUNT(*) FROM tokens WHERE token ILIKE ? AND tag = ? AND {where_clause}", (token, pos_tag, *params)).fetchone()[0]
        node_ids_cte = f"SELECT id, file_id FROM tokens WHERE token ILIKE ? AND tag = ? AND {where_clause}"
        node_params = (token, pos_tag, *params)
    else:
        node_freq = safe_execute(conn, f"SELECT COUNT(*) FROM tokens WHERE token ILIKE ? AND {where_clause}", (token, *params)).fetchone()[0]
        node_ids_cte = f"SELECT id, file_id FROM tokens WHERE token ILIKE ? AND {where_clause}"
        node_params = (token, *params)

    if node_freq == 0:
        if not is_shared: conn.close()
        return []

    # 2. Unified SQL to get O11 and col_freq and calculate LL
    final_filter_sql = base_filter_sql + filter_sql
    final_params = base_filter_params + filter_params

    query = f"""
        WITH node_ids AS ({node_ids_cte}),
        o11_counts AS (
            SELECT t2.token, t2.tag, COUNT(*) as O11, 
                   SUM(CASE WHEN t2.id < n.id THEN 1 ELSE 0 END) as left_count, 
                   SUM(CASE WHEN t2.id > n.id THEN 1 ELSE 0 END) as right_count
            FROM node_ids n
            JOIN tokens t2 ON t2.file_id = n.file_id 
                AND t2.id BETWEEN n.id - ? AND n.id + ?
                AND t2.id != n.id
            WHERE {where_clause} {final_filter_sql}
            GROUP BY t2.token, t2.tag
        ),
        col_freqs AS (
            SELECT token, tag, COUNT(*) as col_freq
            FROM tokens
            WHERE {where_clause}
            AND (token, tag) IN (SELECT token, tag FROM o11_counts)
            GROUP BY token, tag
        ),
        stats AS (
            SELECT 
                o.token, o.tag, o.O11, o.left_count, o.right_count, f.col_freq,
                CAST(? AS FLOAT) as NodeFreq, CAST(? AS FLOAT) as TotalN,
                (NodeFreq * f.col_freq) / TotalN as E11,
                (NodeFreq * (TotalN - f.col_freq)) / TotalN as E12,
                ((TotalN - NodeFreq) * f.col_freq) / TotalN as E21,
                ((TotalN - NodeFreq) * (TotalN - f.col_freq)) / TotalN as E22,
                o.O11 as O11_f,
                GREATEST(0, NodeFreq - o.O11) as O12,
                GREATEST(0, f.col_freq - o.O11) as O21,
                GREATEST(0, TotalN - (NodeFreq + f.col_freq - o.O11)) as O22
            FROM o11_counts o
            JOIN col_freqs f ON o.token = f.token AND o.tag = f.tag
        )
        SELECT token, tag, O11, left_count, right_count,
               {_get_ll_sql('O11_f', 'E11', 'O12', 'E12', 'O21', 'E21', 'O22', 'E22')} as score
        FROM stats
        WHERE O11_f > E11
        ORDER BY score DESC
        LIMIT ?
    """
    
    full_params = (*node_params, window, window, *params, *final_params, *params, node_freq, N, limit)
    res = safe_execute(conn, query, full_params).fetchall()

    results = []
    for row in res:
        results.append({
            'collocate': row[0], 'tag': row[1], 'freq': row[2],
            'left': row[3], 'right': row[4], 'score': row[5]
        })

    if not is_shared: conn.close()
    return results

def get_collocate_rank(token, collocate_to_rank, window=5, where_clause="1=1", params=(), stop_words=None, allowed_words=None, skip_punct=True, pos_tag=None):
    results = get_collocates(token, window=window, limit=1000, where_clause=where_clause, params=params, stop_words=stop_words, allowed_words=allowed_words, skip_punct=skip_punct, pos_tag=pos_tag)
    
    for i, item in enumerate(results):
        if item['collocate'].lower() == collocate_to_rank.lower():
            return i + 1
    return None

def get_phrase_ngrams(phrase, limit=10, where_clause="1=1", params=(), stop_words=None, skip_punct=True):
    conn, is_shared = get_connection()
    parts = phrase.split()
    length = len(parts)

    # Prepare filters
    neighbor_filter = ""
    neighbor_params = []
    if skip_punct:
        neighbor_filter += " AND regexp_matches(token, '([a-zA-Z0-9]|[^\\x00-\\x7F])')"
    if stop_words:
        placeholders = ",".join(["?"] * len(stop_words))
        neighbor_filter += f" AND token NOT IN ({placeholders})"
        neighbor_params.extend(stop_words)

    def apply_filter(alias):
        return neighbor_filter.replace("token", f"{alias}.token")

    # CTE for phrase instances
    joins = []
    conditions = []
    q_params = []
    for i, p in enumerate(parts):
        alias = f"t{i}"
        conditions.append(f"{alias}.token ILIKE ?")
        q_params.append(p)
        if i > 0:
            prev = f"t{i-1}"
            joins.append(f"JOIN tokens {alias} ON {prev}.id + 1 = {alias}.id AND {prev}.file_id = {alias}.file_id")

    # Base CTE query part
    cte_query = f"""
        WITH start_tokens AS (
            SELECT id, file_id 
            FROM tokens 
            WHERE token ILIKE ? AND {where_clause}
        ),
        matches AS (
            SELECT t0.id as start_id, t{length-1}.id as end_id, t0.file_id
            FROM start_tokens t0
            {" ".join(joins)}
        )
    """
    
    # We apply filters in the start_tokens part, but we also need the remaining conditions
    rem_cond = " AND ".join(conditions[1:])
    if rem_cond:
        cte_query = f"""
            WITH start_tokens AS (
                SELECT id, file_id 
                FROM tokens 
                WHERE token ILIKE ? AND {where_clause}
            ),
            matches AS (
                SELECT t0.id as start_id, t{length-1}.id as end_id, t0.file_id
                FROM start_tokens t0
                {" ".join(joins)}
                WHERE {rem_cond}
            )
        """
    else:
        cte_query = f"""
            WITH start_tokens AS (
                SELECT id, file_id 
                FROM tokens 
                WHERE token ILIKE ? AND {where_clause}
            ),
            matches AS (
                SELECT t0.id as start_id, t{length-1}.id as end_id, t0.file_id
                FROM start_tokens t0
                {" ".join(joins)}
                WHERE 1=1
            )
        """

    full_params = (parts[0], *params, *q_params[1:])
    
    results = {}
    
    # 1. Forward (Phrase + Next)
    phrase_disp = " ".join(parts) # Display string
    
    results['forward'] = safe_execute(conn, f"""
        {cte_query}
        SELECT '{phrase_disp}' || ' ' || tn.token, COUNT(*) as freq
        FROM matches m
        JOIN tokens tn ON m.end_id + 1 = tn.id AND m.file_id = tn.file_id
        WHERE 1=1 {apply_filter('tn')}
        GROUP BY tn.token
        ORDER BY freq DESC LIMIT ?
    """, (*full_params, *neighbor_params, limit)).fetchall()
    
    # 2. Backward (Prev + Phrase)
    results['backward'] = safe_execute(conn, f"""
        {cte_query}
        SELECT tp.token || ' ' || '{phrase_disp}', COUNT(*) as freq
        FROM matches m
        JOIN tokens tp ON m.start_id - 1 = tp.id AND m.file_id = tp.file_id
        WHERE 1=1 {apply_filter('tp')}
        GROUP BY tp.token
        ORDER BY freq DESC LIMIT ?
    """, (*full_params, *neighbor_params, limit)).fetchall()
    
    if not is_shared: conn.close()
    return results

def get_phrase_collocates(phrase, window=5, limit=20, where_clause="1=1", params=(), stop_words=None, allowed_words=None, skip_punct=True):
    conn, is_shared = get_connection()
    parts = phrase.split()
    length = len(parts)
    
    # 1. Node IDs logic
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

    gap_checks = ""
    if skip_punct and len(parts) > 1:
        checks = []
        for i in range(1, len(parts)):
            prev = f"t{i-1}"
            curr = f"t{i}"
            checks.append(f"NOT EXISTS (SELECT 1 FROM tokens GAP_{i} WHERE GAP_{i}.file_id = t0.file_id AND GAP_{i}.id > {prev}.id AND GAP_{i}.id < {curr}.id AND regexp_matches(GAP_{i}.token, '([a-zA-Z0-9]|[^\\x00-\\x7F])'))")
        gap_checks = " AND " + " AND ".join(checks)

    node_ids_cte = f"""
        SELECT t0.id as start_id, t{length-1}.id as end_id, t0.file_id
        FROM (SELECT id, file_id, token FROM tokens WHERE token ILIKE ? AND {where_clause}) t0
        {" ".join(joins)}
        WHERE 1=1
        {" AND " + " AND ".join(conditions[1:]) if len(conditions) > 1 else ""}
        {gap_checks}
    """
    
    base_params = (parts[0], *params, *q_params[1:])
    node_freq = safe_execute(conn, f"WITH matches AS ({node_ids_cte}) SELECT COUNT(*) FROM matches", base_params).fetchone()[0]
    
    if node_freq == 0:
        if not is_shared: conn.close()
        return []
        
    N = safe_execute(conn, f"SELECT COUNT(*) FROM tokens WHERE {where_clause}", params).fetchone()[0]
    
    # 2. Filters
    filter_sql, filter_params = parse_collocate_filter(allowed_words, alias="t2")
    base_filter_sql = ""
    base_filter_params = []
    if stop_words:
        placeholders = ",".join(["?"] * len(stop_words))
        base_filter_sql += f" AND t2.token NOT IN ({placeholders})"
        base_filter_params.extend(stop_words)
    if skip_punct:
         base_filter_sql += " AND regexp_matches(t2.token, '([a-zA-Z0-9]|[^\\x00-\\x7F])')"

    final_filter_sql = base_filter_sql + filter_sql
    final_params = base_filter_params + filter_params

    # 3. Optimized Bulk Calculation
    query = f"""
        WITH matches AS ({node_ids_cte}),
        o11_counts AS (
            SELECT t2.token, t2.tag, COUNT(*) as O11,
                   SUM(CASE WHEN t2.id < m.start_id THEN 1 ELSE 0 END) as left_count, 
                   SUM(CASE WHEN t2.id > m.end_id THEN 1 ELSE 0 END) as right_count
            FROM matches m
            JOIN tokens t2 ON t2.file_id = m.file_id 
                AND t2.id BETWEEN m.start_id - ? AND m.end_id + ?
                AND (t2.id < m.start_id OR t2.id > m.end_id)
            WHERE {where_clause} {final_filter_sql}
            GROUP BY t2.token, t2.tag
        ),
        col_freqs AS (
            SELECT token, tag, COUNT(*) as col_freq
            FROM tokens
            WHERE {where_clause}
            AND (token, tag) IN (SELECT token, tag FROM o11_counts)
            GROUP BY token, tag
        ),
        stats AS (
            SELECT 
                o.token, o.tag, o.O11, o.left_count, o.right_count, f.col_freq,
                CAST(? AS FLOAT) as NodeFreq, CAST(? AS FLOAT) as TotalN,
                (NodeFreq * f.col_freq) / TotalN as E11,
                (NodeFreq * (TotalN - f.col_freq)) / TotalN as E12,
                ((TotalN - NodeFreq) * f.col_freq) / TotalN as E21,
                ((TotalN - NodeFreq) * (TotalN - f.col_freq)) / TotalN as E22,
                o.O11 as O11_f,
                GREATEST(0, NodeFreq - o.O11) as O12,
                GREATEST(0, f.col_freq - o.O11) as O21,
                GREATEST(0, TotalN - (NodeFreq + f.col_freq - o.O11)) as O22
            FROM o11_counts o
            JOIN col_freqs f ON o.token = f.token AND o.tag = f.tag
        )
        SELECT token, tag, O11, left_count, right_count,
               {_get_ll_sql('O11_f', 'E11', 'O12', 'E12', 'O21', 'E21', 'O22', 'E22')} as score
        FROM stats
        WHERE O11_f > E11
        ORDER BY score DESC
        LIMIT ?
    """
    
    full_params = (*base_params, window, window, *params, *final_params, *params, node_freq, N, limit)
    res = safe_execute(conn, query, full_params).fetchall()

    results = []
    for row in res:
        results.append({
            'collocate': row[0], 'tag': row[1], 'freq': row[2],
            'left': row[3], 'right': row[4], 'score': row[5]
        })

    if not is_shared: conn.close()
    return results

def get_phrase_collocate_rank(phrase, collocate_to_rank, window=5, where_clause="1=1", params=(), stop_words=None, allowed_words=None, skip_punct=True):
    results = get_phrase_collocates(phrase, window=window, limit=1000, where_clause=where_clause, params=params, stop_words=stop_words, allowed_words=allowed_words, skip_punct=skip_punct)
    
    for i, item in enumerate(results):
        if item['collocate'].lower() == collocate_to_rank.lower():
            return i + 1
    return None
