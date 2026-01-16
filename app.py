import streamlit as st
import pandas as pd
import re

# =========================
# Page config
# =========================
st.set_page_config(page_title="Lexicographic Viewer", layout="wide")

# =========================
# Global CSS (black bg, white text, chips)
# =========================
st.markdown("""
<style>
body, .stApp {
    background-color: #000000;
    color: #ffffff;
}

.section-box {
    border: 1px solid #333;
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 16px;
    background-color: #0f0f0f;
}

.section-title {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 8px;
}

.meta-line {
    font-size: 14px;
    margin-bottom: 4px;
}

.label {
    color: #bbbbbb;
    font-weight: 600;
}

.chip {
    display: inline-block;
    padding: 4px 10px;
    margin: 4px 6px 4px 0;
    border-radius: 14px;
    background-color: #1f1f1f;
    border: 1px solid #555;
    font-size: 13px;
}

hr {
    border: none;
    border-top: 1px solid #333;
    margin: 16px 0;
}
</style>
""", unsafe_allow_html=True)

# =========================
# Helpers
# =========================
def safe(row, col):
    if col in row and pd.notna(row[col]) and str(row[col]).strip() != "":
        return str(row[col]).strip()
    return ""

def render_chips(text):
    if not text:
        return ""
    items = [t.strip() for t in re.split(r"[;,|]", text) if t.strip()]
    return "".join([f"<span class='chip'>{item}</span>" for item in items])

# =========================
# Load data
# =========================
st.title("Lexicographic Entry Viewer")

uploaded = st.file_uploader("Upload your Excel file", type=["xlsx"])
if not uploaded:
    st.stop()

df = pd.read_excel(uploaded)

# =========================
# Select entry
# =========================
if "general_word" not in df.columns:
    st.error("Column 'general_word' not found.")
    st.stop()

word = st.selectbox("Select entry", df["general_word"].dropna().unique())
row = df[df["general_word"] == word].iloc[0]

# =========================
# GENERAL SECTION
# =========================
general_html = f"""
<div class="section-box">
  <div class="section-title">{safe(row,'general_word')}</div>
  <div class="meta-line"><span class="label">Corpus:</span> {safe(row,'general_corpus')}</div>
  <div class="meta-line"><span class="label">Frequency:</span> {safe(row,'general_frequency')} | <span class="label">PMW:</span> {safe(row,'general_pmw')}</div>
  <div class="meta-line"><span class="label">Zipf:</span> {safe(row,'general_zipf')} | <span class="label">Band:</span> {safe(row,'general_band')}</div>
</div>
"""
st.markdown(general_html, unsafe_allow_html=True)

# ===== GENERAL N-GRAMS (before related headwords)
g_bigram = safe(row, "general_bigram")
g_trigram = safe(row, "general_trigram")

if g_bigram or g_trigram:
    st.markdown("### N-grams")
    if g_bigram:
        st.markdown(render_chips(g_bigram), unsafe_allow_html=True)
    if g_trigram:
        st.markdown(render_chips(g_trigram), unsafe_allow_html=True)

# ===== Dictionary / Thesaurus
if safe(row, "general_dictionary"):
    st.markdown("**Dictionary**")
    st.markdown(safe(row, "general_dictionary"))

if safe(row, "general_thesaurus"):
    st.markdown("**Thesaurus**")
    st.markdown(safe(row, "general_thesaurus"))

# ===== Related headwords / regex
if safe(row, "general_related_headword"):
    st.markdown(f"**Related headwords:** {safe(row,'general_related_headword')}")

if safe(row, "general_related_regex"):
    st.markdown(f"**Related patterns (regex):** {safe(row,'general_related_regex')}")

st.markdown("<hr>", unsafe_allow_html=True)

# =========================
# DETECT SENSES DYNAMICALLY (REGEX)
# =========================
sense_numbers = sorted({
    int(m.group(1))
    for col in df.columns
    for m in [re.match(r"sense(\d+)_headword", col)]
    if m
})

# =========================
# RENDER SENSES
# =========================
for i in sense_numbers:
    if not safe(row, f"sense{i}_headword"):
        continue

    sense_html = f"""
    <div class="section-box">
      <div class="section-title">Sense {i}: {safe(row,f'sense{i}_headword')} ({safe(row,f'sense{i}_pos')})</div>
      <div class="meta-line"><span class="label">Frequency:</span> {safe(row,f'sense{i}_frequency')} | <span class="label">PMW:</span> {safe(row,f'sense{i}_pmw')}</div>
      <div class="meta-line"><span class="label">Zipf:</span> {safe(row,f'sense{i}_zipf')} | <span class="label">Band:</span> {safe(row,f'sense{i}_band')}</div>
      <div class="meta-line"><span class="label">Domain:</span> {safe(row,f'sense{i}_domain')} | <span class="label">Register:</span> {safe(row,f'sense{i}_register')}</div>
      <div class="meta-line"><span class="label">Year(s):</span> {safe(row,f'sense{i}_year')}</div>
      <div class="meta-line"><span class="label">Definition:</span> {safe(row,f'sense{i}_definition')}</div>
    </div>
    """
    st.markdown(sense_html, unsafe_allow_html=True)

    # ===== SENSE N-GRAMS (before typical collocates)
    s_bigram = safe(row, f"sense{i}_bigram")
    s_trigram = safe(row, f"sense{i}_trigram")

    if s_bigram or s_trigram:
        st.markdown("### N-grams")
        if s_bigram:
            st.markdown(render_chips(s_bigram), unsafe_allow_html=True)
        if s_trigram:
            st.markdown(render_chips(s_trigram), unsafe_allow_html=True)

    # ===== Typical collocates
    if safe(row, f"sense{i}_typical_collocates"):
        st.markdown(f"**Typical collocates:** {safe(row,f'sense{i}_typical_collocates')}")

    # ===== Example
    if safe(row, f"sense{i}_example"):
        st.markdown(f"**Example:** {safe(row,f'sense{i}_example')}")

    st.markdown("<hr>", unsafe_allow_html=True)
