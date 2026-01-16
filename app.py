import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Corpus Dictionary", layout="wide")

# ===============================
# Load all Excel files in repo dir
# ===============================

@st.cache_data
def load_all_excels():
    base_path = os.path.dirname(os.path.abspath(__file__))
    dfs = []

    for file in os.listdir(base_path):
        if file.lower().endswith(".xlsx"):
            full_path = os.path.join(base_path, file)
            df = pd.read_excel(full_path)
            df["__source_file__"] = file
            dfs.append(df)

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

data = load_all_excels()

if data.empty:
    st.error("No Excel files found in the project directory.")
    st.stop()

# ===============================
# Helpers
# ===============================

def safe(val):
    if pd.isna(val):
        return ""
    return str(val).strip()


def parse_wordlist_badges(wordlist_text):
    if pd.isna(wordlist_text):
        return []
    text = str(wordlist_text).strip()
    return [p.strip() for p in text.split(";") if p.strip()]


def render_badges(badges):
    if not badges:
        return
    cols = st.columns(len(badges))
    for i, badge in enumerate(badges):
        cols[i].markdown(
            f"""
            <div style="
                padding:4px 10px;
                border-radius:12px;
                background-color:#e8f0fe;
                color:#1a237e;
                font-size:12px;
                text-align:center;
                border:1px solid #c5cae9;
                display:inline-block;
                white-space:nowrap;
            ">
            {badge}
            </div>
            """,
            unsafe_allow_html=True
        )


def parse_ngrams_structured(ngram_text):
    if pd.isna(ngram_text):
        return {}

    text = str(ngram_text).strip()

    # Remove Excel wrapping quotes
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]

    # Normalize newlines
    text = text.replace("\r", " ").replace("\n", " ")

    result = {}
    current_section = None

    parts = text.split(";")

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if ">" in part and part.lower().startswith(("bigram", "trigram", "fourgram")):
            section, rest = part.split(">", 1)
            current_section = section.strip().lower()
            result[current_section] = []
            part = rest.strip()

        if "=" in part and current_section:
            left, right = part.split("=", 1)
            result[current_section].append((left.strip(), right.strip()))

    return result


def render_ngrams_block(ngram_text):
    ngrams = parse_ngrams_structured(ngram_text)
    if not ngrams:
        return

    st.markdown("**N-grams**")
    for gram_type, items in ngrams.items():
        st.markdown(f"*{gram_type.capitalize()}*")
        for left, right in items:
            st.markdown(f"- `{left}` → **{right}**")


def render_zipf_bar(zipf_value):
    try:
        val = float(zipf_value)
        norm = min(val / 7.0, 1.0)
        st.progress(norm)
    except:
        pass


# ===============================
# UI
# ===============================

st.title("Corpus Dictionary")

search_term = st.text_input("Search word", "")

if search_term:
    filtered = data[data["general_word"].str.lower() == search_term.lower()]
else:
    filtered = data

if filtered.empty:
    st.warning("No entries found.")
    st.stop()

row = filtered.iloc[0]

# ===============================
# GENERAL BOX
# ===============================

st.markdown("## " + safe(row.get("general_word")).upper())

# Wordlist badges (general)
general_badges = parse_wordlist_badges(row.get("general_wordlist", ""))
render_badges(general_badges)

col1, col2 = st.columns([3, 1])

with col1:
    st.write(f"**Corpus:** {safe(row.get('general_corpus'))}")
    st.write(f"**Frequency:** {safe(row.get('general_frequency'))}  |  **PMW:** {safe(row.get('general_pmw'))}")
    st.write(f"**Band:** {safe(row.get('general_band'))}")

with col2:
    render_zipf_bar(row.get("general_zipf", 0))

# External links
if safe(row.get("general_dictionary")):
    st.markdown(f"[Dictionary]({safe(row.get('general_dictionary'))})")
if safe(row.get("general_thesaurus")):
    st.markdown(f"[Thesaurus]({safe(row.get('general_thesaurus'))})")

# Related forms
if safe(row.get("general_related_headword")):
    st.write(f"**Related headwords:** {safe(row.get('general_related_headword'))}")

if safe(row.get("general_related_regex")):
    st.write(f"**Related patterns (regex):** {safe(row.get('general_related_regex'))}")

# N-grams (general)
render_ngrams_block(row.get("general_n-gram_POS", ""))

st.divider()

# ===============================
# SENSES 1–3
# ===============================

for i in range(1, 4):
    sense_word = row.get(f"sense{i}_headword", "")

    if pd.isna(sense_word) or not str(sense_word).strip():
        continue

    st.markdown(f"### Sense {i}: {safe(sense_word)} ({safe(row.get(f'sense{i}_pos'))})")

    # Definition
    st.write(safe(row.get(f"sense{i}_definition")))

    meta_col1, meta_col2, meta_col3 = st.columns([2, 2, 2])

    with meta_col1:
        st.write(f"**Frequency:** {safe(row.get(f'sense{i}_frequency'))}")
        st.write(f"**PMW:** {safe(row.get(f'sense{i}_pmw'))}")

    with meta_col2:
        st.write(f"**Band:** {safe(row.get(f'sense{i}_band'))}")
        st.write(f"**Domain:** {safe(row.get(f'sense{i}_domain'))}")

    with meta_col3:
        st.write(f"**Register:** {safe(row.get(f'sense{i}_register'))}")
        st.write(f"**Year(s):** {safe(row.get(f'sense{i}_year'))}")

    render_zipf_bar(row.get(f"sense{i}_zipf", 0))

    # Typical collocates
    if safe(row.get(f"sense{i}_typical_collocates")):
        st.write(f"**Typical collocates:** {safe(row.get(f'sense{i}_typical_collocates'))}")

    # Example (NOT collapsible)
    example = row.get(f"sense{i}_example", "")
    if safe(example):
        st.markdown(f"> {safe(example)}")

    st.divider()
