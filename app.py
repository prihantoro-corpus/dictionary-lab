import streamlit as st
import pandas as pd
from glob import glob

st.set_page_config(layout="wide")

# =======================
# STYLE (BLACK BG, WHITE TEXT)
# =======================
st.markdown("""
<style>
body, .stApp {
    background-color: #000000;
    color: #ffffff;
}
.block {
    background-color: #111111;
    padding: 18px;
    border-radius: 10px;
    margin-bottom: 20px;
}
.chip {
    display: inline-block;
    padding: 5px 12px;
    margin: 4px 6px 4px 0;
    border-radius: 16px;
    background-color: #1f3a5f;
    color: #ffffff;
    font-size: 13px;
}
.zipf-bar {
    height: 8px;
    background-color: #f4c430;
    border-radius: 4px;
    margin: 6px 0 10px 0;
}
a { color: #4da6ff; }
h1, h2, h3, h4 { color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# =======================
# HELPERS
# =======================
def safe(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def render_chips(text):
    if not text:
        return ""
    parts = [p.strip() for p in str(text).split(";") if p.strip()]
    return "".join([f"<span class='chip'>{p}</span>" for p in parts])

def zipf_bar(val):
    try:
        v = float(val)
        width = min((v / 7.0) * 100, 100)
        return f"<div class='zipf-bar' style='width:{width}%'></div>"
    except:
        return ""

# =======================
# LOAD ALL EXCEL FILES
# =======================
def load_all_excels():
    files = glob("*.xlsx")
    dfs = []
    for f in files:
        try:
            df = pd.read_excel(f)
            df["__sourcefile"] = f
            dfs.append(df)
        except:
            pass
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

df = load_all_excels()

st.title("Corpus-Based Dictionary Viewer")

if df.empty:
    st.error("No Excel files found in the project folder.")
    st.stop()

# =======================
# SEARCH
# =======================
query = st.text_input("Search headword")

if not query:
    st.stop()

row = df[df["general_word"].str.lower() == query.lower()]

if row.empty:
    st.warning("Word not found.")
    st.stop()

row = row.iloc[0]

# =======================
# GENERAL BLOCK
# =======================
st.markdown("<div class='block'>", unsafe_allow_html=True)
st.markdown(f"## {safe(row.get('general_word')).upper()}")
st.markdown("### General")

st.markdown(f"**Corpus:** {safe(row.get('general_corpus'))}")
st.markdown(f"**Frequency:** {safe(row.get('general_frequency'))} | **PMW:** {safe(row.get('general_pmw'))}")
st.markdown(f"**Zipf:** {safe(row.get('general_zipf'))} | **Band:** {safe(row.get('general_band'))}")

st.markdown(zipf_bar(row.get("general_zipf")), unsafe_allow_html=True)

# ---- GENERAL N-GRAMS (HERE, BEFORE RELATED HEADWORDS) ----
general_bigram = safe(row.get("general_bigram"))
general_trigram = safe(row.get("general_trigram"))

if general_bigram or general_trigram:
    st.markdown("**N-grams**")
    st.markdown(render_chips(general_bigram + ";" + general_trigram), unsafe_allow_html=True)

# ---- LINKS ----
if safe(row.get("general_dictionary")):
    st.markdown(f"[Dictionary]({safe(row.get('general_dictionary'))})")
if safe(row.get("general_thesaurus")):
    st.markdown(f"[Thesaurus]({safe(row.get('general_thesaurus'))})")

# ---- RELATED ----
if safe(row.get("general_related_headword")):
    st.markdown(f"**Related headwords:** {safe(row.get('general_related_headword'))}")
if safe(row.get("general_related_regex")):
    st.markdown(f"**Related patterns (regex):** {safe(row.get('general_related_regex'))}")

st.markdown("</div>", unsafe_allow_html=True)

# =======================
# SENSES
# =======================
for i in range(1, 10):
    head = safe(row.get(f"sense{i}_headword"))
    if not head:
        continue

    st.markdown("<div class='block'>", unsafe_allow_html=True)
    pos = safe(row.get(f"sense{i}_pos"))

    st.markdown(f"### Sense {i}: {head} ({pos})")

    st.markdown(f"**Frequency:** {safe(row.get(f'sense{i}_frequency'))} | **PMW:** {safe(row.get(f'sense{i}_pmw'))}")
    st.markdown(f"**Zipf:** {safe(row.get(f'sense{i}_zipf'))} | **Band:** {safe(row.get(f'sense{i}_band'))}")

    st.markdown(zipf_bar(row.get(f"sense{i}_zipf")), unsafe_allow_html=True)

    st.markdown(f"**Domain:** {safe(row.get(f'sense{i}_domain'))} | **Register:** {safe(row.get(f'sense{i}_register'))}")
    st.markdown(f"**Year(s):** {safe(row.get(f'sense{i}_year'))}")

    # ---- SENSE N-GRAMS (HERE, BEFORE TYPICAL COLLOCATES) ----
    sense_bigram = safe(row.get(f"sense{i}_bigram"))
    sense_trigram = safe(row.get(f"sense{i}_trigram"))

    if sense_bigram or sense_trigram:
        st.markdown("**N-grams**")
        st.markdown(render_chips(sense_bigram + ";" + sense_trigram), unsafe_allow_html=True)

    st.markdown(f"**Definition:** {safe(row.get(f'sense{i}_definition'))}")

    st.markdown(f"**Typical collocates:** {safe(row.get(f'sense{i}_typical_collocates'))}")
    st.markdown(f"**Example:** {safe(row.get(f'sense{i}_example'))}")

    st.markdown("</div>", unsafe_allow_html=True)
