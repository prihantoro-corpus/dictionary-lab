import streamlit as st
import duckdb
from pipeline.indexing import get_connection

def get_corpora():
    conn = get_connection()
    try:
        res = conn.execute("SELECT DISTINCT corpus FROM tokens").fetchall()
        return [r[0] for r in res if r[0]]
    except Exception:
        return []
    finally:
        conn.close()

def render():
    st.sidebar.title("Corpus Filtering")
    
    # Corpus Selection
    available_corpora = get_corpora()
    selected_corpora = st.sidebar.multiselect(
        "Select Corpora",
        options=available_corpora,
        default=available_corpora
    )
    
    # Metadata Selection (Simplified for MVP)
    st.sidebar.subheader("Metadata Filters")
    st.sidebar.caption("Enter filters as key=value (one per line)")
    metadata_filters_str = st.sidebar.text_area("Attributes", placeholder="domain=economy\nyear=2010")
    
    # Build SQL Clause
    where_parts = ["1=1"]
    params = []
    
    if selected_corpora:
        placeholders = ",".join(["?"] * len(selected_corpora))
        where_parts.append(f"corpus IN ({placeholders})")
        params.extend(selected_corpora)
    else:
        # If nothing selected, maybe show nothing? Or everything? 
        # Usually default multiselect shows all. If user unchecks all, show nothing?
        # Let's say if None selected, show None.
        if available_corpora: 
             where_parts.append("1=0") # No corpus selected
    
    if metadata_filters_str:
        # Parsing "key=value"
        # Since metadata is JSON, we use json_extract(metadata, '$.key') = 'value'
        lines = metadata_filters_str.strip().split('\n')
        for line in lines:
            if '=' in line:
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip()
                # DuckDB JSON extraction syntax
                where_parts.append(f"json_extract_string(metadata, '$.{k}') = ?")
                params.append(v)
    
    where_clause = " AND ".join(where_parts)
    
    return where_clause, params
