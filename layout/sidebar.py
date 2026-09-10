import streamlit as st
import duckdb
import os
import json
import tempfile
import time
from pipeline.indexing import get_connection
import math

CACHE_COLUMNS = ['id', 'token', 'tag', 'lemma', 'corpus', 'file_id', 'sentence_id', 'doc_id', 'sentence_num']
from pipeline.overrides_io import load_overrides, save_overrides

CORPORA_DIR = os.path.join(os.getcwd(), "corpora")

@st.cache_data
def get_corpora():
    """Returns list of corpora names already indexed as .duckdb files."""
    corpora = []
    
    # 1. Search corpora directory
    if os.path.exists(CORPORA_DIR):
        for f in os.listdir(CORPORA_DIR):
            if f.endswith('.duckdb'):
                corpora.append(os.path.splitext(f)[0])
                
    # 2. Search root directory (for explicitly tracked large corpora like bawe.duckdb)
    root_dir = os.getcwd()
    for f in os.listdir(root_dir):
        if f.endswith('.duckdb') and f != 'dictionary.duckdb' and not f.startswith('test'):
            name = os.path.splitext(f)[0]
            if name not in corpora:
                corpora.append(name)
                
    return sorted(corpora)

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

def clean_name(n):
    """Helper to map common filenames to cleaner names."""
    if "EN-BPPT" in n: return "EN-BPPT"
    if "KOSLAT" in n: return "KOSLAT"
    return n

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

        if key in CACHE_COLUMNS:
            query = f"SELECT DISTINCT {key} as v FROM tokens WHERE 1=1 {where_sql} ORDER BY v"
        else:
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
    # Inject CSS fix for selectbox dropdown popover clickability and top z-index
    st.markdown(
        """
        <style>
        div[data-baseweb="select"] {
            z-index: 1000 !important;
            pointer-events: auto !important;
        }
        div[data-baseweb="popover"], div[data-baseweb="menu"], div[role="listbox"], ul[role="listbox"] {
            z-index: 999999 !important;
            pointer-events: auto !important;
        }
        li[role="option"] {
            cursor: pointer !important;
            pointer-events: auto !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Manual Link at the top
    st.sidebar.markdown(
        '<div style="text-align: left; margin-bottom: 10px;">'
        '<a href="https://docs.google.com/document/d/1x-arcEkxjMc_9DeBYZUcGxnrWl0JW0Bj5_N6o_Jfyfc/edit?usp=drive_link" '
        'target="_blank" style="text-decoration: none; color: #1976d2; font-size: 16px; font-weight: bold;">'
        '📖 Manual</a><br/>'
        '<span style="font-size: 12px; color: gray;">Version 110726</span>'
        '</div>',
        unsafe_allow_html=True
    )
    st.sidebar.title("DICTIONARY EDITOR")
    
    # Initialize session state
    if 'is_parallel' not in st.session_state:
        st.session_state['is_parallel'] = False
    if 'corpus_language' not in st.session_state:
        st.session_state['corpus_language'] = 'English'
    if 'target_language' not in st.session_state:
        st.session_state['target_language'] = 'Indonesian'
    
    # --- Corpus Selection Section ---
    with st.sidebar.expander("📁 Corpus Selection", expanded=True):
        # 1. Choose Parallel vs Monolingual
        is_parallel = st.toggle("Parallel Corpus Mode", value=st.session_state['is_parallel'])
        st.session_state['is_parallel'] = is_parallel

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
            col1, col2, col3 = st.columns(3)
            
            if col1.button("📤 File Upload", use_container_width=True):
                st.session_state['corpus_selection_mode'] = "File Upload"
                st.rerun()
            
            if col2.button("📚 Built-in", use_container_width=True):
                st.session_state['corpus_selection_mode'] = "Built-in Corpora"
                st.rerun()
                
            if col3.button("🌐 Online", use_container_width=True):
                st.session_state['corpus_selection_mode'] = "Online Corpus"
                st.rerun()

        if st.session_state['corpus_selection_mode'] is not None:
            lang_options = ['English', 'Indonesian', 'Spanish', 'French', 'German', 'Italian', 'Portuguese', 'Chinese', 'Japanese', 'Korean', 'Arabic', 'Javanese', 'Other']
            if not is_parallel:
                st.caption("Select Source Language:")
                if 'corpus_language' not in st.session_state or st.session_state['corpus_language'] not in lang_options:
                    st.session_state['corpus_language'] = 'English'
                st.radio(
                    "Source Language", 
                    lang_options, 
                    key="corpus_language"
                )
            else:
                st.info("🔗 **Parallel Mode Active**")
                colA, colB = st.columns(2)
                with colA:
                    if 'corpus_language' not in st.session_state or st.session_state['corpus_language'] not in lang_options:
                        st.session_state['corpus_language'] = 'English'
                    st.radio(
                        "Source Language", 
                        lang_options, 
                        key="corpus_language"
                    )
                with colB:
                    if 'target_language' not in st.session_state or st.session_state['target_language'] not in lang_options:
                        st.session_state['target_language'] = 'Indonesian'
                    st.radio(
                        "Target Language", 
                        lang_options, 
                        key="target_language"
                    )

            # Step 2: Show appropriate interface based on mode
            if st.session_state['corpus_selection_mode'] == "File Upload":
                if not is_parallel:
                    st.caption("📤 Upload one or more corpus files:")
                    uploaded_files = st.file_uploader("Select files", type=None, accept_multiple_files=True, key="mono_upload")
                    if uploaded_files:
                        st.session_state['staged_files'] = uploaded_files
                        st.info(f"📋 **{len(uploaded_files)} file(s) selected**")
                    else:
                        st.session_state['staged_files'] = []
                else:
                    st.markdown("**1. Source Corpus**")
                    src_selection = st.file_uploader("Upload Source File", type=['xml', 'txt'], key="ups_src")
                    st.markdown("**2. Target Corpus**")
                    tgt_selection = st.file_uploader("Upload Target File", type=['xml', 'txt'], key="ups_tgt")
                    st.session_state['staged_parallel'] = (src_selection, tgt_selection) if src_selection and tgt_selection else None

            elif st.session_state['corpus_selection_mode'] == "Built-in Corpora":
                disk_corpora_map = get_disk_corpora()
                db_corpora = get_corpora()
                available_corpora = sorted(list(set([clean_name(c) for c in disk_corpora_map.keys()] + db_corpora)))
                if not available_corpora:
                    st.warning("No built-in or indexed corpora found.")
                    st.session_state['staged_parallel'] = None
                else:
                    if not is_parallel:
                        st.caption("📚 Select from available built-in corpora:")
                        mode_b = st.radio("Selection Mode", ["Single Corpus (Radio)", "Multiple Corpora (Checkboxes)"], horizontal=True, key="builtin_select_mode")
                        if mode_b == "Single Corpus (Radio)":
                            chosen_corpus = st.radio("Choose corpus:", options=available_corpora, key="mono_builtin_radio")
                            st.session_state['staged_builtin'] = [chosen_corpus] if chosen_corpus else []
                        else:
                            selected_builtin = []
                            st.caption("Select corpora to load:")
                            for corp in available_corpora:
                                if st.checkbox(corp, value=True, key=f"builtin_cb_{corp}"):
                                    selected_builtin.append(corp)
                            st.session_state['staged_builtin'] = selected_builtin
                    else:
                        st.markdown("**1. Source Corpus**")
                        src_selection = st.radio("Select Source Corpus", options=available_corpora, key="para_src_builtin")
                        st.markdown("**2. Target Corpus**")
                        tgt_selection = st.radio("Select Target Corpus", options=available_corpora, key="para_tgt_builtin")
                        st.session_state['staged_parallel'] = (src_selection, tgt_selection) if src_selection and tgt_selection else None

            elif st.session_state['corpus_selection_mode'] == "Online Corpus":
                st.caption("🌐 Build Corpus from Online Sources:")
                online_mode = st.radio("Source Mode", ["YouTube", "Mastodon", "BlueSky", "Link Collection", "Keyword Search"], horizontal=True, key="online_mode_radio")
                st.session_state['online_builder_mode'] = online_mode
                
                if online_mode == "YouTube":
                    st.session_state['online_url'] = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...", key="online_yt_url")
                    st.session_state['online_yt_mode'] = st.radio("What to extract?", ["both", "transcript", "comments"], horizontal=True, key="online_yt_mode_sb")
                elif online_mode == "Mastodon" or online_mode == "BlueSky":
                    urls = st.text_area(f"{online_mode} URLs (one per line)", placeholder="https://...", key="online_social_urls")
                    st.session_state['online_urls'] = [u.strip() for u in urls.split('\n') if u.strip()]
                    st.session_state['online_social_mode'] = st.radio("Extract:", ["both", "post", "replies"], horizontal=True, key="online_social_mode_sb")
                elif online_mode == "Link Collection":
                    urls = st.text_area("URLs to scrape (one per line)", placeholder="https://...", key="online_link_coll_urls")
                    st.session_state['online_urls'] = [u.strip() for u in urls.split('\n') if u.strip()]
                elif online_mode == "Keyword Search":
                    kw = st.text_input("Keywords (comma separated)", placeholder="corpus linguistics, parsing", key="online_kw_input")
                    st.session_state['online_keywords'] = [k.strip() for k in kw.split(',') if k.strip()]
                    
                    st.session_state['online_max_links'] = st.radio("Max Links to Fetch", [25, 50, 75, 100], index=1, horizontal=True, key="online_max_links_sb")
                    
                    if st.button("🔍 Find Links"):
                        if not st.session_state['online_keywords']:
                            st.warning("Please provide keywords.")
                        else:
                            with st.spinner("Searching for links..."):
                                from pipeline.online_corpus import build_online_corpus
                                params = {
                                    'keywords': st.session_state['online_keywords'],
                                    'max_results': st.session_state['online_max_links'],
                                    'language': st.session_state.get('corpus_language', 'English')
                                }
                                links, _ = build_online_corpus("keyword_fetch", params)
                                if links:
                                    st.session_state['keyword_found_links'] = links
                                else:
                                    st.warning("No links found.")
                                    if 'keyword_found_links' in st.session_state:
                                        del st.session_state['keyword_found_links']
                                        
                    if st.session_state.get('keyword_found_links'):
                        st.caption("Select links to scrape (Easy-to-scrape domains at top):")
                        scraped_links = []
                        for link in st.session_state['keyword_found_links']:
                            if st.checkbox(link, value=True, key=f"online_link_cb_{link}"):
                                scraped_links.append(link)
                        st.session_state['online_links_to_scrape'] = scraped_links
                        
                        if st.session_state['online_links_to_scrape']:
                            est_time = max(1, len(st.session_state['online_links_to_scrape']) // 15)
                            if is_parallel:
                                est_time = max(1, len(st.session_state['online_links_to_scrape']) // 3) # Much longer for sentence-by-sentence translation
                            st.info(f"⏱️ Estimated processing time: ~{est_time} minute(s)")
        
        # Step 3: Load Corpus button
        st.divider()
        if not is_parallel:
            has_staged_content = False
            if st.session_state['corpus_selection_mode'] == "File Upload" and st.session_state.get('staged_files'):
                has_staged_content = True
            elif st.session_state['corpus_selection_mode'] == "Built-in Corpora" and st.session_state.get('staged_builtin'):
                has_staged_content = True
            elif st.session_state['corpus_selection_mode'] == "Online Corpus":
                has_staged_content = True
        else:
            if st.session_state.get('corpus_selection_mode') == "Online Corpus":
                has_staged_content = True
            else:
                has_staged_content = st.session_state.get('staged_parallel') is not None
        
        if st.button("🚀 Load Corpus", type="primary", use_container_width=True, disabled=not has_staged_content):
            start_time_total = time.time()
            loaded_names = []
            
            # 1. Process Monolingual Uploads
            if not is_parallel and st.session_state['corpus_selection_mode'] == "File Upload" and st.session_state['staged_files']:
                from pipeline import ingest
                parser = ingest.CorpusParser()
                
                for uploaded_file in st.session_state['staged_files']:
                    with st.spinner(f"Processing {uploaded_file.name}..."):
                        tmp_fd, tmp_path = tempfile.mkstemp()
                        try:
                            with os.fdopen(tmp_fd, 'wb') as tmp:
                                tmp.write(uploaded_file.getvalue())
                            
                            corpus_name_display = os.path.splitext(uploaded_file.name)[0]
                            try:
                                start_time = time.time()
                                parser.process_file(tmp_path, corpus_name_display, lang_code=st.session_state.get('corpus_language', 'English'))
                                end_time = time.time()
                                loaded_names.append(corpus_name_display)
                                st.success(f"Corpus '{corpus_name_display}' successfully loaded in {end_time - start_time:.2f} seconds.")
                            except Exception as e:
                                if "used by another process" in str(e):
                                    st.error(f"❌ Failed to load {uploaded_file.name}: Database locked by another process.")
                                else:
                                    st.error(f"❌ Failed to load {uploaded_file.name}: {e}")
                        finally:
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)
            
            # 2. Process Parallel Uploads
            elif is_parallel and st.session_state.get('staged_parallel'):
                src_selection, tgt_selection = st.session_state['staged_parallel']
                from pipeline import ingest
                parser = ingest.CorpusParser()
                disk_corpora_map = get_disk_corpora()
                clean_to_disk = {clean_name(k): k for k in disk_corpora_map.keys()}
                
                db_corpora = get_corpora()
                def load_parallel_unit(selection, label):
                   if isinstance(selection, str):
                       # Built-in logic
                       if selection in db_corpora:
                           return selection
                       elif selection in clean_to_disk:
                           disk_key = clean_to_disk[selection]
                           f_path = os.path.join(CORPORA_DIR, disk_corpora_map[disk_key])
                           parser.process_file(f_path, selection, lang_code=st.session_state.get('corpus_language') if label == "SRC" else st.session_state.get('target_language'))
                           return selection
                       return None
                   else:
                       # Upload logic
                       tmp_fd, tmp_path = tempfile.mkstemp()
                       try:
                           with os.fdopen(tmp_fd, 'wb') as tmp:
                               tmp.write(selection.getvalue())
                           name = os.path.splitext(selection.name)[0]
                           parser.process_file(tmp_path, name, lang_code=st.session_state.get('corpus_language') if label == "SRC" else st.session_state.get('target_language'))
                           return name
                       finally:
                           if os.path.exists(tmp_path): os.remove(tmp_path)

                with st.spinner("Processing Source..."):
                    src_name = load_parallel_unit(src_selection, "SRC")
                with st.spinner("Processing Target..."):
                    tgt_name = load_parallel_unit(tgt_selection, "TGT")
                
                loaded_names = [src_name, tgt_name]
                st.session_state['parallel_pair'] = (src_name, tgt_name)
                
                # Alignment Check (Simple sentence count check)
                conn, _ = get_connection()
                src_count = conn.execute("SELECT COUNT(DISTINCT sentence_id) FROM tokens WHERE corpus=?", (src_name,)).fetchone()[0]
                tgt_count = conn.execute("SELECT COUNT(DISTINCT sentence_id) FROM tokens WHERE corpus=?", (tgt_name,)).fetchone()[0]
                
                if src_count != tgt_count:
                    st.warning(f"⚠️ **Alignment Warning**: Source has {src_count} sentences, Target has {tgt_count}. Results may mismatch.")
                else:
                    st.success(f"✅ Parallel Corpora perfectly aligned ({src_count} sentences).")
            
            # Process Online Corpus
            elif st.session_state['corpus_selection_mode'] == "Online Corpus":
                from pipeline import ingest
                from pipeline.online_corpus import build_online_corpus
                parser = ingest.CorpusParser()
                
                mode = st.session_state.get('online_builder_mode', '').lower().replace(' ', '_')
                if mode == "link_collection": mode = "links"
                if mode == "keyword_search": mode = "keyword"
                
                params = {}
                if mode == "youtube":
                    params['url'] = st.session_state.get('online_url', '')
                    params['mode'] = st.session_state.get('online_yt_mode', 'both')
                elif mode in ("mastodon", "bluesky", "links"):
                    params['urls'] = st.session_state.get('online_urls', [])
                    params['links'] = st.session_state.get('online_urls', [])
                    params['mode'] = st.session_state.get('online_social_mode', 'both')
                elif mode == "keyword":
                    params['keywords'] = st.session_state.get('online_keywords', [])
                    if 'online_links_to_scrape' in st.session_state:
                        mode = "keyword_scrape"
                        params['links'] = st.session_state['online_links_to_scrape']
                    else:
                        st.error("Please click 'Find Links' and select links first.")
                        st.stop()
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def ui_progress_callback(fraction, message):
                    progress_bar.progress(fraction)
                    status_text.text(message)
                    
                files, warning = build_online_corpus(mode, params, progress_callback=ui_progress_callback)
                    
                if warning:
                    st.warning(warning)
                        
                if files:
                    corpus_clean_name = f"Online_{mode.capitalize()}"
                    if mode == "keyword_scrape":
                        corpus_clean_name = "Online_Keyword"
                    
                    # Show which URLs were scraped
                    scraped_urls = [f.get('url') for f in files if f.get('url')]
                    if scraped_urls:
                        with st.expander(f"🌐 Successfully scraped {len(scraped_urls)} webpages"):
                            for u in scraped_urls:
                                st.markdown(f"- [{u}]({u})")
                    
                    # Combine all files into one big file and ingest it
                    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".txt")
                    try:
                        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as tmp:
                            for file_data in files:
                                tmp.write(file_data['content'])
                                tmp.write("\n")
                        
                        if not is_parallel:
                            status_text.text(f"Starting NLP processing for {corpus_clean_name}...")
                            parser.process_file(tmp_path, corpus_clean_name, lang_code=st.session_state.get('corpus_language', 'English'), progress_callback=ui_progress_callback)
                            loaded_names.append(corpus_clean_name)
                        else:
                            import spacy
                            from pipeline.translator import translate_sentences
                            
                            status_text.text("Segmenting sentences for parallel translation...")
                            # Segment using SpaCy Sentencizer before translation
                            with open(tmp_path, 'r', encoding='utf-8') as f:
                                raw_text = f.read()
                                
                            nlp = spacy.blank("en")
                            nlp.add_pipe('sentencizer')
                            # Because it could be very large, parse in chunks if needed. For 500k words, it's fine.
                            doc = nlp(raw_text)
                            sentences = [s.text.strip() for s in doc.sents if s.text.strip()]
                            
                            # Auto-translate
                            target_lang = st.session_state.get('target_language', 'English')
                            translated_sentences = translate_sentences(sentences, target_lang, progress_callback=ui_progress_callback)
                            
                            # Ingest both!
                            src_name = f"{corpus_clean_name}_SRC"
                            tgt_name = f"{corpus_clean_name}_TGT"
                            
                            tmp_fd_src, tmp_path_src = tempfile.mkstemp(suffix=".txt")
                            tmp_fd_tgt, tmp_path_tgt = tempfile.mkstemp(suffix=".txt")
                            
                            try:
                                with os.fdopen(tmp_fd_src, 'w', encoding='utf-8') as fs:
                                    fs.write("\n".join(sentences))
                                with os.fdopen(tmp_fd_tgt, 'w', encoding='utf-8') as ft:
                                    ft.write("\n".join(translated_sentences))
                                    
                                status_text.text(f"Ingesting Source Corpus ({src_name})...")
                                parser.process_file(tmp_path_src, src_name, lang_code=st.session_state.get('corpus_language', 'English'), progress_callback=ui_progress_callback)
                                
                                status_text.text(f"Ingesting Target Corpus ({tgt_name})...")
                                parser.process_file(tmp_path_tgt, tgt_name, lang_code=target_lang, progress_callback=ui_progress_callback)
                                
                                loaded_names.extend([src_name, tgt_name])
                                st.session_state['parallel_pair'] = (src_name, tgt_name)
                            finally:
                                if os.path.exists(tmp_path_src): os.remove(tmp_path_src)
                                if os.path.exists(tmp_path_tgt): os.remove(tmp_path_tgt)
                        
                        # Clean up UI state
                        if 'keyword_found_links' in st.session_state:
                            del st.session_state['keyword_found_links']
                    except Exception as e:
                        st.error(f"❌ Failed to process online corpus: {e}")
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                        status_text.empty()
                        progress_bar.empty()
                else:
                    st.error("No content could be retrieved from the online source.")

            # Process built-in corpora
            elif st.session_state['corpus_selection_mode'] == "Built-in Corpora" and st.session_state['staged_builtin']:
                from pipeline import ingest
                parser = ingest.CorpusParser()
                disk_corpora_map = get_disk_corpora()
                
                # Create reverse mapping: clean_name -> disk_key
                clean_to_disk = {clean_name(k): k for k in disk_corpora_map.keys()}
                db_corpora = get_corpora()
                
                for corpus_clean_name in st.session_state['staged_builtin']:
                    with st.spinner(f"Loading {corpus_clean_name}..."):
                        if corpus_clean_name in db_corpora:
                            loaded_names.append(corpus_clean_name)
                        elif corpus_clean_name in clean_to_disk:
                            disk_key = clean_to_disk[corpus_clean_name]
                            f_path = os.path.join(CORPORA_DIR, disk_corpora_map[disk_key])
                            try:
                                start_time = time.time()
                                parser.process_file(f_path, corpus_clean_name, lang_code=st.session_state.get('corpus_language', 'English'))
                                end_time = time.time()
                                loaded_names.append(corpus_clean_name)
                                st.success(f"Corpus '{corpus_clean_name}' successfully loaded in {end_time - start_time:.2f} seconds.")
                            except Exception as e:
                                if "used by another process" in str(e):
                                     st.error(f"❌ Failed to load {corpus_clean_name}: Database locked by another process (Try closing other python scripts).")
                                else:
                                     st.error(f"❌ Failed to load {corpus_clean_name}: {e}")
            
            # Activate loaded corpora immediately
            if loaded_names:
                current_loaded = st.session_state.get('loaded_corpora', [])
                st.session_state['loaded_corpora'] = list(set(current_loaded + loaded_names))
                st.session_state['last_selection'] = st.session_state['loaded_corpora']
                
                # Re-attach databases to the active memory connection
                from pipeline.indexing import get_connection, attach_corpora
                conn, _ = get_connection()
                attach_corpora(conn, st.session_state['loaded_corpora'])
                
                # Clear staged items
                st.session_state['staged_files'] = []
                st.session_state['staged_builtin'] = []
                st.session_state['corpus_selection_mode'] = None
                
                st.cache_data.clear()
                total_time = time.time() - start_time_total
                mins = int(total_time // 60)
                secs = int(total_time % 60)
                time_str = f" Load completed in {mins} minutes and {secs} seconds." if total_time >= 1 else ""
                st.session_state['corpus_loaded_success_msg'] = f"Corpus loaded successfully: '{', '.join(loaded_names)}'.{time_str}"
                st.rerun()
        
        # Reset button
        if st.session_state['corpus_selection_mode'] is not None:
            if st.button("↩️ Back to Selection", use_container_width=True):
                st.session_state['corpus_selection_mode'] = None
                st.session_state['staged_files'] = []
                st.session_state['staged_builtin'] = []
                st.rerun()

    # --- User-Defined Wordlists ---
    with st.sidebar.expander("📝 User-Defined Wordlists", expanded=False):
        st.caption("Upload .txt files to check against your corpus searches. One word per line.")
        uploaded_wordlists = st.file_uploader("Upload Wordlists (.txt)", type=['txt'], accept_multiple_files=True, key="user_wl_upload")
        
        if uploaded_wordlists:
            if st.button("💾 Save Wordlists", use_container_width=True, key="save_wl"):
                from wordlist import manager
                # Ensure wordlist directory exists
                if not os.path.exists("wordlist"):
                    os.makedirs("wordlist")
                    
                saved_count = 0
                for wl_file in uploaded_wordlists:
                    file_path = os.path.join("wordlist", wl_file.name)
                    try:
                        with open(file_path, "wb") as f:
                            f.write(wl_file.getvalue())
                        saved_count += 1
                    except Exception as e:
                        st.error(f"Failed to save {wl_file.name}: {e}")
                
                if saved_count > 0:
                    st.success(f"Saved {saved_count} wordlist(s)!")
                    # Clear the cache so it reloads immediately
                    manager._cache = {}
                    st.rerun()
                    
        # Show existing user lists
        try:
            val_files = [f for f in os.listdir("wordlist") if f.endswith(".txt") and f.lower() != "basic_english.csv"] 
            if val_files:
                st.caption("**Active Wordlists:**")
                if 'active_wordlists' not in st.session_state:
                    st.session_state['active_wordlists'] = {}
                    
                for f in val_files:
                    list_key = f"USER-DEFINED: {os.path.splitext(f)[0].upper()}"
                    # Default to active if newly added
                    if list_key not in st.session_state['active_wordlists']:
                        st.session_state['active_wordlists'][list_key] = True
                        
                    is_active = st.checkbox(f, value=st.session_state['active_wordlists'][list_key], key=f"wl_cb_{f}")
                    st.session_state['active_wordlists'][list_key] = is_active
        except:
            pass

    # --- Personal Overrides File (Persistence) ---
    with st.sidebar.expander("🛠️ Personal Overrides Management", expanded=True):
        st.caption("Manage your personal JSON dictionary file:")
        
        col1, col2 = st.columns(2)
        
        if col1.button("📂 Open Existing", use_container_width=True):
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
            root.destroy()
            
            if file_path:
                st.session_state['personal_file_path'] = file_path
                loaded_data = load_overrides(file_path)
                if loaded_data is not None:
                    st.session_state['overrides'] = loaded_data
                    st.success(f"Loaded from {file_path}!")
                else:
                    st.error("Failed to load file.")
                st.rerun()

        if col2.button("🆕 Create New", use_container_width=True):
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
            root.destroy()
            
            if file_path:
                st.session_state['personal_file_path'] = file_path
                try:
                    save_overrides(file_path, {})
                    st.session_state['overrides'] = {}
                    st.success(f"Created new file: {file_path}")
                except Exception as e:
                    st.error(f"Could not create file: {e}")
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
            try:
                # Close memory connection first so Windows releases file handles
                if 'duckdb_conn' in st.session_state:
                    try:
                        st.session_state.duckdb_conn.close()
                    except: pass
                    del st.session_state['duckdb_conn']
                
                if os.path.exists(CORPORA_DIR):
                    for f in os.listdir(CORPORA_DIR):
                        if f.endswith('.duckdb') or f.endswith('.duckdb.wal'):
                            try: os.remove(os.path.join(CORPORA_DIR, f))
                            except: pass
                
                # Re-initialize empty memory view
                from pipeline.indexing import get_connection, attach_corpora
                conn, _ = get_connection()
                attach_corpora(conn, [])
                
                st.sidebar.warning("Database cleared!")
                st.session_state['loaded_corpora'] = []
                st.session_state['last_selection'] = []
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error clearing: {e}")

    # --- Active Search & Filtering ---
    st.sidebar.divider()
    
    # Check if corpora are loaded
    if 'loaded_corpora' not in st.session_state:
        st.session_state['loaded_corpora'] = []
    
    active_corpora = st.session_state['loaded_corpora']
    
    # In parallel mode, we only search the Source corpus
    if st.session_state.get('is_parallel') and st.session_state.get('parallel_pair'):
        src_name = st.session_state['parallel_pair'][0]
        if src_name in active_corpora:
            active_corpora = [src_name]
    
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

    
    # --- Wordlists Section ---
    from wordlist import manager as wl_manager
    loaded_wlists = wl_manager.load_wordlists()
    
    with st.sidebar.expander("📚 Wordlists", expanded=False):
        st.caption("Active Wordlists for profiling & entry badges:")
        
        if 'active_wordlists' not in st.session_state:
            st.session_state['active_wordlists'] = {}
            
        all_wl_names = list(loaded_wlists.keys())
        if wl_manager.HAS_CEFR and "CEFR" not in all_wl_names:
            all_wl_names.insert(0, "CEFR")
            
        if not all_wl_names:
            st.caption("No wordlists found in `wordlist/` folder.")
        else:
            for wl_name in sorted(all_wl_names):
                if wl_name not in st.session_state['active_wordlists']:
                    st.session_state['active_wordlists'][wl_name] = True
                    
                cb_val = st.checkbox(
                    f"🏷️ {wl_name}",
                    value=st.session_state['active_wordlists'][wl_name],
                    key=f"wl_cb_{wl_name}"
                )
                st.session_state['active_wordlists'][wl_name] = cb_val
                
        st.write("---")
        if st.button("📊 Open Vocabulary Profiler", key="btn_open_profiler", use_container_width=True):
            st.session_state['main_nav'] = "Vocabulary Profiler"
            st.rerun()

    st.sidebar.title("METADATA")
    meta_keys = get_metadata_keys(active_corpora)
    selected_metadata = {}
    
    # ⏱️ Select Feature of Time Attribute in Sidebar
    time_candidate_options = list(meta_keys)
    for col in ['corpus', 'doc_id', 'file_id']:
        if col not in time_candidate_options:
            time_candidate_options.append(col)
            
    if time_candidate_options:
        if 'selected_time_attribute' not in st.session_state or st.session_state['selected_time_attribute'] not in time_candidate_options:
            # Prioritize time-like key if present
            time_words = ['year', 'date', 'month', 'time', 'period', 'decade']
            prioritized = [k for k in time_candidate_options if any(tw in k.lower() for tw in time_words)]
            st.session_state['selected_time_attribute'] = prioritized[0] if prioritized else time_candidate_options[0]
            
        with st.sidebar.expander("⏱️ Feature of Time (Attribute)", expanded=True):
            st.caption("Select metadata or structural field to group time periods:")
            st.radio(
                "Select feature of time:",
                options=time_candidate_options,
                key="selected_time_attribute",
                label_visibility="collapsed"
            )
            
    if not meta_keys:
        st.sidebar.caption("No custom JSON metadata found in loaded corpora.")
    
    for key in meta_keys:
        values = get_metadata_values(key, active_corpora)
        if values and len(values) <= 30:
            with st.sidebar.expander(f"🏷️ {key}", expanded=True):
                selected_vals = []
                for val in values:
                    val_str = str(val)
                    cb_key = f"meta_cb_{key}_{val_str}"
                    if cb_key not in st.session_state:
                        st.session_state[cb_key] = True
                    if st.checkbox(val_str, key=cb_key):
                        selected_vals.append(val)
                selected_metadata[key] = selected_vals
            
    st.sidebar.divider()
    st.sidebar.subheader("Filters")
    skip_punct = st.sidebar.checkbox("Skip Punctuation", value=True)
    stop_words_str = st.sidebar.text_input("N-gram Stop Words", placeholder="in, the, of...")
    col_filter_help = "Advanced Collocate Filtering (word, _TAG, car*, etc.)"
    collocate_filter_str = st.sidebar.text_input("Collocate Filter", placeholder="word, _TAG, ...", help=col_filter_help)
    
    stop_words = [s.strip() for s in stop_words_str.split(',')] if stop_words_str else []
    collocate_filter = [s.strip() for s in collocate_filter_str.split(',')] if collocate_filter_str else []
    
    # AI Assistant Configuration
    st.sidebar.divider()
    st.sidebar.subheader("🤖 AI Assistant")
    
    ai_provider = st.sidebar.radio(
        "AI Provider",
        ["None", "Local (Ollama)", "Google Gemini"],
        key="ai_provider",
        help="Enable AI to help generate dictionary entries"
    )
    
    if ai_provider == "Local (Ollama)":
        from utils.ai_helper import AIHelper, detect_ollama_disk_models, list_ollama_models
        
        # Initialize or fetch Ollama models from API and disk
        if 'ollama_models' not in st.session_state or not st.session_state['ollama_models']:
            st.session_state['ollama_models'] = list_ollama_models()
        
        disk_models = detect_ollama_disk_models()
        all_detected = sorted(list(set(st.session_state['ollama_models'] + disk_models)))
        
        if disk_models:
            st.sidebar.caption(f"💾 **Models Detected on Disk**: `{', '.join(disk_models)}`")
        
        display_models = list(all_detected)
        if "custom" not in display_models:
            display_models.append("custom")
        
        if 'ollama_model' not in st.session_state or st.session_state['ollama_model'] not in display_models:
            st.session_state['ollama_model'] = display_models[0] if display_models else 'llama3.2'

        ollama_model = st.sidebar.radio(
            "Ollama Model",
            display_models,
            key="ollama_model",
            help="Select an Ollama model detected on your hard disk or running server"
        )

        if ollama_model == "custom":
            st.sidebar.text_input(
                "Custom Model Name",
                key="ollama_custom_model",
                placeholder="e.g. qwen2.5:7b, tinyllama:latest"
            )
        
        col_test, col_refresh = st.sidebar.columns(2)
        
        # Test connection button
        if col_test.button("⚡ Test Connection", key="test_ollama", use_container_width=True):
            with st.spinner("Testing Ollama connection..."):
                try:
                    model = ollama_model if ollama_model != "custom" else st.session_state.get('ollama_custom_model', 'llama3.2')
                    helper = AIHelper(provider="ollama", model=model)
                    result = helper.test_connection()
                    if result['success']:
                        st.session_state['ollama_models'] = result.get('models', [])
                        models_str = ", ".join(result.get('models', []))
                        st.sidebar.success(f"✅ {result['message']}\n\n**All Detected Models:** {models_str}")
                    else:
                        st.sidebar.error(f"❌ {result['message']}")
                except Exception as e:
                    st.sidebar.error(f"Connection test failed: {str(e)}")
        
        if col_refresh.button("🔍 Detect Models", key="refresh_ollama", use_container_width=True):
            with st.spinner("Scanning hard disk & Ollama daemon..."):
                found = list_ollama_models()
                st.session_state['ollama_models'] = found
                st.sidebar.success(f"Detected {len(found)} model(s) on hard disk / server!")
                st.rerun()
        
        st.sidebar.caption("💡 Make sure Ollama is installed and running on `localhost:11434`")
        
    elif ai_provider == "Google Gemini":
        from utils.ai_helper import AIHelper, list_gemini_models
        
        # Load saved API key if available and not yet set
        if not st.session_state.get('gemini_api_key'):
            config_path = os.path.join(os.getcwd(), ".gemini_config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        if 'api_key' in config:
                            st.session_state['gemini_api_key'] = config['api_key']
                except:
                    pass

        api_key = st.sidebar.text_input(
            "Gemini API Key",
            type="password",
            key="gemini_api_key",
            help="Get your API key from https://aistudio.google.com/apikey"
        )
        
        if 'gemini_models' not in st.session_state:
            st.session_state['gemini_models'] = list_gemini_models(api_key if api_key else None)
            
        display_gemini = sorted(list(set(st.session_state['gemini_models'])))
        if "custom" not in display_gemini:
            display_gemini.append("custom")
            
        if 'gemini_model' not in st.session_state or st.session_state['gemini_model'] not in display_gemini:
            st.session_state['gemini_model'] = 'gemini-2.0-flash-exp'
            
        gemini_model = st.sidebar.radio(
            "Gemini Model",
            display_gemini,
            key="gemini_model",
            help="Select official Google Gemini model"
        )

        if gemini_model == "custom":
            st.sidebar.text_input(
                "Custom Gemini Model Name",
                key="gemini_custom_model",
                placeholder="e.g. gemini-2.0-flash, gemini-3.0-preview"
            )
            
        st.sidebar.caption(
            "ℹ️ **Gemini Version Note**: Google Gemini official models are Gemini 2.0 (Flash/Pro) and Gemini 1.5. "
            "If looking for 'Gemini v3', it may refer to Gemini 2.0 or custom preview model names. You can select 'custom' to enter custom model IDs."
        )

        col_test_g, col_fetch_g = st.sidebar.columns(2)

        # Test connection button
        if col_test_g.button("⚡ Test Connection", key="test_gemini", use_container_width=True):
            if not api_key:
                st.sidebar.warning("Please enter your Gemini API key first.")
            else:
                with st.spinner("Testing Gemini connection..."):
                    try:
                        model = gemini_model if gemini_model != "custom" else st.session_state.get('gemini_custom_model', 'gemini-2.0-flash-exp')
                        helper = AIHelper(provider="gemini", api_key=api_key, model=model)
                        result = helper.test_connection()
                        if result['success']:
                            st.sidebar.success(f"✅ {result['message']}")
                            if result.get('models'):
                                st.session_state['gemini_models'] = result['models']
                        else:
                            st.sidebar.error(f"❌ {result['message']}")
                    except Exception as e:
                        st.sidebar.error(f"Connection test failed: {str(e)}")
                        
        if col_fetch_g.button("🔄 Fetch Models", key="fetch_gemini", use_container_width=True):
            if not api_key:
                st.sidebar.warning("Please enter API key first.")
            else:
                with st.spinner("Fetching accessible Gemini models..."):
                    fetched = list_gemini_models(api_key)
                    st.session_state['gemini_models'] = fetched
                    st.sidebar.success(f"Fetched {len(fetched)} Gemini model(s)!")
                    st.rerun()
        
        # Save API key option
        if api_key and st.sidebar.checkbox("Save API key locally", key="save_gemini_key"):
            config_path = os.path.join(os.getcwd(), ".gemini_config.json")
            try:
                with open(config_path, 'w') as f:
                    json.dump({"api_key": api_key}, f)
                st.sidebar.info("API key saved to .gemini_config.json")
            except Exception as e:
                st.sidebar.error(f"Failed to save: {str(e)}")
        
        # Load saved API key
        if not api_key:
            config_path = os.path.join(os.getcwd(), ".gemini_config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        if 'api_key' in config:
                            st.session_state['gemini_api_key'] = config['api_key']
                            st.sidebar.info("Loaded saved API key")
                except:
                    pass


    
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
                if key in CACHE_COLUMNS:
                    if not actual_vals:
                        where_parts.append(f"{key} IS NULL")
                    else:
                        placeholders = ",".join(["?"] * len(actual_vals))
                        where_parts.append(f"({key} IN ({placeholders}) OR {key} IS NULL)")
                        params.extend(actual_vals)
                else:
                    if not actual_vals:
                        where_parts.append(f"json_extract_string(metadata, '$.{key}') IS NULL")
                    else:
                        placeholders = ",".join(["?"] * len(actual_vals))
                        where_parts.append(f"(json_extract_string(metadata, '$.{key}') IN ({placeholders}) OR json_extract_string(metadata, '$.{key}') IS NULL)")
                        params.extend(actual_vals)
            else:
                placeholders = ",".join(["?"] * len(selected_vals))
                if key in CACHE_COLUMNS:
                    where_parts.append(f"{key} IN ({placeholders})")
                else:
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
