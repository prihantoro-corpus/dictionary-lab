```python
import streamlit as st
import pandas as pd
import eng_to_ipa as ipa
from pipeline import search
from stats import frequency, collocation, kwic
from wordlist import manager
from layout import components

def render(where_clause="1=1", params=()):
    st.title("Dictionary Search")
    
    # Search Box
    # Simple Text Input for now. 
    # For "Autocomplete", we can show a selectbox of suggestions if query is typed
    
    # Session state for query
    if 'query' not in st.session_state:
        st.session_state.query = ""

    query = st.text_input("Search word:", value=st.session_state.query)
    
    if query:
        # Autocomplete / Suggestions
        suggestions = search.autocomplete(query)
        if suggestions and query not in suggestions:
             cols = st.columns(len(suggestions) if len(suggestions) < 5 else 5)
             for i, sugg in enumerate(suggestions[:5]):
                 if cols[i].button(sugg, key=f"sugg_{sugg}"):
                     st.session_state.query = sugg
                     st.experimental_rerun()
        
        # Exact Search
        df = search.search_exact(query)
        
        if df.empty:
            st.warning("No exact match found.")
            # Fuzzy
            fuzzy_tokens = search.search_fuzzy(query)
            if fuzzy_tokens:
                st.write("Did you mean:")
                for ft in fuzzy_tokens:
                    if st.button(ft, key=f"fuzzy_{ft}"):
                        st.session_state.query = ft
                        st.experimental_rerun()
            return
            
        # Group by POS (Tag) -> Senses
        # Different corpora might use different tagsets, but we group by the 'tag' column.
        # Use pandas grouping
        grouped = df.groupby('tag')
        
        tabs = st.tabs([f"Sense: {tag}" for tag in grouped.groups.keys()])
        
        for i, (tag, group_df) in enumerate(grouped):
            with tabs[i]:
                # Take the first entry as representative for lemma/headword (or aggregated?)
                # Usually same token + same tag = same lemma.
                rep = group_df.iloc[0]
                token = rep['token']
                lemma = rep['lemma']
                
                # Stats (Calculated on the fly based on filters)
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
                    
                # PMW Bar
                components.render_pmw_bar(metrics['pmw'])
                
                st.divider()
                
                # Definition (Editable - Mock saving)
                def_key = f"def_{token}_{tag}"
                curr_def = st.session_state.get(def_key, "")
                new_def = st.text_area("Definition", value=curr_def, key=f"input_{def_key}")
                if new_def != curr_def:
                    st.session_state[def_key] = new_def
                    # Save mechanism would go here (update JSON)
                
                # Metadata / Lemma info
                st.write(f"**Lemma**: {lemma}")
                
                # Wordlist Badges
                wl_badges = manager.check_token(token)
                if wl_badges:
                    st.write("**Wordlists**:")
                    cols = st.columns(len(wl_badges) if len(wl_badges) < 6 else 6)
                    for i, b in enumerate(wl_badges):
                        with cols[i % 6]:
                            components.render_badge(f"{b['name']}={b['value']}", type="wordlist")
                
                # Associated Words (Simulated)
                st.write("**Related Words**: "+ ", ".join(search.autocomplete(lemma, limit=5)))
                
                st.divider()
                
                # N-Grams
                ngrams = collocation.get_ngrams(token, where_clause=where_clause, params=params)
                c_bi, c_tri = st.columns(2)
                with c_bi:
                    st.subheader("Top Bigrams")
                    st.table(pd.DataFrame(ngrams['forward_bigrams'], columns=['Bigram', 'Freq']).head(5))
                with c_tri:
                    st.subheader("Top-5 Collocates (Log-Likelihood)")
                    collocs = collocation.get_collocates(token, where_clause=where_clause, params=params)
                    st.table(pd.DataFrame(collocs).head(5))
                    
                st.divider()
                
                # Examples (KWIC)
                st.subheader("Examples (KWIC)")
                kwic_lines = kwic.get_kwic_lines(token, where_clause=where_clause, params=params, limit=10)
                
                for line in kwic_lines:
                    # Simple KWIC display: RIGHT ALIGN left context, BOLD node, LEFT ALIGN right context
                    # Streamlit columns alignment is tricky. Using markdown table or HTML.
                    
                    st.markdown(f"""
                    <div style="display: flex; justify-content: center; font-family: monospace;">
                        <span style="text-align: right; width: 45%; margin-right: 10px;">{line['left']}</span>
                        <span style="font-weight: bold; color: red;">{line['node']}</span>
                        <span style="text-align: left; width: 45%; margin-left: 10px;">{line['right']}</span>
                    </div>
                    """, unsafe_allow_html=True)
