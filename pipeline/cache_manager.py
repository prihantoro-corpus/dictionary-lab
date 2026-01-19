import streamlit as st
from stats import frequency, collocation, kwic

# Wrapper to invalidate cache when corpus changes
# The 'corpus_hash' argument must change when the DB changes.
# We will use total_tokens as a simple proxy for the hash.

@st.cache_data(persist="disk", show_spinner=False)
def get_metrics(corpus_hash, token, where_clause="1=1", params=(), pos_tag=None):
    return frequency.get_metrics(token, where_clause, params, pos_tag)

@st.cache_data(persist="disk", show_spinner=False)
def get_max_frequency(corpus_hash, where_clause="1=1", params=()):
    return frequency.get_max_frequency(where_clause, params)

@st.cache_data(persist="disk", show_spinner=False)
def get_pmw_range(corpus_hash, where_clause="1=1", params=()):
    return frequency.get_pmw_range(where_clause, params)

@st.cache_data(persist="disk", show_spinner=False)
def get_ngrams(corpus_hash, token, limit=10, where_clause="1=1", params=(), stop_words=None, skip_punct=True, pos_tag=None):
    return collocation.get_ngrams(token, limit, where_clause, params, stop_words, skip_punct, pos_tag)

@st.cache_data(persist="disk", show_spinner=False)
def get_collocates(corpus_hash, token, window=5, limit=20, where_clause="1=1", params=(), stop_words=None, allowed_words=None, skip_punct=True, pos_tag=None):
    return collocation.get_collocates(token, window, limit, where_clause, params, stop_words, allowed_words, skip_punct, pos_tag)

@st.cache_data(persist="disk", show_spinner=False)
def get_kwic_lines(corpus_hash, token, window=7, limit=50, where_clause="1=1", params=(), pos_tag=None):
    return kwic.get_kwic_lines(token, window, limit, where_clause, params, pos_tag)

@st.cache_data(persist="disk", show_spinner=False)
def get_collocate_kwic(corpus_hash, token, collocate, window=7, limit=5, where_clause="1=1", params=(), pos_tag=None):
    return kwic.get_collocate_kwic(token, collocate, window, limit, where_clause, params, pos_tag)
