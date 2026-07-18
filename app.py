import streamlit as st
import layout.sidebar as sidebar
import layout.main_view as main_view
from pipeline.indexing import init_db

# Page Config
st.set_page_config(
    page_title="Corpus-Driven Dictionary",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize DB on first load check
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# Main App Control
def main():
    # Render Sidebar
    filters = sidebar.render()

    if st.session_state.get('corpus_loaded_success_msg'):
        st.success(st.session_state['corpus_loaded_success_msg'])
        del st.session_state['corpus_loaded_success_msg']
        
    import time
    start_render = time.time()
    
    with st.spinner("Crunching data and rendering interface... (This may take a few minutes for very large corpora)"):
        # Render Main View
        main_view.render(
            where_clause=filters['where_clause'], 
            params=filters['params'],
            stop_words=filters['stop_words'],
            collocate_filter=filters['collocate_filter'],
            skip_punct=filters.get('skip_punct', True),
            no_corpora=filters.get('no_corpora', False)
        )
        
    end_render = time.time()
    duration = end_render - start_render
    
    if duration > 0.1:
        st.caption(f"⏱️ **Performance:** Interface rendered in {duration:.2f} seconds")

if __name__ == "__main__":
    main()
