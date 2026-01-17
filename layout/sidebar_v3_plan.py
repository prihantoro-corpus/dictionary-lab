import streamlit as st
from pipeline.indexing import get_connection

# Update to helpers
def get_metadata_keys(corpora=None):
    # WHERE corpus IN (...)
    pass

def get_metadata_values(key, corpora=None):
    # WHERE corpus IN (...)
    pass

def render():
    st.sidebar.title("CORPUS")
    all_corpora = get_corpora()
    
    # Initialize session state for loaded corpora if not present
    if 'loaded_corpora' not in st.session_state:
        st.session_state['loaded_corpora'] = [] # Start empty or default? User said "User must first choose...". So empty.
        
    # Selection
    selected = st.sidebar.multiselect("Select Corpora", all_corpora)
    
    # Load Button
    if st.sidebar.button("Load"):
        st.session_state['loaded_corpora'] = selected
        st.rerun()
        
    # Display Badge of active
    active = st.session_state['loaded_corpora']
    if not active:
        st.sidebar.warning("No corpus loaded. Please select and load.")
        return {'where_clause': "1=0", ...}
        
    st.sidebar.caption(f"Active: {len(active)} corpora")
    
    # METADATA - Pass active to get_metadata_*
    # ...
