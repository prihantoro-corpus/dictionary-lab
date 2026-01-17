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

    # Render Main View
    # Pass the entire filters dict or unpack
    main_view.render(
        where_clause=filters['where_clause'], 
        params=filters['params'],
        stop_words=filters['stop_words'],
        collocate_filter=filters['collocate_filter'],
        skip_punct=filters.get('skip_punct', True)
    )

if __name__ == "__main__":
    main()
