import streamlit as st
import duckdb
from pipeline.indexing import get_connection

@st.cache_data
def get_corpora():
    conn, is_shared = get_connection()
    try:
        res = conn.execute("SELECT DISTINCT corpus FROM tokens ORDER BY corpus").fetchall()
        return [r[0] for r in res if r[0]]
    except Exception:
        return []
    finally:
        if not is_shared:
            conn.close()

@st.cache_data
def get_metadata_keys(corpora=None):
    """Returns list of unique keys found in metadata JSON, optionally filtered by corpora."""
    conn, is_shared = get_connection()
    try:
        where_sql = ""
        params = []
        if corpora:
            placeholders = ",".join(["?"] * len(corpora))
            where_sql = f"AND corpus IN ({placeholders})"
            params = list(corpora)
        
        query = f"""
            SELECT DISTINCT unnest(json_keys(metadata)) as k 
            FROM tokens 
            WHERE metadata IS NOT NULL {where_sql}
        """
        res = conn.execute(query, params).fetchall()
        return sorted([r[0] for r in res])
    except Exception:
        return []
    finally:
        if not is_shared:
            conn.close()

@st.cache_data
def get_metadata_values(key, corpora=None):
    """Returns list of unique values for a specific metadata key, optionally filtered."""
    conn, is_shared = get_connection()
    try:
        where_sql = ""
        params = []
        if corpora:
            placeholders = ",".join(["?"] * len(corpora))
            where_sql = f"AND corpus IN ({placeholders})"
            params = list(corpora)

        query = f"""
            SELECT DISTINCT json_extract_string(metadata, '$.{key}') as v 
            FROM tokens 
            WHERE 1=1 {where_sql} 
            ORDER BY v
        """
        res = conn.execute(query, params).fetchall()
        vals = [r[0] for r in res if r[0] is not None]
        # Add N/A if there are tokens without this metadata key
        has_null = any(r[0] is None for r in res)
        if has_null:
            vals.append("None/N/A")
        return vals
    except Exception:
        return []
    finally:
        if not is_shared:
            conn.close()

