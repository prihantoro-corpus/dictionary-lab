
import streamlit as st
import pandas as pd
import eng_to_ipa as ipa
import json
from pipeline import search
from stats import frequency, collocation, kwic
from wordlist import manager
from layout import components

def render_clickable_word_row(label, words, key_prefix="nav", context=""):
    if not words: return
    st.write(f"**{label}**:")
    cols = st.columns(len(words) if len(words) < 10 else 10)
    for i, w in enumerate(words[:20]): # Limit to 20 visually
        if cols[i % 10].button(w, key=f"{key_prefix}_{context}_{w}_{i}"):
            st.session_state.query = w
            st.rerun()

def render_sense_editor(token, tag, initial_data):
    """
    Renders a form to edit sense fields.
    initial_data: dict with definition, pronunciation, frequency, etc.
    """
    with st.expander(f"📝 Edit Sense ({tag})", expanded=False):
        new_pron = st.text_input("Pronunciation", value=initial_data.get('pronunciation', ''), key=f"edit_pron_{token}_{tag}")
        new_freq = st.number_input("Frequency", value=int(initial_data.get('frequency', 0)), key=f"edit_freq_{token}_{tag}")
        new_def = st.text_area("Definition", value=initial_data.get('definition', ''), key=f"edit_def_{token}_{tag}")
        
        if st.button("Save Changes", key=f"save_{token}_{tag}"):
            if token not in st.session_state['overrides']:
                st.session_state['overrides'][token] = {}
            st.session_state['overrides'][token][tag] = {
                "pronunciation": new_pron,
                "frequency": new_freq,
                "definition": new_def,
                "is_manual": True
            }
            st.success("Saved!")
            st.rerun()

