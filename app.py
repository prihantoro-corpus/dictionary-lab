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

# ── Global compact layout (reduce scrolling) ─────────────────────────
st.markdown("""
<style>
/* Main area */
.block-container {padding-top:0.5rem !important; padding-bottom:1rem !important;
                  padding-left:1.5rem !important; padding-right:1.5rem !important; max-width:100% !important;}
div[data-testid="stVerticalBlock"] {gap:0.55rem !important;}
div[data-testid="stHorizontalBlock"] {gap:0.65rem !important;}
h1 {font-size:1.65rem !important; padding:0.3rem 0 0.1rem !important; margin:0 !important;}
h2 {font-size:1.35rem !important; padding:0.2rem 0 !important; margin:0 !important;}
h3 {font-size:1.15rem !important; padding:0.15rem 0 !important; margin:0 !important;}
h4, h5 {font-size:1rem !important; padding:0.05rem 0 !important; margin:0 !important;}
p, li {margin-bottom:0.25rem !important;}
hr {margin:0.5rem 0 !important;}
div[data-testid="stCaptionContainer"] {margin:0.1rem 0 !important;}
div[data-testid="stMarkdownContainer"] p {line-height:1.45;}

/* Expanders */
div[data-testid="stExpander"] details summary {padding:0.3rem 0.6rem !important; font-size:0.9rem;}
div[data-testid="stExpander"] details div[data-testid="stExpanderDetails"] {padding:0.3rem 0.6rem 0.5rem !important;}

/* Tabs */
button[data-baseweb="tab"] {padding:0.25rem 0.7rem !important; height:auto !important;}
div[data-baseweb="tab-panel"] {padding-top:0.5rem !important;}

/* Buttons & inputs */
.stButton > button, .stDownloadButton > button {padding:0.15rem 0.6rem !important; min-height:1.9rem !important;}
div[data-baseweb="input"] input, div[data-baseweb="select"] > div {min-height:2rem !important;}
div[data-testid="stRadio"] > div {gap:0.4rem !important;}
label[data-testid="stWidgetLabel"] {margin-bottom:0.1rem !important; min-height:0 !important;}

/* Alerts / metrics / dataframes */
div[data-testid="stAlert"] {padding:0.4rem 0.7rem !important;}
div[data-testid="stMetric"] {padding:0.2rem 0 !important;}

/* Sidebar */
section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {padding-top:0.6rem !important;}
section[data-testid="stSidebar"] .block-container,
section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {padding:0.7rem 1rem !important;}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {gap:0.45rem !important;}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {font-size:1.08rem !important;}
/* Sidebar expanders must NOT overlap the main area */
section[data-testid="stSidebar"] div[data-baseweb="select"] {z-index:100 !important;}
section[data-testid="stSidebar"] div[data-baseweb="popover"],
section[data-testid="stSidebar"] div[data-baseweb="menu"],
section[data-testid="stSidebar"] div[role="listbox"],
section[data-testid="stSidebar"] ul[role="listbox"] {z-index:200 !important;}
</style>
""", unsafe_allow_html=True)

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