def render():
    st.sidebar.title("DICTIONARY EDITOR")
    
    # --- Persistence & Uploads ---
    with st.sidebar.expander("📁 File Management", expanded=True):
        # 1. Corpus Upload
        uploaded_corpus = st.sidebar.file_uploader("Upload Corpus (vertical, XML, etc.)", type=None, key="corpus_uploader")
        if uploaded_corpus:
            if st.sidebar.button("⚙️ Process Uploaded File"):
                with st.spinner("Ingesting corpus..."):
                    from pipeline import ingest
                    import tempfile
                    import os
                    # Use a context manager that we explicitly close and delete
                    tmp_fd, tmp_path = tempfile.mkstemp()
                    try:
                        with os.fdopen(tmp_fd, 'wb') as tmp:
                            tmp.write(uploaded_corpus.getvalue())
                        
                        parser = ingest.CorpusParser()
                        # Use the original filename (without extension) as the corpus name
                        corpus_name_display = os.path.splitext(uploaded_corpus.name)[0]
                        parser.process_file(tmp_path, corpus_name_display)
                        
                        # NEW: Exclusively select the newly ingested corpus
                        st.session_state['last_selection'] = [corpus_name_display]
                        st.session_state['loaded_corpora'] = [corpus_name_display]
                        
                        st.sidebar.success(f"Ingested and Activated {corpus_name_display}")
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    
                    st.cache_data.clear()
                    st.rerun()

        # 2. Upload Changes (JSON)
        uploaded_json = st.sidebar.file_uploader("Upload Changes (.json)", type=["json"], key="json_uploader")
        if uploaded_json:
            if st.sidebar.button("💾 Apply Changes"):
                try:
                    import json
                    new_overrides = json.load(uploaded_json)
                    if 'overrides' not in st.session_state:
                        st.session_state['overrides'] = {}
                    st.session_state['overrides'].update(new_overrides)
                    st.sidebar.success("Changes uploaded and merged!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Error loading JSON: {e}")

        # 3. Save All Changes (Export)
        if st.session_state.get('overrides'):
            import json
            json_data = json.dumps(st.session_state['overrides'], indent=2)
            st.sidebar.download_button(
                label="💾 Save All Changes (JSON)",
                data=json_data,
                file_name="dictionary_changes.json",
                mime="application/json"
            )
        
        st.sidebar.divider()
        # 4. Clear Database (Reset)
        if st.sidebar.button("🗑️ Clear All Corpus Data", help="Delete all tokens from the database. This does NOT affect your saved overrides."):
            from pipeline.indexing import get_connection
            conn, is_shared = get_connection()
            try:
                conn.execute("DELETE FROM tokens")
                st.sidebar.warning("Database cleared!")
                # Clear session state related to corpora
                if 'loaded_corpora' in st.session_state:
                    del st.session_state['loaded_corpora']
                if 'last_selection' in st.session_state:
                    del st.session_state['last_selection']
                st.cache_data.clear()
                st.rerun()
            finally:
                if not is_shared:
                    conn.close()

    st.sidebar.divider()
    available_corpora = get_corpora()
    
    # 1. Status Section ( provenance )
    st.sidebar.subheader("📡 Corpus Status")
    active_corpora = st.session_state.get('loaded_corpora', [])
    
    if not active_corpora:
        st.sidebar.warning("⭕ No Active Corpora")
    else:
        for c in active_corpora:
            source = "SYSTEM" if c in ["BPPT", "KOSLAT"] else "USER MACHINE"
            st.sidebar.success(f"✅ {c} ({source})")

    st.sidebar.divider()
    
    # 2. Corpus Selection
    st.sidebar.title("CORPUS SEARCH")
    
    # Defaults? If nothing loaded, maybe default is empty or all? User said "System overload", so default empty.
    raw_default = st.session_state.get('last_selection', available_corpora)
    # CRITICAL: Ensure every default value exists in available_corpora to avoid StreamlitAPIException
    default_sel = [v for v in raw_default if v in available_corpora]
    
    if st.sidebar.button("✖️ Deselect All Corpora"):
        st.session_state['last_selection'] = []
        st.session_state['loaded_corpora'] = []
        st.rerun()
    
    # Keyconcept: reactive selection
    selection = st.sidebar.multiselect(
        "Select Corpora to Index",
        options=available_corpora,
        default=default_sel,
        key="corpus_multiselect"
    )
    
    # Update active list immediately when selection changes
    st.session_state['loaded_corpora'] = selection
    st.session_state['last_selection'] = selection
        
    # Get active loaded
    active_corpora = selection
    
    st.sidebar.divider()
    
    # If nothing loaded, stop here
    if not active_corpora:
        st.sidebar.info("💡 Select one or more corpora above to begin.")
        # Diagnostic button even here
        if st.sidebar.button("🔍 Diagnose Statistics"):
             from stats.frequency import get_total_tokens
             st.sidebar.write(f"Global Tokens: {get_total_tokens()}")
             st.sidebar.write("Subset Tokens: 0 (No corpora active)")
             st.sidebar.info("You must select a corpus and click 'Load Corpora' to see data.")
        return {
            'where_clause': "1=0",
            'params': [],
            'stop_words': [],
            'collocate_filter': []
        }
    
    st.sidebar.success(f"Active: {len(active_corpora)} corpora")
    
    st.sidebar.title("METADATA")
    
    # Dynamic Metadata Selection (Context-aware)
    meta_keys = get_metadata_keys(active_corpora)
    selected_metadata = {}
    
    if not meta_keys:
        st.sidebar.caption("No metadata attributes found in loaded corpora.")
    
    for key in meta_keys:
        values = get_metadata_values(key, active_corpora)
        if values and len(values) <= 20:
            sel = st.sidebar.multiselect(
                f"{key}",
                options=values,
                default=values
            )
            selected_metadata[key] = sel
            
    st.sidebar.divider()
    
    # Filters
    st.sidebar.subheader("Filters")
    
    skip_punct = st.sidebar.checkbox("Skip Punctuation", value=True, help="Exclude punctuation marks and symbols from N-grams and Collocates.")
    
    stop_words_help = "Comma-separated list of words to exclude (e.g. 'the, of, a'). N-grams containing these words will be hidden."
    stop_words_str = st.sidebar.text_input("N-gram Stop Words", placeholder="in, the, of...", help=stop_words_help)
    
    col_filter_help = """
    Advanced Collocate Filtering:
    - **Exact Match**: `of` (Include only 'of')
    - **Wildcard**: `car*` (Starts with 'car'), `*car` (Ends with 'car'), `*car*` (Contains 'car')
    - **Regex**: `(of|in)` (Matches 'of' or 'in')
    - **POS Inclusion**: `_JJ` (Include only Adjectives)
    - **POS Exclusion**: `-NN` (Exclude Nouns)
    
    Combine with commas (OR logic for inclusions, AND logic for exclusions).
    """
    collocate_filter_str = st.sidebar.text_input("Collocate Filter", placeholder="word, _TAG, ...", help=col_filter_help)
    
    stop_words = [s.strip() for s in stop_words_str.split(',')] if stop_words_str else []
    collocate_filter = [s.strip() for s in collocate_filter_str.split(',')] if collocate_filter_str else []
    
    # Build SQL
    where_parts = []
    params = []
    
    # Corpus Filter (Active)
    placeholders = ",".join(["?"] * len(active_corpora))
    where_parts.append(f"corpus IN ({placeholders})")
    params.extend(active_corpora)
    
    # Metadata Filters
    for key, selected_vals in selected_metadata.items():
        if not selected_vals:
             where_parts.append("1=0")
        else:
            # Handle the "None/N/A" choice
            if "None/N/A" in selected_vals:
                actual_vals = [v for v in selected_vals if v != "None/N/A"]
                if not actual_vals:
                    where_parts.append(f"json_extract_string(metadata, '$.{key}') IS NULL")
                else:
                    placeholders = ",".join(["?"] * len(actual_vals))
                    where_parts.append(f"(json_extract_string(metadata, '$.{key}') IN ({placeholders}) OR json_extract_string(metadata, '$.{key}') IS NULL)")
                    params.extend(actual_vals)
            else:
                placeholders = ",".join(["?"] * len(selected_vals))
                where_parts.append(f"json_extract_string(metadata, '$.{key}') IN ({placeholders})")
                params.extend(selected_vals)
            
    where_clause = " AND ".join(where_parts)
    
    # Diagnostics
    if st.sidebar.button("🔍 Diagnose Statistics"):
        from stats.frequency import get_total_tokens
        t_total = get_total_tokens()
        t_subset = get_total_tokens(where_clause, params)
        st.sidebar.write(f"Global Tokens: {t_total}")
        st.sidebar.write(f"Subset Tokens: {t_subset}")
        st.sidebar.code(f"WHERE: {where_clause}")
        st.sidebar.code(f"PARAMS: {params}")

    return {
        'where_clause': where_clause,
        'params': params,
        'stop_words': stop_words,
        'collocate_filter': collocate_filter,
        'skip_punct': skip_punct
    }
