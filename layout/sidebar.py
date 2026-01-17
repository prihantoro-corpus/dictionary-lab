import streamlit as st
import duckdb
from pipeline.indexing import get_connection

@st.cache_data
def get_corpora():
    conn = get_connection()
    try:
        res = conn.execute("SELECT DISTINCT corpus FROM tokens ORDER BY corpus").fetchall()
        return [r[0] for r in res if r[0]]
    except Exception:
        return []
    finally:
        conn.close()

@st.cache_data
def get_metadata_keys():
    """Returns list of unique keys found in metadata JSON."""
    conn = get_connection()
    try:
        # Unnest keys and find distinct ones
        # Check if table exists first
        res = conn.execute("""
            SELECT DISTINCT unnest(json_keys(metadata)) as k 
            FROM tokens 
            WHERE metadata IS NOT NULL
        """).fetchall()
        return sorted([r[0] for r in res])
    except Exception:
        return []
    finally:
        conn.close()

@st.cache_data
def get_metadata_values(key):
    """Returns list of unique values for a specific metadata key."""
    conn = get_connection()
    try:
        # Use json_extract_string
        query = f"SELECT DISTINCT json_extract_string(metadata, '$.{key}') as v FROM tokens WHERE json_extract_string(metadata, '$.{key}') IS NOT NULL ORDER BY v"
        res = conn.execute(query).fetchall()
        return [r[0] for r in res if r[0] is not None]
    except Exception:
        return []
    finally:
        conn.close()

def render():
    st.sidebar.title("CORPUS")
    
    # Corpus Selection
    available_corpora = get_corpora()
    selected_corpora = st.sidebar.multiselect(
        "Select corpora",
        options=available_corpora,
        default=available_corpora
    )
    
    st.sidebar.divider()
    st.sidebar.title("METADATA")
    
    # Dynamic Metadata Selection
    meta_keys = get_metadata_keys()
    selected_metadata = {}
    
    if not meta_keys:
        st.sidebar.caption("No metadata attributes found.")
    
    for key in meta_keys:
        values = get_metadata_values(key)
        if values:
            # Default: All selected? Or None? User said "all metadata attribute values must by default be shown".
            # Multiselect default=values means all selected (no filter applied effectively if logic is 'in').
            # Logic: If nothing selected -> No filter? Or Everything selected -> No filter.
            # Usually in simple UI, "All" is implied if nothing specific is excluded. 
            # But `st.multiselect` returns list.
            # Let's default to ALL.
            sel = st.sidebar.multiselect(
                f"{key}",
                options=values,
                default=values
            )
            selected_metadata[key] = sel
            
    st.sidebar.divider()
    
    # Filters
    st.sidebar.subheader("Filters")
    stop_words_str = st.sidebar.text_input("N-gram Stop Words", placeholder="in, the, of...")
    collocate_filter_str = st.sidebar.text_input("Collocate Filter", placeholder="word, ...")
    
    # Processing inputs
    stop_words = [s.strip() for s in stop_words_str.split(',')] if stop_words_str else []
    collocate_filter = [s.strip() for s in collocate_filter_str.split(',')] if collocate_filter_str else []
    
    # Build SQL Clause
    where_parts = ["1=1"]
    params = []
    
    # Corpus Filter
    if selected_corpora:
        placeholders = ",".join(["?"] * len(selected_corpora))
        where_parts.append(f"corpus IN ({placeholders})")
        params.extend(selected_corpora)
    else:
        where_parts.append("1=0") 
    
    # Metadata Filters
    for key, selected_vals in selected_metadata.items():
        # If user deselected some items, we filter. 
        # If selected list == all values, we technically don't need to filter, but robust way is to just filter IN (...)
        if not selected_vals:
            # If nothing selected for a category, assume 0 matches for that category? 
            # Or ignore? Usually if you uncheck all "years", you want no results?
            # Let's assume uncheck all = 0 results.
             where_parts.append("1=0")
        else:
            # Only add filter if it is a subset? 
            # For simplicity and correctness with "default all", we just add the IN clause.
            # Optimization: If len(selected) == len(all), skip? (Saves query complexity)
            # For now, just add it.
            placeholders = ",".join(["?"] * len(selected_vals))
            # JSON extract
            where_parts.append(f"json_extract_string(metadata, '$.{key}') IN ({placeholders})")
            params.extend(selected_vals)
            
    where_clause = " AND ".join(where_parts)
    
    return {
        'where_clause': where_clause,
        'params': params,
        'stop_words': stop_words,
        'collocate_filter': collocate_filter
    }
