
import streamlit as st
import pandas as pd
import eng_to_ipa as ipa
import json
from pipeline import search
from stats import frequency, collocation, kwic
from wordlist import manager
from layout import components
from pipeline.overrides_io import save_overrides

def parse_manual_list(text, delimiter="|"):
    """Parses text area input into a list of dicts/tuples."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    results = []
    for line in lines:
        parts = [p.strip() for p in line.split(delimiter)]
        results.append(parts)
    return results

def cb_update_query(new_term):
    """Callback to update search query."""
    st.session_state.search_box = new_term

def cb_update_query(new_term):
    """Callback to update search query."""
    st.session_state.search_box = new_term

def render_clickable_word_row(label, words, key_prefix="nav", context=""):
    if not words: return
    st.write(f"**{label}**:")
    cols = st.columns(len(words) if len(words) < 10 else 10)
    for i, w in enumerate(words[:20]): # Limit to 20 visually
        cols[i % 10].button(w, key=f"{key_prefix}_{context}_{w}_{i}", on_click=cb_update_query, args=(w,))

def render_sense_editor(token, tag, initial_data):
    """
    Renders a form to edit sense fields.
    initial_data: dict with definition, pronunciation, frequency, etc.
    """
    with st.expander(f"📝 Edit Sense ({tag})", expanded=False):
        new_pron = st.text_input("Pronunciation", value=initial_data.get('pronunciation', ''), key=f"edit_pron_{token}_{tag}")
        new_freq = st.number_input("Frequency", value=int(initial_data.get('frequency', 0)), key=f"edit_freq_{token}_{tag}")
        new_def = st.text_area("Definition", value=initial_data.get('definition', ''), key=f"edit_def_{token}_{tag}")
        
        st.write("---")
        st.caption("Manual Statistics & Examples (Format: 'Item | Value')")
        m_bigrams = st.text_area("Bigrams (manual)", value=initial_data.get('manual_bigrams', ''), placeholder="node word | 10\nword node | 5", key=f"edit_bi_{token}_{tag}")
        m_trigrams = st.text_area("Trigrams (manual)", value=initial_data.get('manual_trigrams', ''), placeholder="node w1 w2 | 3", key=f"edit_tri_{token}_{tag}")
        m_collocs = st.text_area("Collocates (manual)", value=initial_data.get('manual_collocates', ''), placeholder="word | score", key=f"edit_coll_list_{token}_{tag}")
        m_examples = st.text_area("KWIC Examples (manual)", value=initial_data.get('manual_examples', ''), placeholder="left | node | right", key=f"edit_ex_{token}_{tag}")
        m_collo_ex = st.text_area("Collocate Examples (manual)", value=initial_data.get('manual_collo_ex', ''), placeholder="collocate | left | node | right", key=f"edit_collo_ex_{token}_{tag}")

        if st.button("Save Changes", key=f"save_{token}_{tag}"):
            if token not in st.session_state['overrides']:
                st.session_state['overrides'][token] = {}
            st.session_state['overrides'][token][tag] = {
                "pronunciation": new_pron,
                "frequency": new_freq,
                "definition": new_def,
                "manual_bigrams": m_bigrams,
                "manual_trigrams": m_trigrams,
                "manual_collocates": m_collocs,
                "manual_examples": m_examples,
                "manual_collo_ex": m_collo_ex,
                "is_manual": True
            }
            # Auto-save to personal file
            p_path = st.session_state.get('personal_file_path')
            if p_path:
                save_overrides(p_path, st.session_state['overrides'])
                st.success(f"Saved and synced to {p_path}!")
            else:
                st.success("Saved to session (Set personal file path in sidebar to persist)!")
            st.rerun()

def render(where_clause="1=1", params=(), stop_words=None, collocate_filter=None, skip_punct=True, no_corpora=False):
    if stop_words is None: stop_words = []
    if collocate_filter is None: collocate_filter = []
    
    if 'overrides' not in st.session_state:
        st.session_state['overrides'] = {}

    # Initialize search box in session state
    if 'search_box' not in st.session_state:
        st.session_state.search_box = ""

    if no_corpora:
        st.info("💡 **Getting Started**: Select one or more corpora from the sidebar to begin searching and indexing.")
        st.caption("You can also upload your own files or choose from the 'Available on Disk' collection.")

    # Search input - the widget automatically syncs with st.session_state.search_box
    st.text_input(
        "Search word:", 
        placeholder="Enter a word to see its dictionary entry...",
        key="search_box"
    )
    
    # Custom CSS for Professional Look
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@300;700;900&family=Open+Sans:wght@400;600&display=swap');
    
    /* Global Tightening */
    .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
    div[data-testid="stDivider"] { margin-top: 0.5rem; margin-bottom: 0.5rem; }
    
    /* Typography */
    .headword {
        font-family: 'Merriweather', serif;
        font-size: 2.2rem;
        font-weight: 900;
        color: #1d2a57; /* Navy Blue */
        margin-right: 0.5rem;
        line-height: 1.2;
        text-shadow: 2px 0 #fff, -2px 0 #fff, 0 2px #fff, 0 -2px #fff, 1px 1px #fff, -1px -1px #fff, 1px -1px #fff, -1px 1px #fff;
    }
    .phonetic {
        font-family: 'Open Sans', sans-serif;
        font-size: 1.1rem;
        color: #555;
        margin-right: 0.5rem;
        text-shadow: 1px 0 #fff, -1px 0 #fff, 0 1px #fff, 0 -1px #fff;
    }
    .pos-tag {
        font-family: 'Open Sans', sans-serif;
        font-weight: 700;
        font-size: 0.9rem;
        color: #c00; /* Deep Red */
        text-transform: uppercase;
        background: #fff0f0;
        padding: 2px 6px;
        border-radius: 4px;
        vertical-align: middle;
    }
    
    /* Definition Block */
    .sense-block {
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .definition {
        font-family: 'Open Sans', sans-serif;
        font-size: 1.1rem;
        color: #222;
        line-height: 1.4;
        margin-bottom: 0.5rem;
    }
    
    /* Examples Styling */
    .example-box {
        border-left: 3px solid #1d2a57;
        background-color: #f4f6f9;
        padding: 4px 8px;
        margin-top: 4px;
        font-family: 'Merriweather', serif;
        font-style: italic;
        color: #333;
        font-size: 0.95rem;
    }
    
    /* Section Headers */
    h3 {
        font-family: 'Open Sans', sans-serif !important;
        font-size: 1.1rem !important;
        color: #1d2a57 !important;
        margin-bottom: 4px !important;
        padding-top: 8px !important;
        text-shadow: 1px 0 #fff, -1px 0 #fff, 0 1px #fff, 0 -1px #fff;
    }
    
    </style>
    """, unsafe_allow_html=True)

    # Use the widget's current value as the query
    query = st.session_state.search_box.strip()
    
    if query:
        # Autocomplete (Respecting filters) - Show suggestions for quick picking
        suggestions = search.autocomplete(query, where_clause, params)
        if suggestions and query not in suggestions:
             st.caption("Did you mean:")
             cols = st.columns(len(suggestions) if len(suggestions) < 5 else 5)
             for i, sugg in enumerate(suggestions[:5]):
                 cols[i].button(sugg, key=f"sugg_{sugg}", on_click=cb_update_query, args=(sugg,))

        # 1. Exact Search (Filtered by your sidebar)
        df = search.search_exact(query, where_clause, params)
        
        # 2. Check for manual overrides even if not in current corpus
        query_overrides = st.session_state['overrides'].get(query, {})
        
        if df.empty and not query_overrides:
            # Check if it exists GLOBALLY to give helpful feedback
            global_count = frequency.get_metrics(query, "1=1", [])['frequency']
            if global_count > 0:
                st.warning(f"⚠️ **{query}** exists in the database ({global_count} times), but it is hidden by your current **Corpus** or **Metadata** filters.")
                st.info("Check your sidebar selections to unhide this data.")
            else:
                st.error(f"❌ **{query}** was not found in the current database.")
            
            # Fuzzy match as fallback for typos
            fuzzy = search.search_fuzzy(query)
            if fuzzy:
                st.write("Similar words in database:")
                for ft in fuzzy:
                    st.button(ft, key=f"fuzzy_{ft}", on_click=cb_update_query, args=(ft,))
            return
            
        # Group by POS (Found in corpus)
        grouped = df.groupby('tag') if not df.empty else None

        # Tags from BOTH corpus and overrides
        corpus_tags = list(grouped.groups.keys()) if grouped is not None else []
        all_display_tags = sorted(list(set(corpus_tags + list(query_overrides.keys()))))
        
        # Sense Tabs + Add Sense
        sense_labels = [f"Sense: {tag}" for tag in all_display_tags]
        sense_labels.append("➕ Add Sense")
        
        tabs = st.tabs(sense_labels)
        
        # Pre-fetch common data
        lemma = search.get_lemma(query)
        same_lemma_words = search.get_forms_by_lemma(lemma)
        all_pos_tags = sorted(list(set(search.get_pos_tags(query) + list(query_overrides.keys()))))
        
        # Global metrics for this token (from corpus)
        metrics_corpus = frequency.get_metrics(query, where_clause, params)

        # Render senses
        for i, tag in enumerate(all_display_tags):
            with tabs[i]:
                # Data from overrides
                override = query_overrides.get(tag, {})
                is_override = bool(override)
                
                # 1. Definition
                def_key = f"def_{query}_{tag}"
                # Precedence: Override > SessionState > Corpus (none here)
                curr_def = override.get('definition') or st.session_state.get(def_key, "")
                
                # Header - Professional Style
                # Precedence: Override > default IPA
                try:
                    default_pron = ipa.convert(query)
                except:
                    default_pron = query
                pron = override.get('pronunciation') or default_pron
                
                # Check metrics
                freq = override.get('frequency') if 'frequency' in override else metrics_corpus['frequency']
                is_manual_freq = 'frequency' in override
                
                # HTML Header Block
                st.markdown(f"""
                <div class="entry-header">
                    <span class="headword">{query}</span>
                    <span class="phonetic">/{pron}/</span>
                    <span class="pos-tag">{tag}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Metadata Row (Frequency, CEFR, etc.) - Compact
                m1, m2, m3 = st.columns([2, 2, 4])
                with m1:
                    st.caption(f"Freq: **{freq}** {'(Manual)' if is_manual_freq else ''}")
                with m2:
                    wl_badges = manager.check_token(query)
                    if wl_badges:
                        badges_html = " ".join([f"<span style='background:#e0f2f1; color:#00695c; padding:2px 6px; border-radius:4px; font-size:12px;'>{b['name']} {b['value']}</span>" for b in wl_badges])
                        st.markdown(badges_html, unsafe_allow_html=True)
                with m3:
                     # Zipf and PMW simplified
                     pass 

                # Definition Block
                st.markdown(f"""
                <div class="sense-block">
                    <div class="definition">{curr_def if curr_def else "<span style='color:#999; font-style:italic;'>No definition provided.</span>"}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Navigation Rows - Stacked (Full Width)
                render_clickable_word_row("Words from same Lemma", same_lemma_words, key_prefix="lemma", context=tag)
                related = search.get_related_words(query, limit=10) # Limit 10
                render_clickable_word_row("Related Words", related, key_prefix="related", context=tag)

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True) # Spacer
                
                # Form to Edit (Collapsed by default and compacted)
                render_sense_editor(query, tag, {
                    "definition": curr_def,
                    "pronunciation": pron,
                    "frequency": freq,
                    "manual_bigrams": override.get('manual_bigrams', ''),
                    "manual_trigrams": override.get('manual_trigrams', ''),
                    "manual_collocates": override.get('manual_collocates', ''),
                    "manual_examples": override.get('manual_examples', ''),
                    "manual_collo_ex": override.get('manual_collo_ex', '')
                })
                
                # External Links - minimalist
                st.markdown(f"<div style='font-size:12px; margin-top:5px;'><a href='https://www.collinsdictionary.com/dictionary/english/{query}' target='_blank'>Collins Dictionary</a> • <a href='https://www.collinsdictionary.com/dictionary/english-thesaurus/{query}' target='_blank'>Thesaurus</a></div>", unsafe_allow_html=True)
                
                st.divider()
                
                # N-Grams Side-by-Side
                st.subheader("N-Grams")
                
                # Bigram/Trigram Manual Overrides
                bi_over = parse_manual_list(override.get('manual_bigrams', ''))
                tri_over = parse_manual_list(override.get('manual_trigrams', ''))
                
                if bi_over or tri_over:
                    ngrams = {
                        'bi_search_word': [(r[0], r[1]) for r in bi_over if len(r) >= 2],
                        'bi_word_search': [], 
                        'tri_s_w_w': [(r[0], r[1]) for r in tri_over if len(r) >= 2],
                        'tri_w_s_w': [],
                        'tri_w_w_s': []
                    }
                else:
                    ngrams = collocation.get_ngrams(query, where_clause=where_clause, params=params, stop_words=stop_words, skip_punct=skip_punct)

                c_bi, c_tri = st.columns([4, 6]) # 40% / 60% Split
                
                with c_bi:
                    st.caption("**Bigrams**")
                    b1, b2 = st.columns(2)
                    with b1:
                        st.caption(f"{query} + Word")
                        if ngrams['bi_search_word']:
                            st.table(pd.DataFrame(ngrams['bi_search_word'], columns=['Bigram', 'Freq']).head(5))
                        else:
                            st.caption("-")
                    with b2:
                        st.caption(f"Word + {query}")
                        if ngrams['bi_word_search']:
                            st.table(pd.DataFrame(ngrams['bi_word_search'], columns=['Bigram', 'Freq']).head(5))
                        else:
                            st.caption("-")
                    
                    # Download Bigrams
                    all_bi = []
                    if ngrams['bi_search_word']: all_bi.extend([{'Type': f"{query}+Word", 'Bigram': x[0], 'Freq': x[1]} for x in ngrams['bi_search_word']])
                    if ngrams['bi_word_search']: all_bi.extend([{'Type': f"Word+{query}", 'Bigram': x[0], 'Freq': x[1]} for x in ngrams['bi_word_search']])
                    if all_bi:
                        st.download_button("📥 CSV", pd.DataFrame(all_bi).to_csv(index=False).encode('utf-8'), f"bigrams_{query}.csv", "text/csv", key=f"dl_bi_{query}_{tag}")


                with c_tri:
                    st.caption("**Trigrams**")
                    # Side-by-side sub-columns for Trigrams
                    t1, t2, t3 = st.columns(3)
                    with t1:
                        st.caption(f"{query}+W+W")
                        if ngrams['tri_s_w_w']:
                             st.table(pd.DataFrame(ngrams['tri_s_w_w'], columns=['Trigram', 'Freq']).head(5))
                        else:
                             st.caption("-")
                    with t2:
                        st.caption(f"W+{query}+W")
                        if ngrams['tri_w_s_w']:
                             st.table(pd.DataFrame(ngrams['tri_w_s_w'], columns=['Trigram', 'Freq']).head(5))
                        else:
                             st.caption("-")
                    with t3:
                        st.caption(f"W+W+{query}")
                        if ngrams['tri_w_w_s']:
                             st.table(pd.DataFrame(ngrams['tri_w_w_s'], columns=['Trigram', 'Freq']).head(5))
                        else:
                             st.caption("-")
                    
                    # Download Trigrams
                    all_tri = []
                    if ngrams['tri_s_w_w']: all_tri.extend([{'Type': f"{query}+W+W", 'Trigram': x[0], 'Freq': x[1]} for x in ngrams['tri_s_w_w']])
                    if ngrams['tri_w_s_w']: all_tri.extend([{'Type': f"W+{query}+W", 'Trigram': x[0], 'Freq': x[1]} for x in ngrams['tri_w_s_w']])
                    if ngrams['tri_w_w_s']: all_tri.extend([{'Type': f"W+W+{query}", 'Trigram': x[0], 'Freq': x[1]} for x in ngrams['tri_w_w_s']])
                    if all_tri:
                        st.download_button("📥 CSV", pd.DataFrame(all_tri).to_csv(index=False).encode('utf-8'), f"trigrams_{query}.csv", "text/csv", key=f"dl_tri_{query}_{tag}")

                
                # Collocates
                st.subheader("Top-26 Collocates")
                coll_over = parse_manual_list(override.get('manual_collocates', ''))
                if coll_over:
                    collocs = [{'collocate': r[0], 'LL': r[1] if len(r)>1 else '0'} for r in coll_over]
                else:
                    collocs = collocation.get_collocates(query, limit=26, where_clause=where_clause, params=params, stop_words=stop_words, allowed_words=collocate_filter, skip_punct=skip_punct)
                
                if collocs:
                    # 13-Column Grid (2 items each) -> 13x2 = 26
                    # Filling Column-by-Column (chunks of 2)
                    chunks = [collocs[i:i + 2] for i in range(0, len(collocs), 2)]
                    
                    cols_grid = st.columns(13)
                    
                    for i, chunk in enumerate(chunks):
                        if i < 13:
                            with cols_grid[i]:
                                for c in chunk:
                                    st.button(c['collocate'], key=f"coll_{c['collocate']}_{tag}", on_click=cb_update_query, args=(c['collocate'],))

                    # Download Button
                    st.divider()
                    df_collocs = pd.DataFrame(collocs)
                    csv_collocs = df_collocs.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Collocates Table",
                        data=csv_collocs,
                        file_name=f"collocates_{query}_{tag}.csv",
                        mime="text/csv",
                        key=f"dl_collocs_{query}_{tag}"
                    )
                else:
                    st.caption("No collocates found.")
                
                st.divider()
                
                # KWIC Examples (Reverted to Old Style)
                st.subheader("Examples")
                ex_over = parse_manual_list(override.get('manual_examples', ''))
                
                if ex_over:
                    kwic_lines = [{'left': r[0], 'node': r[1], 'right': r[2]} for r in ex_over if len(r) >= 3]
                else:
                    kwic_lines = kwic.get_kwic_lines(query, where_clause=where_clause, params=params, limit=10) # Restored limit or keep small? User said "old version", likely refers to style.
                
                # Download KWIC
                if kwic_lines:
                     df_kwic = pd.DataFrame(kwic_lines)
                     csv_kwic = df_kwic.to_csv(index=False).encode('utf-8')
                     st.download_button(
                        label="📥 Download Examples",
                        data=csv_kwic,
                        file_name=f"examples_{query}_{tag}.csv",
                        mime="text/csv",
                        key=f"dl_kwic_{query}_{tag}"
                     )
                
                for line in kwic_lines:
                     # Old Flexbox Style
                     st.markdown(f"""
                    <div style="display: flex; justify-content: center; font-family: monospace; font-size: 0.95rem; margin-bottom: 4px;">
                        <span style="text-align: right; width: 45%; margin-right: 10px;">{line['left']}</span>
                        <span style="font-weight: bold; color: #c00;">{line['node']}</span>
                        <span style="text-align: left; width: 45%; margin-left: 10px;">{line['right']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                if st.button("Choose", key=f"btn_choose_kwic_{query}_{tag}", help="Select specific lines"):
                    open_selection_dialog(query, tag, "general", where_clause=where_clause, params=params)

                # Collocations & Examples
                st.subheader("Examples by Collocates")
                # Download Button for Collocate Examples (Need to fetch them all? Or just user manual ones? 
                # "also present download table button to download examples and examples by collocates"
                # For "Examples by collocates", there are many. I should probably just download the MANUAL ones if manual, or maybe fetch a batch?
                # I'll stick to downloading the visible Manual ones for now, or maybe generated ones if not manual?
                # Generating ALL collocate examples is heavy. I will only provide download for CURRENTLY VISIBLE or Manual overrides.
                
                collo_ex_over = parse_manual_list(override.get('manual_collo_ex', ''))
                
                if collo_ex_over:
                     # Prepare Download
                     df_collo_ex = pd.DataFrame(collo_ex_over, columns=['Collocate', 'Left', 'Node', 'Right'])
                     csv_collo_ex = df_collo_ex.to_csv(index=False).encode('utf-8')
                     st.download_button("📥 Download Collocate Examples", csv_collo_ex, f"collo_examples_{query}.csv", "text/csv", key=f"dl_ce_{query}_{tag}")

                if collo_ex_over:
                    # Manual collocates
                    manual_collo_data = {}
                    for r in collo_ex_over:
                         if len(r) >= 4:
                            col_word = r[0]
                            if col_word not in manual_collo_data: manual_collo_data[col_word] = []
                            manual_collo_data[col_word].append({'left': r[1], 'node': r[2], 'right': r[3], 'col_token': col_word})
                    
                    for col_word, examples in manual_collo_data.items():
                        with st.expander(f"**{col_word}**", expanded=False):
                            for ex in examples:
                                components.render_collocate_example(ex['left'], ex['node'], ex['right'], ex['col_token'])
                            if st.button("Edit", key=f"edit_coll_sel_{query}_{tag}_{col_word}"):
                                 open_selection_dialog(query, tag, "collocate", collocate_word=col_word, where_clause=where_clause, params=params)
                else:
                    # Top Collocates 
                    top_collocs = [c['collocate'] for c in collocs[:3]] # Limit 3 for display
                    if top_collocs:
                         for col_word in top_collocs:
                            with st.expander(f"Usage with '{col_word}'", expanded=False):
                                col_examples = kwic.get_collocate_kwic(query, col_word, where_clause=where_clause, params=params, limit=3)
                                if col_examples:
                                    for ex in col_examples:
                                         components.render_collocate_example(ex['left'], ex['node'], ex['right'], ex['col_token'])
                                
                                if st.button("Choose", key=f"btn_choose_coll_{query}_{tag}_{col_word}"):
                                    open_selection_dialog(query, tag, "collocate", collocate_word=col_word, where_clause=where_clause, params=params)
                    else:
                         st.caption("No strong word partners found.")
                
                # Save Button (Direct to personal file)
                st.divider()
                p_path = st.session_state.get('personal_file_path')
                if st.button("💾 Save Entry to Personal File", key=f"save_personal_{query}_{tag}"):
                    if p_path:
                        # Ensure we have the latest entry in session state
                        if query not in st.session_state['overrides']:
                            st.session_state['overrides'][query] = {}
                        
                        # Only update if not already manual or user confirms? 
                        # For now, just save current view state as override
                        st.session_state['overrides'][query][tag] = {
                            "definition": curr_def,
                            "pronunciation": pron,
                            "frequency": freq,
                            "manual_bigrams": override.get('manual_bigrams', ''),
                            "manual_trigrams": override.get('manual_trigrams', ''),
                            "manual_collocates": override.get('manual_collocates', ''),
                            "manual_examples": override.get('manual_examples', ''),
                            "manual_collo_ex": override.get('manual_collo_ex', ''),
                            "is_manual": True
                        }
                        if save_overrides(p_path, st.session_state['overrides']):
                            st.success(f"Entry for '{query}' saved to {p_path}!")
                        else:
                            st.error("Failed to save to personal file.")
                    else:
                        st.warning("⚠️ Please set a 'Personal Overrides File Path' in the sidebar first.")

        # "Add Sense" Tab content
        with tabs[-1]:
            st.header("Add New Sense")
            st.info("Manually define all fields for a new sense.")
            
            with st.form("new_sense_form"):
                new_tag = st.text_input("POS Tag (e.g., NN, VB)")
                new_pron = st.text_input("Pronunciation")
                new_freq = st.number_input("Initial Frequency", value=0)
                new_def_manual = st.text_area("Definition")
                
                st.write("---")
                st.caption("Manual Statistics & Examples (Format: 'Item | Value')")
                m_bi = st.text_area("Bigrams", placeholder="node word | 10")
                m_tri = st.text_area("Trigrams", placeholder="node w1 w2 | 3")
                m_coll = st.text_area("Collocates", placeholder="word | score")
                m_ex = st.text_area("Examples (KWIC)", placeholder="left | node | right")
                m_col_ex = st.text_area("Collocate Examples", placeholder="collocate | left | node | right")
                
                submitted = st.form_submit_button("➕ Add Sense to Dictionary")
                if submitted:
                    if not new_tag:
                        st.error("POS Tag is required.")
                    else:
                        if query not in st.session_state['overrides']:
                            st.session_state['overrides'][query] = {}
                        st.session_state['overrides'][query][new_tag] = {
                            "pronunciation": new_pron,
                            "frequency": new_freq,
                            "definition": new_def_manual,
                            "manual_bigrams": m_bi,
                            "manual_trigrams": m_tri,
                            "manual_collocates": m_coll,
                            "manual_examples": m_ex,
                            "manual_collo_ex": m_col_ex,
                            "is_manual": True
                        }
                        # Auto-save
                        p_path = st.session_state.get('personal_file_path')
                        if p_path:
                            save_overrides(p_path, st.session_state['overrides'])
                            st.success(f"New sense added and synced to {p_path}!")
                        else:
                            st.success(f"New sense for {query} ({new_tag}) added!")
                        st.rerun()

@st.cache_data(show_spinner=False)
def get_cached_candidates(token, type, collocate_word, where_clause, params):
    """Cached wrapper to ensure stable dataframe generation for data_editor."""
    if type == "general":
        return kwic.get_kwic_lines(token, where_clause=where_clause, params=params, limit=50)
    else:
        # Collocate
        return kwic.get_collocate_kwic(token, collocate_word, where_clause=where_clause, params=params, limit=50)

@st.dialog("Choose Concordance Lines", width="large")
def open_selection_dialog(token, tag, type, collocate_word=None, where_clause="1=1", params=()):
    st.write(f"Select examples for **{token}** ({tag}).")
    limit_cnt = 10 if type == "general" else 3
    st.caption(f"You can select up to **{limit_cnt}** lines.")
    
    # 1. Fetch Candidates (Pool of 50) - Cached
    candidates = get_cached_candidates(token, type, collocate_word, where_clause, params)
    
    if not candidates:
        st.warning("No concordance lines found to select from.")
        return

    # 2. Prepare Data for Editor
    # We need a boolean column for selection
    df = pd.DataFrame(candidates)
    
    # Ensuring columns exist (handle empty case safely)
    if df.empty:
         st.warning("No concordance lines found to select from.")
         return

    # st.data_editor needs a stable key and input. By caching 'candidates', the input DF is stable.
    # We also need to PRESERVE selection state if possible, but st.data_editor handles that with 'key' 
    # as long as the underlying data structure hasn't "re-shuffled".
    
    if 'selected' not in df.columns:
        df.insert(0, "selected", False)
    
    # Show user-friendly columns
    display_cols = ['selected', 'left', 'node', 'right']
    
    edited_df = st.data_editor(
        df[display_cols], 
        hide_index=True, 
        column_config={"selected": st.column_config.CheckboxColumn(required=True)},
        disabled=["left", "node", "right"], # Read-only text
        key=f"editor_{token}_{tag}_{type}_{collocate_word}"
    )
    
    # 3. Validation & Save
    selected_rows = edited_df[edited_df.selected]
    count = len(selected_rows)
    
    st.write(f"Selected: {count} / {limit_cnt}")
    
    if st.button("Confirm Selection"):
        if count > limit_cnt:
            st.error(f"Please select at most {limit_cnt} lines (you selected {count}).")
        else:
            # Format for storage
            # GENERAL: "left | node | right"
            # COLLOCATE: "col_token | left | node | right"
            
            lines_str = []
            for _, row in selected_rows.iterrows():
                if type == "general":
                    lines_str.append(f"{row['left']} | {row['node']} | {row['right']}")
                else:
                    # For collocate examples, we need to preserve existing other-collocate examples?
                    # The override structure for manual_collo_ex is a single big string/list.
                    # This dialog is specific to ONE collocate.
                    # So we need to merge this selection with existing ones for other collocates.
                    lines_str.append(f"{collocate_word} | {row['left']} | {row['node']} | {row['right']}")
            
            # Update Session State / Overrides
            if token not in st.session_state['overrides']:
                st.session_state['overrides'][token] = {}
            if tag not in st.session_state['overrides'][token]:
                st.session_state['overrides'][token][tag] = {} # partial init
            
            target_key = 'manual_examples' if type == 'general' else 'manual_collo_ex'
            
            # Logic to merge logic for collocates
            if type == 'collocate':
                curr_str = st.session_state['overrides'][token][tag].get(target_key, '')
                curr_list = parse_manual_list(curr_str)
                # Filter out lines for THIS collocate from existing list
                # format: [col, left, node, right]
                kept_list = [r for r in curr_list if len(r) > 0 and r[0] != collocate_word]
                
                # Append new ones
                # We need to construct the list lines manually for new ones
                for _, row in selected_rows.iterrows():
                    kept_list.append([collocate_word, row['left'], row['node'], row['right']])
                
                # Re-serialize
                final_str = "\n".join([" | ".join(r) for r in kept_list])
            else:
                # General: Just replace
                final_str = "\n".join(lines_str)
                
            st.session_state['overrides'][token][tag][target_key] = final_str
            st.session_state['overrides'][token][tag]['is_manual'] = True
            
            # Auto-save
            p_path = st.session_state.get('personal_file_path')
            if p_path:
                save_overrides(p_path, st.session_state['overrides'])
                st.success("Saved!")
            else:
                st.success("Saved to session!")
            
            st.rerun()
