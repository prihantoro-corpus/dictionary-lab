import streamlit as st
import duckdb
import os
import json
import tempfile
from pipeline.indexing import get_connection
from pipeline.overrides_io import load_overrides, save_overrides

CORPORA_DIR = os.path.join(os.getcwd(), "corpora")

@st.cache_data
def get_corpora():
    """Returns list of corpora names already indexed in DuckDB."""
    conn, is_shared = get_connection()
    try:
        res = conn.execute("SELECT DISTINCT corpus FROM tokens ORDER BY corpus").fetchall()
        return [r[0] for r in res if r[0]]
    except Exception:
        return []
    finally:
        if not is_shared:
            conn.close()

def get_disk_corpora():
    """Returns a dictionary of {corpus_name: filename} from the relative corpora/ folder."""
    if not os.path.exists(CORPORA_DIR):
        return {}
    
    disk_files = {}
    valid_exts = {'.xml', '.txt', '.xlsx', '.csv'}
    for f in os.listdir(CORPORA_DIR):
        name, ext = os.path.splitext(f)
        if ext.lower() in valid_exts:
            disk_files[name] = f
    return disk_files

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
    
    # --- Language Selection Section (FIRST) ---
    with st.sidebar.expander("🌐 Language Selection", expanded=True):
        st.caption("Select the language of your corpus:")
        
        # Initialize language in session state
        if 'corpus_language' not in st.session_state:
            st.session_state['corpus_language'] = 'English'
        
        language = st.selectbox(
            "Corpus Language:",
            options=['English', 'Indonesian', 'Other'],
            index=['English', 'Indonesian', 'Other'].index(st.session_state['corpus_language']),
            key="language_selector",
            help="This determines which features are available. English: all features. Indonesian: IPA transcription + Indonesian dictionaries. Other: basic features only."
        )
        
        st.session_state['corpus_language'] = language
        
        # Show language-specific info
        if language == 'English':
            st.success("✅ All features active")
        elif language == 'Indonesian':
            st.info("🇮🇩 Indonesian IPA + dictionaries active")
        else:
            st.warning("⚠️ Limited features (no transcription/badges)")
    
    st.sidebar.divider()
    
    # --- Corpus Selection Section ---
    with st.sidebar.expander("📁 Corpus Selection", expanded=True):
        # Initialize session state for corpus selection
        if 'corpus_selection_mode' not in st.session_state:
            st.session_state['corpus_selection_mode'] = None
        if 'staged_files' not in st.session_state:
            st.session_state['staged_files'] = []
        if 'staged_builtin' not in st.session_state:
            st.session_state['staged_builtin'] = []
        
        # Step 1: Show initial selection buttons or the selected mode interface
        if st.session_state['corpus_selection_mode'] is None:
            st.caption("Choose how to add corpora:")
            col1, col2 = st.columns(2)
            
            if col1.button("📤 File Upload", use_container_width=True):
                st.session_state['corpus_selection_mode'] = "File Upload"
                st.rerun()
            
            if col2.button("📚 Built-in Corpora", use_container_width=True):
                st.session_state['corpus_selection_mode'] = "Built-in Corpora"
                st.rerun()
        
        # Step 2: Show appropriate interface based on mode
        elif st.session_state['corpus_selection_mode'] == "File Upload":
            st.caption("📤 Upload one or more corpus files:")
            uploaded_files = st.file_uploader(
                "Select files",
                type=None,
                accept_multiple_files=True,
                key="corpus_file_uploader"
            )
            
            if uploaded_files:
                st.session_state['staged_files'] = uploaded_files
                st.info(f"📋 **{len(uploaded_files)} file(s) selected:**")
                for f in uploaded_files:
                    st.write(f"  • {f.name}")
            else:
                st.session_state['staged_files'] = []
                st.caption("No files selected yet.")
        
        elif st.session_state['corpus_selection_mode'] == "Built-in Corpora":
            st.caption("📚 Select from available built-in corpora:")
            disk_corpora_map = get_disk_corpora()
            
            # Helper to map common filenames to cleaner names
            def clean_name(n):
                if "EN-BPPT" in n: return "EN-BPPT"
                if "KOSLAT" in n: return "KOSLAT"
                return n
            
            # Get all available corpora (clean names)
            available_corpora = sorted([clean_name(c) for c in disk_corpora_map.keys()])
            
            if not available_corpora:
                st.warning("No built-in corpora found in the corpora/ folder.")
            else:
                selected_builtin = st.multiselect(
                    "Choose corpora:",
                    options=available_corpora,
                    default=st.session_state.get('staged_builtin', []),
                    key="builtin_corpus_multiselect"
                )
                st.session_state['staged_builtin'] = selected_builtin
                
                if selected_builtin:
                    st.info(f"📋 **{len(selected_builtin)} corpus/corpora selected:**")
                    for c in selected_builtin:
                        st.write(f"  • {c}")
                else:
                    st.caption("No corpora selected yet.")
        
        # Step 3: Load Corpus button
        st.divider()
        has_staged_content = (
            (st.session_state['corpus_selection_mode'] == "File Upload" and st.session_state['staged_files']) or
            (st.session_state['corpus_selection_mode'] == "Built-in Corpora" and st.session_state['staged_builtin'])
        )
        
        if st.button("🚀 Load Corpus", type="primary", use_container_width=True, disabled=not has_staged_content):
            loaded_names = []
            
            # Process file uploads
            if st.session_state['corpus_selection_mode'] == "File Upload" and st.session_state['staged_files']:
                from pipeline import ingest
                parser = ingest.CorpusParser()
                
                for uploaded_file in st.session_state['staged_files']:
                    with st.spinner(f"Processing {uploaded_file.name}..."):
                        tmp_fd, tmp_path = tempfile.mkstemp()
                        try:
                            with os.fdopen(tmp_fd, 'wb') as tmp:
                                tmp.write(uploaded_file.getvalue())
                            
                            corpus_name_display = os.path.splitext(uploaded_file.name)[0]
                            parser.process_file(tmp_path, corpus_name_display)
                            loaded_names.append(corpus_name_display)
                        finally:
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)
            
            # Process built-in corpora
            elif st.session_state['corpus_selection_mode'] == "Built-in Corpora" and st.session_state['staged_builtin']:
                from pipeline import ingest
                parser = ingest.CorpusParser()
                disk_corpora_map = get_disk_corpora()
                
                # Helper to map common filenames to cleaner names
                def clean_name(n):
                    if "EN-BPPT" in n: return "EN-BPPT"
                    if "KOSLAT" in n: return "KOSLAT"
                    return n
                
                # Create reverse mapping: clean_name -> disk_key
                clean_to_disk = {clean_name(k): k for k in disk_corpora_map.keys()}
                
                for corpus_clean_name in st.session_state['staged_builtin']:
                    with st.spinner(f"Loading {corpus_clean_name}..."):
                        if corpus_clean_name in clean_to_disk:
                            disk_key = clean_to_disk[corpus_clean_name]
                            f_path = os.path.join(CORPORA_DIR, disk_corpora_map[disk_key])
                            parser.process_file(f_path, corpus_clean_name)
                            loaded_names.append(corpus_clean_name)
            
            # Activate loaded corpora immediately
            if loaded_names:
                current_loaded = st.session_state.get('loaded_corpora', [])
                st.session_state['loaded_corpora'] = list(set(current_loaded + loaded_names))
                st.session_state['last_selection'] = st.session_state['loaded_corpora']
                
                # Clear staged items
                st.session_state['staged_files'] = []
                st.session_state['staged_builtin'] = []
                st.session_state['corpus_selection_mode'] = None
                
                st.cache_data.clear()
                st.success(f"✅ Loaded {len(loaded_names)} corpus/corpora. Now fully searchable!")
                st.rerun()
        
        # Reset button
        if st.session_state['corpus_selection_mode'] is not None:
            if st.button("↩️ Back to Selection", use_container_width=True):
                st.session_state['corpus_selection_mode'] = None
                st.session_state['staged_files'] = []
                st.session_state['staged_builtin'] = []
                st.rerun()

    # --- Personal Overrides File (Persistence) ---
    with st.sidebar.expander("🛠️ Personal Overrides Management", expanded=True):
        st.caption("Specify the path to your personal JSON file:")
        
        # Text input for file path
        default_path = st.session_state.get('personal_file_path', 'personal_overrides.json')
        file_path_input = st.text_input(
            "Personal File Path",
            value=default_path,
            help="Enter the full path to your personal modifications JSON file. The file will be created if it doesn't exist."
        )
        
        if st.button("✅ Set & Load File", use_container_width=True):
            st.session_state['personal_file_path'] = file_path_input
            # Create file if it doesn't exist
            if not os.path.exists(file_path_input):
                try:
                    # Create directory if needed
                    os.makedirs(os.path.dirname(file_path_input) or '.', exist_ok=True)
                    save_overrides(file_path_input, {})
                    st.success(f"Created new file: {file_path_input}")
                except Exception as e:
                    st.error(f"Could not create file: {e}")
            else:
                # Load existing file
                loaded_data = load_overrides(file_path_input)
                if loaded_data is not None:
                    st.session_state['overrides'] = loaded_data
                    st.success(f"Loaded from {file_path_input}!")
                else:
                    st.error("Failed to load file.")
            st.rerun()

        p_path = st.session_state.get('personal_file_path', 'personal_overrides.json')
        st.info(f"**Current file:**\n`{p_path}`")

        if st.button("🔄 Sync from File (Read)", help="Re-load overrides from your personal JSON file into the current session (discards unsaved session changes).", use_container_width=True):
             loaded_data = load_overrides(p_path)
             if loaded_data is not None:
                 st.session_state['overrides'] = loaded_data
                 st.success(f"Synced from {p_path}!")
                 st.rerun()
             else:
                 st.error("Failed to load from file.")
        
        st.sidebar.divider()
        if st.sidebar.button("🗑️ Clear All Corpus Data", help="Delete all tokens from the database."):
            from pipeline.indexing import get_connection
            conn, is_shared = get_connection()
            try:
                conn.execute("DELETE FROM tokens")
                st.sidebar.warning("Database cleared!")
                st.session_state['loaded_corpora'] = []
                st.session_state['last_selection'] = []
                st.cache_data.clear()
                st.rerun()
            finally:
                if not is_shared:
                    conn.close()

    # --- Active Search & Filtering ---
    st.sidebar.divider()
    
    # Check if corpora are loaded
    if 'loaded_corpora' not in st.session_state:
        st.session_state['loaded_corpora'] = []
    
    active_corpora = st.session_state['loaded_corpora']
    
    # If nothing loaded, stop here
    if not active_corpora:
        st.sidebar.warning("⚠️ No corpora loaded. Use **Corpus Selection** above to load corpora.")
        return {
            'where_clause': "1=0",
            'params': [],
            'stop_words': [],
            'collocate_filter': [],
            'no_corpora': True
        }

    
    st.sidebar.title("METADATA")
    meta_keys = get_metadata_keys(active_corpora)
    selected_metadata = {}
    
    if not meta_keys:
        st.sidebar.caption("No metadata found in loaded corpora.")
    
    for key in meta_keys:
        values = get_metadata_values(key, active_corpora)
        if values and len(values) <= 20:
            sel = st.sidebar.multiselect(f"{key}", options=values, default=values)
            selected_metadata[key] = sel
            
    st.sidebar.divider()
    st.sidebar.subheader("Filters")
    skip_punct = st.sidebar.checkbox("Skip Punctuation", value=True)
    stop_words_str = st.sidebar.text_input("N-gram Stop Words", placeholder="in, the, of...")
    col_filter_help = "Advanced Collocate Filtering (word, _TAG, car*, etc.)"
    collocate_filter_str = st.sidebar.text_input("Collocate Filter", placeholder="word, _TAG, ...", help=col_filter_help)
    
    stop_words = [s.strip() for s in stop_words_str.split(',')] if stop_words_str else []
    collocate_filter = [s.strip() for s in collocate_filter_str.split(',')] if collocate_filter_str else []
    
    where_parts = []
    params = []
    placeholders = ",".join(["?"] * len(active_corpora))
    where_parts.append(f"corpus IN ({placeholders})")
    params.extend(active_corpora)
    
    for key, selected_vals in selected_metadata.items():
        if not selected_vals:
             where_parts.append("1=0")
        else:
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
    
    return {
        'where_clause': where_clause,
        'params': params,
        'stop_words': stop_words,
        'collocate_filter': collocate_filter,
        'skip_punct': skip_punct
    }
