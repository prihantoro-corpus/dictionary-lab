
import streamlit as st
import pandas as pd
import eng_to_ipa as ipa
import json
from pipeline import search
from stats import frequency, collocation, kwic
from wordlist import manager
from layout import components

def render(where_clause="1=1", params=(), stop_words=None, collocate_filter=None):
    if stop_words is None: stop_words = []
    if collocate_filter is None: collocate_filter = []
    
    st.title("Dictionary Search")
    
    # Session state for query
    if 'query' not in st.session_state:
        st.session_state.query = ""

    query = st.text_input("Search word:", value=st.session_state.query)
    
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
        
        # Sense Tabs + Add Sense
        sense_labels = [f"Sense: {tag}" for tag in grouped.groups.keys()]
        sense_labels.append("➕ Add Sense")
        
        tabs = st.tabs(sense_labels)
        
        # Pre-fetch common data
        lemma = search.get_lemma(query)
        same_lemma_words = search.get_forms_by_lemma(lemma)
        all_pos_tags = search.get_pos_tags(query)
        
        # Render existing senses
        for i, (tag, group_df) in enumerate(grouped):
            with tabs[i]:
                token = query # or group_df.iloc[0]['token']
                
                # Metrics
                metrics = frequency.get_metrics(token, where_clause, params)
                
                # Header
                c1, c2, c3, c4 = st.columns(4)
                c1.header(token)
                try:
                    pron = ipa.convert(token)
                except:
                    pron = token
                c2.text(f"/{pron}/") 
                c3.metric("Frequency", metrics['frequency'])
                with c4:
                    components.render_zipf_band(metrics['zipf'])
                    
                components.render_pmw_bar(metrics['pmw'])
                
                st.divider()
                
                # Definition
                def_key = f"def_{token}_{tag}"
                curr_def = st.session_state.get(def_key, "")
                new_def = st.text_area("Definition", value=curr_def, key=f"input_{def_key}")
                if new_def != curr_def:
                    st.session_state[def_key] = new_def
                
                # Info Block
                st.write(f"**Headword/Lemma**: {lemma}")
                
                display_forms = same_lemma_words[:20]
                distinct_forms_str = ', '.join(display_forms)
                if len(same_lemma_words) > 20:
                    distinct_forms_str += f", ... (+{len(same_lemma_words)-20} more)"
                st.write(f"**Words from same Lemma**: {distinct_forms_str}")
                
                # Related Words (Regex/Infix match)
                related = search.get_related_words(token, limit=20)
                if related:
                     st.write(f"**Related Words** (containing '{token}'): {', '.join(related)}")
                
                st.write("**All POS Tags**:")
                cols_pos = st.columns(len(all_pos_tags) if len(all_pos_tags) < 10 else 10)
                for j, p in enumerate(all_pos_tags):
                    with cols_pos[j % 10]:
                        st.caption(p) # Simple badge

                # Wordlists
                wl_badges = manager.check_token(token)
                if wl_badges:
                    st.write("**Wordlists**:")
                    cols_wl = st.columns(len(wl_badges) if len(wl_badges) < 6 else 6)
                    for j, b in enumerate(wl_badges):
                        with cols_wl[j % 6]:
                            components.render_badge(f"{b['name']}={b['value']}", type="wordlist")
                
                # External Links
                st.write("**External Links**:")
                st.markdown(f"[Collins Dictionary](https://www.collinsdictionary.com/dictionary/english/{token}) | [Collins Thesaurus](https://www.collinsdictionary.com/dictionary/english-thesaurus/{token})")
                
                st.divider()
                
                # N-Grams
                ngrams = collocation.get_ngrams(token, where_clause=where_clause, params=params)
                
                st.subheader("Bigrams")
                b1, b2 = st.columns(2)
                with b1:
                    st.markdown(f"**{token} + Word**")
                    st.table(pd.DataFrame(ngrams['bi_search_word'], columns=['Bigram', 'Freq']).head(5))
                with b2:
                    st.markdown(f"**Word + {token}**")
                    st.table(pd.DataFrame(ngrams['bi_word_search'], columns=['Bigram', 'Freq']).head(5))

                st.subheader("Trigrams")
                t1, t2, t3 = st.columns(3)
                with t1:
                    st.markdown(f"**{token} + W + W**")
                    st.table(pd.DataFrame(ngrams['tri_s_w_w'], columns=['Trigram', 'Freq']).head(5))
                with t2:
                    st.markdown(f"**W + {token} + W**")
                    st.table(pd.DataFrame(ngrams['tri_w_s_w'], columns=['Trigram', 'Freq']).head(5))
                with t3:
                    st.markdown(f"**W + W + {token}**")
                    st.table(pd.DataFrame(ngrams['tri_w_w_s'], columns=['Trigram', 'Freq']).head(5))
                
                # Collocates
                st.subheader("Top-20 Collocates (Log-Likelihood)")
                collocs = collocation.get_collocates(token, limit=20, where_clause=where_clause, params=params, stop_words=stop_words, allowed_words=collocate_filter)
                st.dataframe(pd.DataFrame(collocs)) # dataframe better for larger lists
                
                st.divider()
                
                # KWIC
                st.subheader("Examples (KWIC)")
                kwic_lines = kwic.get_kwic_lines(token, where_clause=where_clause, params=params, limit=10)
                for line in kwic_lines:
                     st.markdown(f"""
                    <div style="display: flex; justify-content: center; font-family: monospace;">
                        <span style="text-align: right; width: 45%; margin-right: 10px;">{line['left']}</span>
                        <span style="font-weight: bold; color: red;">{line['node']}</span>
                        <span style="text-align: left; width: 45%; margin-left: 10px;">{line['right']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Save Button
                st.divider()
                export_data = {
                    "token": token,
                    "tag": tag,
                    "definition": new_def,
                    "metrics": metrics,
                    "collocates": collocs,
                    "examples": kwic_lines
                }
                json_str = json.dumps(export_data, indent=2)
                st.download_button(
                    label="💾 Save Entry to JSON",
                    data=json_str,
                    file_name=f"{token}_{tag}_entry.json",
                    mime="application/json"
                )

        # "Add Sense" Tab content
        with tabs[-1]:
            st.header("Add New Sense")
            st.info("This feature allows you to define a new sense for the word manually.")
            new_pos = st.text_input("POS Tag (e.g., NN, VB)")
            new_def_manual = st.text_area("Definition")
            if st.button("Save New Sense"):
                 st.success(f"New sense for {query} ({new_pos}) saved! (Simulated)")