def render(where_clause="1=1", params=(), stop_words=None, collocate_filter=None, skip_punct=True):
    if stop_words is None: stop_words = []
    if collocate_filter is None: collocate_filter = []
    
    if 'overrides' not in st.session_state:
        st.session_state['overrides'] = {}

    
    # Session state for query
    if 'query' not in st.session_state:
        st.session_state.query = ""

    query_input = st.text_input("Search word:", value=st.session_state.get('query', ''))
    query = query_input.strip()
    
    if query:
        # Autocomplete
        suggestions = search.autocomplete(query)
        if suggestions and query not in suggestions:
             cols = st.columns(len(suggestions) if len(suggestions) < 5 else 5)
             for i, sugg in enumerate(suggestions[:5]):
                 if cols[i].button(sugg, key=f"sugg_{sugg}"):
                     st.session_state.query = sugg
                     st.rerun()
        
        # Exact Search
        df = search.search_exact(query)
        
        if df.empty:
            st.warning("No exact match found.")
            fuzzy_tokens = search.search_fuzzy(query)
            if fuzzy_tokens:
                st.write("Did you mean:")
                for ft in fuzzy_tokens:
                    if st.button(ft, key=f"fuzzy_{ft}"):
                        st.session_state.query = ft
                        st.rerun()
            return
            
        # Group by POS
        grouped = df.groupby('tag')

        # Overrides for this query
        query_overrides = st.session_state['overrides'].get(query, {})
        
        # Tags from BOTH corpus and overrides
        all_display_tags = sorted(list(set(list(grouped.groups.keys()) + list(query_overrides.keys()))))
        
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
                
                # 2. Pronunciation
                # Precedence: Override > default IPA
                try:
                    default_pron = ipa.convert(query)
                except:
                    default_pron = query
                pron = override.get('pronunciation') or default_pron
                
                # 3. Frequency
                # Precedence: Override > Corpus
                freq = override.get('frequency') if 'frequency' in override else metrics_corpus['frequency']
                
                # Header
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.header(query)
                c2.text(f"/{pron}/") 
                
                # Wordlists / CEFR
                with c3:
                    st.caption("Wordlists / CEFR")
                    wl_badges = manager.check_token(query)
                    if wl_badges:
                        for b in wl_badges:
                            components.render_badge(f"{b['name']}={b['value']}", type="wordlist")
                    else:
                        st.caption("None")
                
                c4.metric("Frequency", freq)
                with c5:
                    components.render_zipf_band(metrics_corpus['zipf'])
                    
                # PMW Bar
                components.render_pmw_bar(metrics_corpus['pmw'] if not is_override else (freq*1000000/1000000)) # Simple calc if manual
                
                # NEW: Global existence check for troubleshooting
                if freq == 0:
                    global_count = frequency.get_metrics(query, "1=1", [])['frequency']
                    if global_count > 0:
                        st.warning(f"⚠️ **{query}** exists in the database ({global_count} times), but it is hidden by your current **Corpus** or **Metadata** filters. Adjust your sidebar selections to see it.")
                    else:
                        st.error(f"❌ **{query}** not found anywhere in the current database.")

                st.divider()
                
                # Display Definition
                st.write("**Definition**:")
                st.write(curr_def if curr_def else "_No definition provided._")
                
                st.divider()
                
                # Navigation Rows
                render_clickable_word_row("Words from same Lemma", same_lemma_words, key_prefix="lemma", context=tag)
                related = search.get_related_words(query, limit=20)
                render_clickable_word_row(f"Related Words (containing '{query}')", related, key_prefix="related", context=tag)
                
                # Form to Edit
                render_sense_editor(query, tag, {
                    "definition": curr_def,
                    "pronunciation": pron,
                    "frequency": freq
                })
                
                st.write("**All POS Tags**:")
                cols_pos = st.columns(len(all_pos_tags) if len(all_pos_tags) < 10 else 10)
                for j, p in enumerate(all_pos_tags):
                    with cols_pos[j % 10]:
                        st.caption(p) # Simple badge


                
                # External Links
                st.write("**External Links**:")
                st.markdown(f"[Collins Dictionary](https://www.collinsdictionary.com/dictionary/english/{query}) | [Collins Thesaurus](https://www.collinsdictionary.com/dictionary/english-thesaurus/{query})")
                
                st.divider()
                
                # N-Grams
                ngrams = collocation.get_ngrams(query, where_clause=where_clause, params=params, stop_words=stop_words, skip_punct=skip_punct)
                
                st.subheader("Bigrams")
                b1, b2 = st.columns(2)
                with b1:
                    st.markdown(f"**{query} + Word**")
                    st.table(pd.DataFrame(ngrams['bi_search_word'], columns=['Bigram', 'Freq']).head(5))
                with b2:
                    st.markdown(f"**Word + {query}**")
                    st.table(pd.DataFrame(ngrams['bi_word_search'], columns=['Bigram', 'Freq']).head(5))

                st.subheader("Trigrams")
                t1, t2, t3 = st.columns(3)
                with t1:
                    st.markdown(f"**{query} + W + W**")
                    st.table(pd.DataFrame(ngrams['tri_s_w_w'], columns=['Trigram', 'Freq']).head(5))
                with t2:
                    st.markdown(f"**W + {query} + W**")
                    st.table(pd.DataFrame(ngrams['tri_w_s_w'], columns=['Trigram', 'Freq']).head(5))
                with t3:
                    st.markdown(f"**W + W + {query}**")
                    st.table(pd.DataFrame(ngrams['tri_w_w_s'], columns=['Trigram', 'Freq']).head(5))
                
                # Collocates
                st.subheader("Top-20 Collocates (Log-Likelihood)")
                collocs = collocation.get_collocates(query, limit=20, where_clause=where_clause, params=params, stop_words=stop_words, allowed_words=collocate_filter, skip_punct=skip_punct)
                st.dataframe(pd.DataFrame(collocs)) # dataframe better for larger lists
                
                st.divider()
                
                # KWIC
                st.subheader("Examples (KWIC)")
                kwic_lines = kwic.get_kwic_lines(query, where_clause=where_clause, params=params, limit=10)
                for line in kwic_lines:
                     st.markdown(f"""
                    <div style="display: flex; justify-content: center; font-family: monospace;">
                        <span style="text-align: right; width: 45%; margin-right: 10px;">{line['left']}</span>
                        <span style="font-weight: bold; color: red;">{line['node']}</span>
                        <span style="text-align: left; width: 45%; margin-left: 10px;">{line['right']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Collocate Examples
                st.subheader("Examples by Collocates")
                # Pick top 3 collocates for examples
                top_collocs = [c['collocate'] for c in collocs[:3]]
                for col_word in top_collocs:
                    with st.expander(f"Usage with '{col_word}'", expanded=True):
                        col_examples = kwic.get_collocate_kwic(query, col_word, where_clause=where_clause, params=params, limit=3)
                        if col_examples:
                            for ex in col_examples:
                                components.render_collocate_example(ex['left'], ex['node'], ex['right'], ex['col_token'])
                        else:
                            st.caption("No specific examples found for this pair.")
                
                # Save Button
                st.divider()
                export_data = {
                    "token": query,
                    "tag": tag,
                    "definition": curr_def,
                    "metrics": metrics_corpus,
                    "collocates": collocs,
                    "examples": kwic_lines
                }
                json_str = json.dumps(export_data, indent=2)
                st.download_button(
                    label="💾 Save Entry to JSON",
                    data=json_str,
                    file_name=f"{query}_{tag}_entry.json",
                    mime="application/json"
                )

        # "Add Sense" Tab content
        with tabs[-1]:
            st.header("Add New Sense")
            st.info("Manually define all fields for a new sense.")
            
            with st.form("new_sense_form"):
                new_tag = st.text_input("POS Tag (e.g., NN, VB)")
                new_pron = st.text_input("Pronunciation")
                new_freq = st.number_input("Initial Frequency", value=0)
                new_def_manual = st.text_area("Definition")
                
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
                            "is_manual": True
                        }
                        st.success(f"New sense for {query} ({new_tag}) added!")
                        st.rerun()
