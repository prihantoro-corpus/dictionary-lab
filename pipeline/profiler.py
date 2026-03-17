import pandas as pd
from pipeline.indexing import get_connection, safe_execute
from wordlist import manager

def get_vocabulary_profile(where_clause="1=1", params=()):
    """
    Calculates the distribution of corpus lemmas across all loaded wordlists.
    Returns: { 
        'Aggregate': { 'Wordlist Name': { ... } },
        'By Corpus': { 'Corpus Name': { 'Wordlist Name': { ... } } },
        'By File': { 'Filename': { 'Wordlist Name': { ... } } }
    }
    """
    conn, is_shared = get_connection()
    
    # helper for coverage calculation
    def calc_coverage(lemmas, wordlists):
        results = {}
        total_unique = len(lemmas)
        
        # Static wordlists
        for list_name, data in wordlists.items():
            covered_count = 0
            breakdown = {}
            for lemma in lemmas:
                if lemma in data:
                    covered_count += 1
                    category = data[lemma] or "Generic"
                    breakdown[category] = breakdown.get(category, 0) + 1
            
            results[list_name] = {
                'total_corpus_unique': total_unique,
                'covered_count': covered_count,
                'not_covered_count': total_unique - covered_count,
                'coverage_pct': (covered_count / total_unique) * 100 if total_unique > 0 else 0,
                'breakdown': breakdown
            }
            
        # CEFR case
        if manager.HAS_CEFR:
            from cefrpy import CEFRAnalyzer
            analyzer = CEFRAnalyzer()
            cefr_covered = 0
            cefr_breakdown = {}
            for lemma in lemmas:
                res_dict = analyzer.get_pos_level_dict_for_word(lemma)
                if res_dict:
                    cefr_covered += 1
                    levels = sorted(list(set([lvl.name for lvl in res_dict.values()])))
                    if levels:
                        cefr_breakdown[levels[-1]] = cefr_breakdown.get(levels[-1], 0) + 1
            if cefr_covered > 0:
                results['CEFR'] = {
                    'total_corpus_unique': total_unique,
                    'covered_count': cefr_covered,
                    'not_covered_count': total_unique - cefr_covered,
                    'coverage_pct': (cefr_covered / total_unique) * 100 if total_unique > 0 else 0,
                    'breakdown': cefr_breakdown
                }
        return results

    # Get data levels
    wordlists = manager.load_wordlists()
    final_output = {'Aggregate': {}, 'By Corpus': {}, 'By File': {}}
    
    # 1. Aggregate
    query_agg = f"SELECT DISTINCT LOWER(lemma) FROM tokens WHERE lemma IS NOT NULL AND lemma != '' AND {where_clause}"
    res_agg = safe_execute(conn, query_agg, params).fetchall()
    final_output['Aggregate'] = calc_coverage({r[0] for r in res_agg}, wordlists)
    
    # 2. By Corpus
    query_corp = f"SELECT corpus, list(DISTINCT LOWER(lemma)) FROM tokens WHERE lemma IS NOT NULL AND lemma != '' AND {where_clause} GROUP BY corpus"
    res_corp = safe_execute(conn, query_corp, params).fetchall()
    for corpus_name, lemma_list in res_corp:
        final_output['By Corpus'][corpus_name] = calc_coverage(set(lemma_list), wordlists)
        
    # 3. By File
    # We need filenames. Usually file_id links to something? 
    # Metadata usually has 'file_name' or just use the id. 
    # Let's try to extract filenames if available in metadata
    query_files = f"""
        SELECT 
            COALESCE(json_extract_string(metadata, '$.file_name'), CAST(file_id AS VARCHAR)) as fname, 
            list(DISTINCT LOWER(lemma)) 
        FROM tokens 
        WHERE lemma IS NOT NULL AND lemma != '' AND {where_clause} 
        GROUP BY fname
    """
    try:
        res_files = safe_execute(conn, query_files, params).fetchall()
        for fname, lemma_list in res_files:
            final_output['By File'][fname] = calc_coverage(set(lemma_list), wordlists)
    except:
        # Fallback to just file_id
        query_files_fallback = f"SELECT file_id, list(DISTINCT LOWER(lemma)) FROM tokens WHERE lemma IS NOT NULL AND lemma != '' AND {where_clause} GROUP BY file_id"
        res_files = safe_execute(conn, query_files_fallback, params).fetchall()
        for fid, lemma_list in res_files:
            final_output['By File'][f"File {fid}"] = calc_coverage(set(lemma_list), wordlists)
            
    if not is_shared:
        conn.close()
        
    return final_output
