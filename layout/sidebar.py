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
def get_metadata_keys(corpora=None):
    """Returns list of unique keys found in metadata JSON, optionally filtered by corpora."""
    conn = get_connection()
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
        conn.close()

@st.cache_data
def get_metadata_values(key, corpora=None):
    """Returns list of unique values for a specific metadata key, optionally filtered."""
    conn = get_connection()
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
            WHERE json_extract_string(metadata, '$.{key}') IS NOT NULL {where_sql} 
            ORDER BY v
        """
        res = conn.execute(query, params).fetchall()
        return [r[0] for r in res if r[0] is not None]
    except Exception:
        return []
    finally:
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
                        parser.ingest_file(tmp_path)
                        st.sidebar.success(f"Ingested {uploaded_corpus.name}")
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
            conn = get_connection()
            try:
                conn.execute("DELETE FROM tokens")
                st.sidebar.warning("Database cleared!")
                st.cache_data.clear()
                st.rerun()
            finally:
                conn.close()

    st.sidebar.divider()
    st.sidebar.title("CORPUS SEARCH")
    
    available_corpora = get_corpora()
    
    # 1. Corpus Selection
    # Key concept: "Selection" vs "Loaded"
    # User selects from list, then clicks Load.
    
    # Defaults? If nothing loaded, maybe default is empty or all? User said "System overload", so default empty.
    default_sel = st.session_state.get('last_selection', available_corpora) # Keep last choice logic if desirable
    
    selection = st.sidebar.multiselect(
        "Available Corpora",
        options=available_corpora,
        default=default_sel,
        key="corpus_multiselect"
    )
    
    if st.sidebar.button("Load Corpora"):
        st.session_state['loaded_corpora'] = selection
        st.session_state['last_selection'] = selection
        st.rerun() # Refresh to show metadata
        
    # Get active loaded
    active_corpora = st.session_state.get('loaded_corpora', [])
    
    st.sidebar.divider()
    
    # If nothing loaded, stop here
    if not active_corpora:
        st.sidebar.warning("No corpora loaded. Select above and click 'Load Corpora'.")
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
            placeholders = ",".join(["?"] * len(selected_vals))
            where_parts.append(f"json_extract_string(metadata, '$.{key}') IN ({placeholders})")
            params.extend(selected_vals)
            
    where_clause = " AND ".join(where_parts)
    
    
    return {
        'where_clause': where_clause,
        'params': params,
        'stop_words': stop_words,
        'collocate_filter': collocate_filter,
        'skip_punct': skip_punct
    }
