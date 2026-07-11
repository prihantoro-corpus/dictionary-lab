import streamlit as st
import duckdb
import os
import json
import tempfile
from pipeline.indexing import get_connection
import math

CACHE_COLUMNS = ['id', 'token', 'tag', 'lemma', 'corpus', 'file_id', 'sentence_id', 'doc_id', 'sentence_num']
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
            if not is_parallel:
                st.caption("Select Source Language:")
                st.session_state['corpus_language'] = st.selectbox(
                    "Source Language", 
                    ['English', 'Indonesian', 'Chinese', 'Japanese', 'Korean', 'Arabic', 'Javanese', 'Other'], 
                    index=['English', 'Indonesian', 'Chinese', 'Japanese', 'Korean', 'Arabic', 'Javanese', 'Other'].index(st.session_state.get('corpus_language', 'English')) if st.session_state.get('corpus_language', 'English') in ['English', 'Indonesian', 'Chinese', 'Japanese', 'Korean', 'Arabic', 'Javanese', 'Other'] else 7,
                    key="mono_lang"
                )
            else:
                st.info("🔗 **Parallel Mode Active**")
                colA, colB = st.columns(2)
                with colA:
                    st.session_state['corpus_language'] = st.selectbox("Source Language", ['English', 'Indonesian', 'Chinese', 'Japanese', 'Korean', 'Arabic', 'Javanese', 'Other'], index=0, key="p_src_lang")
                with colB:
                    st.session_state['target_language'] = st.selectbox("Target Language", ['English', 'Indonesian', 'Chinese', 'Japanese', 'Korean', 'Arabic', 'Javanese', 'Other'], index=1, key="p_tgt_lang")

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
                available_corpora = sorted([clean_name(c) for c in disk_corpora_map.keys()])
                if not available_corpora:
                    st.warning("No built-in corpora found.")
                    st.session_state['staged_parallel'] = None
                else:
                    if not is_parallel:
                        st.caption("📚 Select from available built-in corpora:")
                        selected_builtin = st.multiselect("Choose corpora:", options=available_corpora, key="mono_builtin")
                        st.session_state['staged_builtin'] = selected_builtin
                    else:
                        st.markdown("**1. Source Corpus**")
                        src_selection = st.selectbox("Select Source Corpus", options=available_corpora, key="para_src_builtin")
                        st.markdown("**2. Target Corpus**")
                        tgt_selection = st.selectbox("Select Target Corpus", options=available_corpora, key="para_tgt_builtin")
                        st.session_state['staged_parallel'] = (src_selection, tgt_selection) if src_selection and tgt_selection else None

            elif st.session_state['corpus_selection_mode'] == "Online Corpus":
                st.caption("🌐 Build Corpus from Online Sources:")
                online_mode = st.radio("Source Mode", ["YouTube", "Mastodon", "BlueSky", "Link Collection", "Keyword Search"], horizontal=True)
                st.session_state['online_builder_mode'] = online_mode
                
                if online_mode == "YouTube":
                    st.session_state['online_url'] = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")
                    st.session_state['online_yt_mode'] = st.selectbox("What to extract?", ["both", "transcript", "comments"])
                elif online_mode == "Mastodon" or online_mode == "BlueSky":
                    urls = st.text_area(f"{online_mode} URLs (one per line)", placeholder="https://...")
                    st.session_state['online_urls'] = [u.strip() for u in urls.split('\n') if u.strip()]
                    st.session_state['online_social_mode'] = st.selectbox("Extract:", ["both", "post", "replies"])
                elif online_mode == "Link Collection":
                    urls = st.text_area("URLs to scrape (one per line)", placeholder="https://...")
                    st.session_state['online_urls'] = [u.strip() for u in urls.split('\n') if u.strip()]
                elif online_mode == "Keyword Search":
                    kw = st.text_input("Keywords (comma separated)", placeholder="corpus linguistics, parsing")
                    st.session_state['online_keywords'] = [k.strip() for k in kw.split(',') if k.strip()]
                    
                    st.session_state['online_max_links'] = st.selectbox("Max Links to Fetch", [25, 50, 75, 100], index=1)
                    
                    if st.button("🔍 Find Links"):
                        if not st.session_state['online_keywords']:
                            st.warning("Please provide keywords.")
                        else:
                            with st.spinner("Searching for links..."):
                                from pipeline.online_corpus import build_online_corpus
                                params = {
                                    'keywords': st.session_state['online_keywords'],
                                    'max_results': st.session_state['online_max_links']
                                }
                                links, _ = build_online_corpus("keyword_fetch", params)
                                if links:
                                    st.session_state['keyword_found_links'] = links
                                else:
                                    st.warning("No links found.")
                                    if 'keyword_found_links' in st.session_state:
                                        del st.session_state['keyword_found_links']
                                        
                    if st.session_state.get('keyword_found_links'):
                        st.session_state['online_links_to_scrape'] = st.multiselect(
                            "Select links to scrape (Easy-to-scrape domains at the top)", 
                            options=st.session_state['keyword_found_links'], 
                            default=st.session_state['keyword_found_links']
                        )
                        
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
                                parser.process_file(tmp_path, corpus_name_display, lang_code=st.session_state.get('corpus_language', 'English'))
                                loaded_names.append(corpus_name_display)
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
                
                def load_parallel_unit(selection, label):
                   if isinstance(selection, str):
                       # Built-in logic
                       if selection in clean_to_disk:
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
                
                for corpus_clean_name in st.session_state['staged_builtin']:
                    with st.spinner(f"Loading {corpus_clean_name}..."):
                        if corpus_clean_name in clean_to_disk:
                            disk_key = clean_to_disk[corpus_clean_name]
                            f_path = os.path.join(CORPORA_DIR, disk_corpora_map[disk_key])
                            try:
                                parser.process_file(f_path, corpus_clean_name, lang_code=st.session_state.get('corpus_language', 'English'))
                                loaded_names.append(corpus_clean_name)
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
                
                # Clear staged items
                st.session_state['staged_files'] = []
                st.session_state['staged_builtin'] = []
                st.session_state['corpus_selection_mode'] = None
                
                st.cache_data.clear()
                file_names = ", ".join(loaded_names + [f"{ext}" for ext in []])
                st.session_state['corpus_loaded_success_msg'] = f"corpus loaded successfully: '{', '.join(loaded_names)}'"
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
        # Initialize or fetch Ollama models
        if 'ollama_models' not in st.session_state or not st.session_state['ollama_models']:
            try:
                from utils.ai_helper import AIHelper
                temp_helper = AIHelper(provider="ollama")
                res = temp_helper.test_connection()
                if res['success']:
                    st.session_state['ollama_models'] = res['models']
                else:
                    st.session_state['ollama_models'] = ["llama3.2", "llama3.1", "mistral", "phi"]
            except:
                st.session_state['ollama_models'] = ["llama3.2", "llama3.1", "mistral", "phi"]
        
        # Ensure default models are in the list if they are standard but not pulled yet
        base_models = ["llama3.2", "llama3.1", "mistral", "phi"]
        for bm in base_models:
            if bm not in st.session_state['ollama_models']:
                st.session_state['ollama_models'].append(bm)
        
        # Model Dropdown
        display_models = sorted(list(set(st.session_state['ollama_models']))) + ["custom"]
        
        # Ensure currently selected model is in the list
        curr_model = st.session_state.get('ollama_model', 'llama3.2')
        if curr_model not in display_models:
            display_models = [curr_model] + display_models

        ollama_model = st.sidebar.selectbox(
            "Ollama Model",
            display_models,
            key="ollama_model",
            help="Select the Ollama model to use"
        )
        if ollama_model == "custom":
            st.sidebar.text_input(
                "Custom Model Name",
                key="ollama_custom_model",
                placeholder="model:tag"
            )
        
        col_test, col_refresh = st.sidebar.columns(2)
        
        # Test connection button
        if col_test.button("Test Connection", key="test_ollama", use_container_width=True):
            try:
                from utils.ai_helper import AIHelper
                model = ollama_model if ollama_model != "custom" else st.session_state.get('ollama_custom_model', 'llama3.2')
                helper = AIHelper(provider="ollama", model=model)
                result = helper.test_connection()
                if result['success']:
                    st.session_state['ollama_models'] = result['models']
                    models_str = ", ".join(result.get('models', []))
                    st.sidebar.success(f"✅ {result['message']}\n\n**Models:** {models_str}")
                else:
                    st.sidebar.error(result['message'])
            except Exception as e:
                st.sidebar.error(f"Connection failed: {str(e)}")
        
        if col_refresh.button("Refresh Models", key="refresh_ollama", use_container_width=True):
            try:
                from utils.ai_helper import AIHelper
                temp_helper = AIHelper(provider="ollama")
                res = temp_helper.test_connection()
                if res['success']:
                    st.session_state['ollama_models'] = res['models']
                    st.sidebar.success(f"Fetched {len(res['models'])} models")
                    st.rerun()
                else:
                    st.sidebar.error("Could not fetch models. Is Ollama running?")
            except Exception as e:
                st.sidebar.error(f"Fetch failed: {e}")
        
        st.sidebar.caption("💡 Make sure Ollama is running on localhost:11434")
        
    elif ai_provider == "Google Gemini":
        api_key = st.sidebar.text_input(
            "Gemini API Key",
            type="password",
            key="gemini_api_key",
            help="Get your API key from https://aistudio.google.com/apikey"
        )
        
        gemini_model = st.sidebar.selectbox(
            "Gemini Model",
            ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
            key="gemini_model"
        )
        
        # Test connection button
        if api_key and st.sidebar.button("Test Gemini Connection", key="test_gemini"):
            try:
                from utils.ai_helper import AIHelper
                helper = AIHelper(provider="gemini", api_key=api_key, model=gemini_model)
                result = helper.test_connection()
                if result['success']:
                    st.sidebar.success(result['message'])
                else:
                    st.sidebar.error(result['message'])
            except Exception as e:
                st.sidebar.error(f"Connection failed: {str(e)}")
        
        # Save API key option
        if api_key and st.sidebar.checkbox("Save API key locally", key="save_gemini_key"):
            config_path = os.path.join(os.getcwd(), ".gemini_config.json")
            try:
                with open(config_path, 'w') as f:
                    json.dump({"api_key": api_key}, f)
                st.sidebar.success("API key saved to .gemini_config.json")
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
