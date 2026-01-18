import streamlit as st
import duckdb
import os
import json
import tempfile
import tkinter as tk
from tkinter import filedialog
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
    
    # --- Management Section ---
    with st.sidebar.expander("📁 Corpus Management", expanded=True):
        manage_mode = st.radio("Add Corpus From:", ["Upload your file", "Use built-in corpora"], horizontal=True)
        
        if manage_mode == "Upload your file":
            uploaded_corpus = st.file_uploader("Upload Corpus (vertical, XML, etc.)", type=None, key="corpus_uploader")
            if uploaded_corpus:
                if st.button("⚙️ Process Uploaded File"):
                    with st.spinner("Ingesting corpus..."):
                        from pipeline import ingest
                        tmp_fd, tmp_path = tempfile.mkstemp()
                        try:
                            with os.fdopen(tmp_fd, 'wb') as tmp:
                                tmp.write(uploaded_corpus.getvalue())
                            
                            parser = ingest.CorpusParser()
                            corpus_name_display = os.path.splitext(uploaded_corpus.name)[0]
                            parser.process_file(tmp_path, corpus_name_display)
                            
                            # Exclusively stage the newly ingested corpus
                            st.session_state['last_selection'] = [corpus_name_display]
                            st.session_state['loaded_corpora'] = [] # Don't activate until "Load" is pressed
                            st.success(f"✅ Ingested '{corpus_name_display}'. Now select it below and click 'Load Corpora'.")
                        finally:
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)
                        
                        st.cache_data.clear()
                        st.rerun()
        else:
            # Use built-in corpora
            disk_corpora_map = get_disk_corpora()
            indexed_corpora = get_corpora()
            
            # Helper to map common filenames to cleaner names
            def clean_name(n):
                if "EN-BPPT" in n: return "EN-BPPT"
                if "KOSLAT" in n: return "KOSLAT"
                return n

            available_on_disk = [c for c in disk_corpora_map.keys() if clean_name(c) not in indexed_corpora]
            
            if not available_on_disk:
                st.caption("All built-in corpora are already indexed.")
                if st.button("🔄 Refresh List"):
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.caption("Available built-in files found:")
                for c in available_on_disk:
                    display_n = clean_name(c)
                    cols = st.columns([3, 1])
                    cols[0].write(f"📄 {display_n}")
                    if cols[1].button("📥 Index", key=f"index_btn_{c}"):
                        with st.status(f"Indexing '{display_n}'...", expanded=True) as status:
                            from pipeline import ingest
                            parser = ingest.CorpusParser()
                            f_path = os.path.join(CORPORA_DIR, disk_corpora_map[c])
                            parser.process_file(f_path, display_n)
                            status.update(label=f"Finished indexing {display_n}!", state="complete", expanded=False)
                        
                        # Just Stage it, don't auto-load
                        st.session_state['last_selection'] = list(set(st.session_state.get('last_selection', []) + [display_n]))
                        st.cache_data.clear()
                        st.rerun()

    # --- Personal Overrides File (Persistence) ---
    with st.sidebar.expander("🛠️ Personal Overrides Management", expanded=True):
        
        def select_folder():
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            folder_path = filedialog.askdirectory(master=root)
            root.destroy()
            return folder_path

        def select_file():
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            file_path = filedialog.askopenfilename(master=root, filetypes=[("JSON files", "*.json")])
            root.destroy()
            return file_path

        col_a, col_b = st.columns(2)
        if col_a.button("📂 Select Existing", help="Pick an existing JSON file from your computer."):
            picked_file = select_file()
            if picked_file:
                st.session_state['personal_file_path'] = picked_file
                st.session_state['overrides'] = load_overrides(picked_file)
                st.success("Loaded personal file!")
                st.rerun()

        if col_b.button("📁 New: Select Folder", help="Select a folder where you want to create a new modification file."):
            picked_folder = select_folder()
            if picked_folder:
                st.session_state['temp_folder'] = picked_folder
        
        if 'temp_folder' in st.session_state:
            with st.container():
                st.caption(f"Folder: {st.session_state['temp_folder']}")
                new_fn = st.text_input("New Filename", value="personal_modifications.json")
                if st.button("✅ Confirm & Create"):
                    full_path = os.path.join(st.session_state['temp_folder'], new_fn)
                    st.session_state['personal_file_path'] = full_path
                    if not os.path.exists(full_path):
                        save_overrides(full_path, {})
                    del st.session_state['temp_folder']
                    st.rerun()

        p_path = st.session_state.get('personal_file_path', 'personal_overrides.json')
        st.info(f"**This is your personal modification file:**\n`{p_path}`")
        st.session_state['personal_file_path'] = p_path

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
    st.sidebar.title("🔍 CORPUS SEARCH")
    
    indexed_corpora = get_corpora()
    disk_corpora_map = get_disk_corpora()
    
    # Helper to map common filenames to cleaner names
    def clean_name(n):
        if "EN-BPPT" in n: return "EN-BPPT"
        if "KOSLAT" in n: return "KOSLAT"
        return n

    # Create a mapping of clean_name -> actual_key/disk_filename for reverse lookup
    clean_to_disk = {clean_name(k): k for k in disk_corpora_map.keys()}
    
    # All display options: combines indexed names and cleaned disk names
    all_options = sorted(list(set(indexed_corpora) | set(clean_to_disk.keys())))
    
    # Reset default if nothing set (Ensure clean startup)
    if 'last_selection' not in st.session_state:
        st.session_state['last_selection'] = []
    
    if 'loaded_corpora' not in st.session_state:
        st.session_state['loaded_corpora'] = []

    default_sel = [v for v in st.session_state['last_selection'] if v in all_options]
    
    active_corpora = st.session_state['loaded_corpora']
    
    if not active_corpora:
        st.sidebar.warning("⚠️ No Corpora Loaded")
    else:
        st.sidebar.success(f"Loaded: {len(active_corpora)} items")

    selection = st.sidebar.multiselect(
        "Choose corpora to index/load:",
        options=all_options,
        default=default_sel,
        key="corpus_multiselect"
    )
    st.session_state['last_selection'] = selection

    col1, col2 = st.sidebar.columns(2)
    if col1.button("🔄 Load Selected", type="primary", use_container_width=True):
        # Trigger Indexing for unindexed items (using clean -> disk mapping)
        for c in selection:
            # c is the clean name from multiselect
            if c not in indexed_corpora and c in clean_to_disk:
                disk_key = clean_to_disk[c] # e.g. "EN-BPPT-tagged"
                with st.status(f"Indexing '{c}'...", expanded=True) as status:
                    from pipeline import ingest
                    parser = ingest.CorpusParser()
                    f_path = os.path.join(CORPORA_DIR, disk_corpora_map[disk_key])
                    parser.process_file(f_path, c)
                    status.update(label=f"Finished indexing {c}!", state="complete", expanded=False)
        
        st.session_state['loaded_corpora'] = selection
        st.cache_data.clear()
        st.rerun()

    if col2.button("✖️ Deselect All", use_container_width=True):
        st.session_state['last_selection'] = []
        st.session_state['loaded_corpora'] = []
        st.rerun()

    st.sidebar.divider()
    
    # If nothing loaded, stop here
    if not active_corpora:
        st.sidebar.info("💡 Select corpora above and click **'Load Selected'** to begin.")
        if st.sidebar.button("🔍 Diagnose Statistics"):
             from stats.frequency import get_total_tokens
             st.sidebar.write(f"Global Tokens: {get_total_tokens()}")
             st.sidebar.write("Subset Tokens: 0 (No corpora loaded)")
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
