
import streamlit as st
import pandas as pd
import eng_to_ipa as ipa
from utils import indo_g2p
import json
from pipeline import search, cache_manager as cache
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

def cb_search_token(token):
    """Callback to search for a token and switch to Search tab."""
    st.session_state.search_box = token
    st.session_state.main_nav = "Search"


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


    
    # Custom CSS for Professional Look
    st.markdown("""
    <style>
    /* ... CSS kept ... */
    </style>
    """, unsafe_allow_html=True)

    # Navigation Tabs
    # We use a radio button styled as tabs or just simple toggle
    nav = st.radio("Navigation", ["Search", "Corpus Statistic"], horizontal=True, label_visibility="collapsed", key="main_nav")
    
    if nav == "Corpus Statistic":
        render_entry_tab(where_clause, params)
    else:
        render_search_tab(where_clause, params, stop_words, collocate_filter, skip_punct)

def render_entry_tab(where_clause, params):
    st.title("Corpus Statistic")
    
    # 1. Stats
    stats = search.get_corpus_stats(where_clause, params)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Tokens", f"{stats['total_tokens']:,}")
    c2.metric("Total Lemmas", f"{stats['total_lemmas']:,}")
    c3.metric("Unique POS Tags", len(stats['pos_tags']))
    
    
    # Display POS Tags as Badges
    st.caption("**POS Tags:**")
    if stats['pos_tags']:
        badges_html = "<div style='margin-top: 8px; margin-bottom: 12px;'>" + " ".join([
            f"<span style='background:#e3f2fd; color:#1976d2; padding:4px 8px; border-radius:4px; font-size:13px; margin-right:6px; display:inline-block; margin-bottom:4px;'>{tag}</span>" 
            for tag in sorted(stats['pos_tags'])
        ]) + "</div>"
        st.markdown(badges_html, unsafe_allow_html=True)
    else:
        st.write("No POS tags found.")
    
        
    st.divider()
    
    # Header with download button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Frequency List")
    
    # 2. Data
    df = search.get_full_frequency_list(where_clause, params)
    
    if df.empty:
        st.info("No tokens found in current selection.")
        return
        
    # Add Definition Column (from overrides)
    def get_def(token):
        # Optimistic check
        ov = st.session_state['overrides'].get(token, {})
        if not ov:
             ov = st.session_state['overrides'].get(token.lower(), {})
        return ov.get('definition', '')

    df['Definition'] = df['token'].apply(get_def)
    
    # Sort: Definition (Desc -> items with def first), then Freq (Desc)
    df = df.sort_values(by=['Definition', 'freq'], ascending=[False, False])
    
    # Excel download button
    from io import BytesIO
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Frequency List', index=False)
    buffer.seek(0)
    
    with col2:
        st.download_button(
            label="📥 Excel",
            data=buffer,
            file_name="frequency_list.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # 3. Interactive Table with clickable tokens
    # Display with pagination
    items_per_page = 50
    total_items = len(df)
    total_pages = (total_items - 1) // items_per_page + 1
    
    if 'freq_list_page' not in st.session_state:
        st.session_state.freq_list_page = 0
    
    page = st.session_state.freq_list_page
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    
    df_page = df.iloc[start_idx:end_idx].reset_index(drop=True)
    
    # Display table with clickable tokens
    for idx, row in df_page.iterrows():
        col1, col2, col3 = st.columns([2, 1, 4])
        with col1:
            st.button(row['token'], key=f"tok_{start_idx + idx}", use_container_width=True, 
                     on_click=cb_search_token, args=(row['token'],))
        with col2:
            st.write(f"**{row['freq']}**")
        with col3:
            st.write(row['Definition'][:100] + "..." if len(row['Definition']) > 100 else row['Definition'])
    
    # Pagination controls
    if total_pages > 1:
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("← Previous", disabled=(page == 0)):
                st.session_state.freq_list_page = max(0, page - 1)
                st.rerun()
        with col_info:
            st.write(f"Page {page + 1} of {total_pages} ({start_idx + 1}-{end_idx} of {total_items})")
        with col_next:
            if st.button("Next →", disabled=(page >= total_pages - 1)):
                st.session_state.freq_list_page = min(total_pages - 1, page + 1)
                st.rerun()

def render_search_tab(where_clause, params, stop_words, collocate_filter, skip_punct):
    # Search input - the widget automatically syncs with st.session_state.search_box
    st.text_input(
        "Search word:", 
        placeholder="Enter a word to see its dictionary entry...",
        key="search_box"
    )

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
        
        # Calculate Corpus Hash (for Caching)
        # We use the total token count of the current filtered corpus as a proxy for versioning.
        corpus_hash = frequency.get_total_tokens(where_clause, params)
        
        # Sense Tabs + Add Sense
        sense_labels = [f"Sense: {tag}" for tag in all_display_tags]
        sense_labels.append("➕ Add Sense")
        
        tabs = st.tabs(sense_labels)
        
        # Pre-fetch common data
        lemma = search.get_lemma(query)
        same_lemma_words = search.get_forms_by_lemma(lemma)
        
        # Global metrics (Removed - calculated per sense now)
        # metrics_corpus = frequency.get_metrics(query, where_clause, params)

        # Render senses
        for i, tag in enumerate(all_display_tags):
            with tabs[i]:
                # Data from overrides
                override = query_overrides.get(tag, {})
                
                # 1. Definition
                def_key = f"def_{query}_{tag}"
                curr_def = override.get('definition') or st.session_state.get(def_key, "")
                
                # Header - Professional Style
                # Get language setting
                language = st.session_state.get('corpus_language', 'English')
                
                # Generate pronunciation based on language
                if language == 'English':
                    try:
                        default_pron = ipa.convert(query)
                    except:
                        default_pron = query
                elif language == 'Indonesian':
                    try:
                        default_pron = indo_g2p.convert(query)
                    except:
                        default_pron = query
                else:
                    # Other languages - no transcription
                    default_pron = ""
                
                pron = override.get('pronunciation') or default_pron
                
                # Check metrics (Per Sense)
                # Check metrics (Per Sense)
                metrics_corpus = cache.get_metrics(corpus_hash, query, where_clause, params, pos_tag=tag)
                
                freq = override.get('frequency') if 'frequency' in override else metrics_corpus['frequency']
                is_manual_freq = 'frequency' in override
                
                # Calculate dynamic metrics (PMW, Zipf)
                total_toks = metrics_corpus.get('total_subset', 1) or 1
                if is_manual_freq:
                    pmw_val = (freq / total_toks) * 1000000
                    if pmw_val > 1000: zipf_val = 5
                    elif pmw_val > 100: zipf_val = 4
                    elif pmw_val > 10: zipf_val = 3
                    elif pmw_val > 1: zipf_val = 2
                    else: zipf_val = 1
                else:
                    pmw_val = metrics_corpus.get('pmw', 0)
                    zipf_val = metrics_corpus.get('zipf', 1)

                # Consolidated Header - All on one line
                st.header(f"{query}")
                
                # Build pronunciation links based on language
                pron_links_html = ""
                if language == 'English' and pron:
                    us_link = f"https://youglish.com/pronounce/{query}/english/us"
                    uk_link = f"https://youglish.com/pronounce/{query}/english/uk"
                    pron_links_parts = [
                        f"<a href=\"{us_link}\" target=\"_blank\" title=\"US Pronunciation\" style=\"text-decoration: none; font-size: 20px;\">🎤 US</a>",
                        f"<a href=\"{uk_link}\" target=\"_blank\" title=\"UK Pronunciation\" style=\"text-decoration: none; font-size: 20px;\">🎤 UK</a>"
                    ]
                    pron_links_html = " ".join(pron_links_parts)
                elif language == 'Indonesian' and pron:
                    # Indonesian pronunciation (could add Indonesian audio links if desired)
                    pron_links_html = "<span style=\"font-size: 18px; color: #666;\">🇮🇩</span>"
                
                # Build wordlist badges (only for English)
                wl_badges = []
                if language == 'English':
                    wl_badges = manager.check_token(query, lemma=lemma)
                
                # Get PMW range for relative percentage calculation
                pmw_range = cache.get_pmw_range(corpus_hash, where_clause, params)
                min_pmw = pmw_range['min_pmw']
                max_pmw = pmw_range['max_pmw']
                
                # Calculate percentage position in PMW range
                if max_pmw > min_pmw:
                    pmw_pct = ((pmw_val - min_pmw) / (max_pmw - min_pmw)) * 100
                    pmw_pct = min(100, max(1, pmw_pct))  # Clamp between 1% and 100%
                else:
                    pmw_pct = 100
                
                # PMW Visual Band (Single line construction to avoid Markdown issues)
                pmw_band_parts = [
                    f"<div style=\"display:inline-flex; flex-direction:column; align-items:flex-start; margin-right:12px; background:#f5f5f5; padding:6px 10px; border-radius:4px;\">",
                    f"<span style=\"font-size:12px; color:#666; margin-bottom:2px;\">PMW</span>",
                    f"<div style=\"display:flex; align-items:center; gap:6px;\">",
                    f"<span style=\"font-weight:bold; font-size:18px; min-width:60px;\">{pmw_val:.2f}</span>",
                    f"<div style=\"background-color:#e0e0e0; width:120px; height:12px; border-radius:6px; overflow:hidden;\">",
                    f"<div style=\"background-color:#2196F3; width:{pmw_pct:.1f}%; height:100%;\"></div>",
                    f"</div>",
                    f"<span style=\"font-size:11px; color:#888;\">{pmw_pct:.0f}%</span>",
                    f"</div>",
                    f"</div>"
                ]
                pmw_band_html = "".join(pmw_band_parts)
                
                # Zipf Visual Band (5 bars)
                zipf_bars = []
                for i in range(1, 6):
                    color = "#1d2a57" if i <= zipf_val else "#e0e0e0"
                    zipf_bars.append(f"<div style=\"width:10px; height:20px; background-color:{color}; border-radius:2px;\"></div>")
                
                # Tooltip text for Zipf band
                zipf_tooltip = "Zipf Scale (Frequency per Million Words):&#10;Band 1: < 1 (Very Low)&#10;Band 2: 1 - 10 (Low)&#10;Band 3: 10 - 100 (Medium)&#10;Band 4: 100 - 1,000 (High)&#10;Band 5: > 1,000 (Very High)"
                
                zipf_band_parts = [
                    f"<div title=\"{zipf_tooltip}\" style=\"display:inline-flex; flex-direction:column; align-items:center; background:#f5f5f5; padding:6px 10px; border-radius:4px; cursor:help;\">",
                    f"<span style=\"font-size:12px; color:#666; margin-bottom:4px;\">Zipf {zipf_val}</span>",
                    f"<div style=\"display:flex; gap:3px;\">",
                    " ".join(zipf_bars),
                    f"</div>",
                    f"</div>"
                ]
                zipf_band_html = "".join(zipf_band_parts)
                
                # Pronunciation display (conditional)
                pron_display = ""
                if pron:
                    pron_display = f"<span style=\"font-size: 24px; font-weight: bold;\">/{pron}/</span>"
                
                # Build badges HTML string
                badges_list = []
                # POS tag badge
                badges_list.append(f"<span style=\"background:#1976d2; color:#ffffff; padding:4px 10px; border-radius:4px; font-size:24px; margin-right:6px; font-weight:bold;\">{tag}</span>")
                # Wordlist badges (only for English)
                if wl_badges:
                    for b in wl_badges:
                        badges_list.append(f"<span style=\"background:#e0f2f1; color:#00695c; padding:4px 10px; border-radius:4px; font-size:24px; margin-right:6px;\">{b['name']} {b['value']}</span>")
                
                badges_html = " ".join(badges_list)
                
                # Build complete HTML for metadata row
                html_parts = [pron_display, pron_links_html]
                html_parts.append(f"<span style=\"font-size: 24px;\">Freq: <strong>{freq}</strong> {'(Manual)' if is_manual_freq else ''}</span>")
                html_parts.append(badges_html)
                html_parts.append(pmw_band_html)
                html_parts.append(zipf_band_html)
                
                # Filter out empty strings
                html_parts = [p for p in html_parts if p]
                
                # Combine all parts
                combined_html = " ".join(html_parts)
                
                # Render all metadata
                st.markdown(f'<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;">{combined_html}</div>', unsafe_allow_html=True)
                # Definition Block
                st.markdown(f"""
                <div class="sense-block">
                    <div class="definition">{curr_def if curr_def else "<span style='color:#999; font-style:italic;'>No definition provided.</span>"}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Dictionary and Thesaurus Links (language-specific)
                if language == 'English':
                    st.markdown(f"<div style=\"font-size:12px; margin-top:5px;\"><a href=\"https://www.collinsdictionary.com/dictionary/english/{query}\" target=\"_blank\">Collins Dictionary</a> • <a href=\"https://www.collinsdictionary.com/dictionary/english-thesaurus/{query}\" target=\"_blank\">Thesaurus</a></div>", unsafe_allow_html=True)
                elif language == 'Indonesian':
                    # Single line construction for Indonesian links
                    indo_links = [
                        f"<a href=\"https://kbbi.kemendikdasmen.go.id/entri/{query}\" target=\"_blank\">KBBI (Kemendikbud)</a>",
                        f"<a href=\"https://kbbi.web.id/{query}\" target=\"_blank\">KBBI (Web)</a>",
                        f"<a href=\"https://tesaurus.kemendikdasmen.go.id/tematis/lema/{query}\" target=\"_blank\">Tesaurus</a>"
                    ]
                    st.markdown(f"<div style=\"font-size:12px; margin-top:5px;\">{' • '.join(indo_links)}</div>", unsafe_allow_html=True)
                # For 'Other' languages, no dictionary links
                
                # Navigation Rows
                render_clickable_word_row("Words from same Lemma", same_lemma_words, key_prefix="lemma", context=tag)
                related = search.get_related_words(query, limit=10)
                render_clickable_word_row("Related Words", related, key_prefix="related", context=tag)

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                
                # Form to Edit
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
                
                # External Links
                st.markdown(f"<div style='font-size:12px; margin-top:5px;'><a href='https://www.collinsdictionary.com/dictionary/english/{query}' target='_blank'>Collins Dictionary</a> • <a href='https://www.collinsdictionary.com/dictionary/english-thesaurus/{query}' target='_blank'>Thesaurus</a></div>", unsafe_allow_html=True)
                
                st.divider()
                
                # N-Grams
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
                    ngrams = cache.get_ngrams(corpus_hash, query, where_clause=where_clause, params=params, stop_words=stop_words, skip_punct=skip_punct, pos_tag=tag)

                c_bi, c_tri = st.columns([4, 6])
                
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
                st.subheader("Top-20 Collocates")
                coll_over = parse_manual_list(override.get('manual_collocates', ''))
                if coll_over:
                    collocs = [{'collocate': r[0], 'score': float(r[1]) if len(r)>1 and r[1].replace('.', '', 1).isdigit() else 0.0, 'freq': 0} for r in coll_over]
                else:
                    collocs = cache.get_collocates(corpus_hash, query, limit=26, where_clause=where_clause, params=params, stop_words=stop_words, allowed_words=collocate_filter, skip_punct=skip_punct, pos_tag=tag)
                
                if collocs:
                    limit_n = 20
                    collocs_subset = collocs[:limit_n]
                    chunk_size = 5
                    chunks = [collocs_subset[i:i + chunk_size] for i in range(0, len(collocs_subset), chunk_size)]
                    
                    cols_grid = st.columns(4)
                    
                    for col_idx, chunk in enumerate(chunks):
                        if col_idx < 4:
                            with cols_grid[col_idx]:
                                for item in chunk:
                                    col_txt = item['collocate']
                                    score_val = item.get('score', item.get('LL', 0))
                                    freq_val = item.get('freq', 0)
                                    
                                    if st.button(
                                        f"{col_txt} ({score_val:.1f})", 
                                        key=f"coll_{col_txt}_{tag}", 
                                        help=f"Frequency: {freq_val}\nLog-Likelihood: {score_val:.2f}",
                                        use_container_width=True
                                    ):
                                        st.session_state.query = col_txt
                                        st.rerun()
                    
                    st.divider()
                    
                    df_collocs = pd.DataFrame(collocs)
                    csv_collocs = df_collocs.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Full Collocates", csv_collocs, f"collocates_{query}_{tag}.csv", "text/csv", key=f"dl_coll_{query}_{tag}")
                else:
                    st.info("No collocates found.")
                
                st.divider()
                
                # KWIC Examples
                st.subheader("Examples")
                ex_over = parse_manual_list(override.get('manual_examples', ''))
                
                if ex_over:
                    kwic_lines = [{'left': r[0], 'node': r[1], 'right': r[2]} for r in ex_over if len(r) >= 3]
                else:
                    kwic_lines = cache.get_kwic_lines(corpus_hash, query, where_clause=where_clause, params=params, limit=10, pos_tag=tag)
                
                if kwic_lines:
                     df_kwic = pd.DataFrame(kwic_lines)
                     csv_kwic = df_kwic.to_csv(index=False).encode('utf-8')
                     st.download_button("📥 Download Examples", csv_kwic, f"examples_{query}_{tag}.csv", "text/csv", key=f"dl_kwic_{query}_{tag}")
                
                for line in kwic_lines:
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
                
                collo_ex_over = parse_manual_list(override.get('manual_collo_ex', ''))
                
                if collo_ex_over:
                     df_collo_ex = pd.DataFrame(collo_ex_over, columns=['Collocate', 'Left', 'Node', 'Right'])
                     csv_collo_ex = df_collo_ex.to_csv(index=False).encode('utf-8')
                     st.download_button("📥 Download Collocate Examples", csv_collo_ex, f"collo_examples_{query}.csv", "text/csv", key=f"dl_ce_{query}_{tag}")

                if collo_ex_over:
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
                    top_collocs = [c['collocate'] for c in collocs[:3]]
                    if top_collocs:
                         for col_word in top_collocs:
                            with st.expander(f"Usage with '{col_word}'", expanded=False):
                                col_examples = cache.get_collocate_kwic(corpus_hash, query, col_word, where_clause=where_clause, params=params, limit=3, pos_tag=tag)
                                if col_examples:
                                    for ex in col_examples:
                                         components.render_collocate_example(ex['left'], ex['node'], ex['right'], ex['col_token'])
                                
                                if st.button("Choose", key=f"btn_choose_coll_{query}_{tag}_{col_word}"):
                                    open_selection_dialog(query, tag, "collocate", collocate_word=col_word, where_clause=where_clause, params=params)
                    else:
                         st.caption("No strong word partners found.")
                
                st.divider()
                p_path = st.session_state.get('personal_file_path')
                if st.button("💾 Save Entry to Personal File", key=f"save_personal_{query}_{tag}"):
                    if p_path:
                        if query not in st.session_state['overrides']:
                            st.session_state['overrides'][query] = {}
                        
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
def get_cached_candidates(token, tag, type, collocate_word, where_clause, params):
    """Cached wrapper to ensure stable dataframe generation for data_editor."""
    # We recalculate hash here or pass it? Better to recalculate to keep signature simple for this specific component
    corpus_hash = frequency.get_total_tokens(where_clause, params)
    
    if type == "general":
        return cache.get_kwic_lines(corpus_hash, token, where_clause=where_clause, params=params, limit=50, pos_tag=tag)
    else:
        # Collocate
        return cache.get_collocate_kwic(corpus_hash, token, collocate_word, where_clause=where_clause, params=params, limit=50, pos_tag=tag)

@st.dialog("Choose Concordance Lines", width="large")
def open_selection_dialog(token, tag, type, collocate_word=None, where_clause="1=1", params=()):
    st.write(f"Select examples for **{token}** ({tag}).")
    limit_cnt = 10 if type == "general" else 3
    st.caption(f"You can select up to **{limit_cnt}** lines.")
    
    # 1. Fetch Candidates (Pool of 50) - Cached
    candidates = get_cached_candidates(token, tag, type, collocate_word, where_clause, params)
    
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
