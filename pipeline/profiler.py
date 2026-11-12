import pandas as pd
from pipeline.indexing import get_connection, safe_execute
from wordlist import manager

# TreeTagger placeholder lemmas that are not real vocabulary items
PLACEHOLDER_LEMMAS = ('@card@', '@ord@')

# Effective lemma: TreeTagger's '<unknown>' falls back to the surface word form.
EFFECTIVE_LEMMA = "LOWER(CASE WHEN lemma IS NULL OR lemma = '' OR lemma = '<unknown>' THEN token ELSE lemma END)"

# Module-level CEFR cache to avoid recomputing known words
_cefr_cache = {}

def _lookup_cefr(word, analyzer):
    """Cached lookup of the highest CEFR level for a word."""
    if word not in _cefr_cache:
        try:
            d = analyzer.get_pos_level_dict_for_word(word)
            if d:
                levels = sorted(list(set(lvl.name for lvl in d.values())))
                _cefr_cache[word] = levels[-1] if levels else None
            else:
                _cefr_cache[word] = None
        except Exception:
            _cefr_cache[word] = None
    return _cefr_cache[word]


def _calc_coverage(rows, wordlists, is_active_fn):
    """
    Computes text coverage purely by running word count (tokens).
    Matches words using both surface form and lemma so inflections
    (e.g. 'needs', 'needed') are properly recognized.
    """
    results = {}
    if not rows:
        return results

    total_words = sum(r[2] for r in rows)

    # 1. Static wordlists (e.g. NGSL, AWL, GSL, user-defined)
    for list_name, data in wordlists.items():
        if not is_active_fn(list_name):
            continue

        cov_words = 0
        breakdown = {}
        for l, tok, cnt in rows:
            # Match via lemma first, then surface token
            val = data.get(l) or data.get(tok)
            if val is not None:
                cov_words += cnt
                cat = val or "Generic"
                breakdown[cat] = breakdown.get(cat, 0) + cnt

        not_cov = total_words - cov_words
        results[list_name] = {
            'total_words': total_words,
            'covered_words': cov_words,
            'not_covered_words': not_cov,
            'coverage_pct': (cov_words / total_words * 100) if total_words > 0 else 0,
            'breakdown': breakdown,
            # Backward-compatibility aliases
            'total_corpus_unique': total_words,
            'covered_count': cov_words,
            'not_covered_count': not_cov,
        }

    # 2. CEFR library
    if manager.HAS_CEFR and is_active_fn('CEFR'):
        from cefrpy import CEFRAnalyzer
        analyzer = CEFRAnalyzer()

        cov_words = 0
        breakdown = {}
        for l, tok, cnt in rows:
            lvl = _lookup_cefr(l, analyzer) or _lookup_cefr(tok, analyzer)
            if lvl:
                cov_words += cnt
                breakdown[lvl] = breakdown.get(lvl, 0) + cnt

        if cov_words > 0:
            not_cov = total_words - cov_words
            results['CEFR'] = {
                'total_words': total_words,
                'covered_words': cov_words,
                'not_covered_words': not_cov,
                'coverage_pct': (cov_words / total_words * 100) if total_words > 0 else 0,
                'breakdown': breakdown,
                # Backward-compatibility aliases
                'total_corpus_unique': total_words,
                'covered_count': cov_words,
                'not_covered_count': not_cov,
            }

    return results


def get_vocabulary_profile(where_clause="1=1", params=(), active_lists=None):
    """
    Calculates corpus vocabulary coverage purely in word counts and percentages.
    Inflected words are matched via their lemma so words like 'needs' are covered.

    Punctuation, numbers, and TreeTagger tags @card@/@ord@ are excluded.
    active_lists: optional dict of { 'Wordlist Name': bool } from sidebar toggles.
    """
    conn, is_shared = get_connection()
    wordlists = manager.load_wordlists()
    
    active_lists = active_lists or {}
    def is_active(name):
        return active_lists.get(name, True)

    final_output = {'Aggregate': {}, 'By Corpus': {}, 'By File': {}}
    placeholders = ", ".join(f"'{p}'" for p in PLACEHOLDER_LEMMAS)
    base_where = (
        f"token IS NOT NULL AND token != '' "
        f"AND regexp_matches(token, '\\pL') "
        f"AND {EFFECTIVE_LEMMA} NOT IN ({placeholders}) "
        f"AND {where_clause}"
    )

    # 1. Aggregate
    query_agg = f"""
        SELECT {EFFECTIVE_LEMMA} as lemma, LOWER(token) as token, count(*) as cnt
        FROM tokens
        WHERE {base_where}
        GROUP BY 1, 2
    """
    res_agg = safe_execute(conn, query_agg, params).fetchall()
    final_output['Aggregate'] = _calc_coverage(res_agg, wordlists, is_active)

    # 2. By Corpus
    query_corp = f"""
        SELECT corpus, {EFFECTIVE_LEMMA} as lemma, LOWER(token) as token, count(*) as cnt
        FROM tokens
        WHERE {base_where}
        GROUP BY 1, 2, 3
    """
    res_corp = safe_execute(conn, query_corp, params).fetchall()
    grouped_corp = {}
    for corpus_name, lemma, token, cnt in res_corp:
        grouped_corp.setdefault(corpus_name, []).append((lemma, token, cnt))
    for corpus_name, rows in grouped_corp.items():
        final_output['By Corpus'][corpus_name] = _calc_coverage(rows, wordlists, is_active)

    # 3. By File
    query_files = f"""
        SELECT 
            COALESCE(json_extract_string(metadata, '$.file_name'), CAST(file_id AS VARCHAR)) as fname, 
            {EFFECTIVE_LEMMA} as lemma, 
            LOWER(token) as token, 
            count(*) as cnt 
        FROM tokens 
        WHERE {base_where} 
        GROUP BY 1, 2, 3
    """
    try:
        res_files = safe_execute(conn, query_files, params).fetchall()
        prefix = ""
    except Exception:
        query_files_fallback = f"""
            SELECT file_id, {EFFECTIVE_LEMMA} as lemma, LOWER(token) as token, count(*) as cnt
            FROM tokens
            WHERE {base_where}
            GROUP BY 1, 2, 3
        """
        res_files = safe_execute(conn, query_files_fallback, params).fetchall()
        prefix = "File "

    grouped_files = {}
    for fname, lemma, token, cnt in res_files:
        grouped_files.setdefault(f"{prefix}{fname}", []).append((lemma, token, cnt))
    for fname, rows in grouped_files.items():
        final_output['By File'][fname] = _calc_coverage(rows, wordlists, is_active)

    if not is_shared:
        conn.close()

    return final_output
