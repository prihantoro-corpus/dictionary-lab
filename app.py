import streamlit as st
import pandas as pd

# =========================
# Page config
# =========================
st.set_page_config(
    page_title="Lexical Entry Viewer",
    layout="wide"
)

# =========================
# Custom CSS for chips
# =========================
st.markdown("""
<style>
.chip-container {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
    margin-bottom: 6px;
}

.chip {
    display: inline-block;
    padding: 4px 10px;
    background-color: #f1f3f4;
    border-radius: 16px;
    font-size: 0.85rem;
    color: #202124;
    border: 1px solid #dadce0;
}

.section-box {
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 14px;
    background-color: #fafafa;
}

.section-title {
    font-weight: 600;
    font-size: 1.05rem;
    margin-bottom: 6px;
    color: #1f1f1f;
}

.meta-line {
    font-size: 0.9rem;
    margin-bottom: 4px;
}

.label {
    font-weight: 600;
    color: #444;
}
</style>
""", unsafe_allow_html=True)

# =========================
# Helper functions
# =========================

def render_chips(text):
    """
    Render semicolon- or comma-separated strings as chips.
    """
    if pd.isna(text) or str(text).strip() == "":
        return ""

    # split on ; or ,
    parts = [p.strip() for p in str(text).replace(",", ";").split(";") if p.strip()]

    if not parts:
        return ""

    chips_html = '<div class="chip-container">'
    for p in parts:
        chips_html += f'<div class="chip">{p}</div>'
    chips_html += '</div>'

    return chips_html


def safe_get(row, col):
    if col in row and pd.notna(row[col]):
        return str(row[col])
    return ""


# =========================
# Load data
# =========================
st.sidebar.title("Data source")

uploaded_file = st.sidebar.file_uploader("Upload Excel file", type=["xlsx", "xls"])

if not uploaded_file:
    st.info("⬅️ Upload your Excel file to start.")
    st.stop()

df = pd.read_excel(uploaded_file)

if df.empty:
    st.error("Excel file is empty.")
    st.stop()

# =========================
# Headword selector
# =========================
headwords = df["general_word"].dropna().unique().tolist()
headwords.sort()

selected_word = st.sidebar.selectbox("Select headword", headwords)

entry = df[df["general_word"] == selected_word].iloc[0]

# =========================
# GENERAL SECTION
# =========================
st.markdown(f"## {selected_word.upper()}")

general_box = f"""
<div class="section-box">
    <div class="section-title">General</div>
    <div class="meta-line"><span class="label">Corpus:</span> {safe_get(entry, 'general_corpus')}</div>
    <div class="meta-line"><span class="label">Frequency:</span> {safe_get(entry, 'general_frequency')} | <span class="label">PMW:</span> {safe_get(entry, 'general_pmw')}</div>
    <div class="meta-line"><span class="label">Zipf:</span> {safe_get(entry, 'general_zipf')} | <span class="label">Band:</span> {safe_get(entry, 'general_band')}</div>
</div>
"""
st.markdown(general_box, unsafe_allow_html=True)

# General bigram & trigram chips
gen_bigram = render_chips(safe_get(entry, "general_bigram"))
gen_trigram = render_chips(safe_get(entry, "general_trigram"))

if gen_bigram or gen_trigram:
    st.markdown("**N-grams (General)**")
    st.markdown(gen_bigram + gen_trigram, unsafe_allow_html=True)

# Dictionary & thesaurus links
col1, col2 = st.columns(2)
with col1:
    if safe_get(entry, "general_dictionary"):
        st.markdown(f"[Dictionary]({safe_get(entry, 'general_dictionary')})")
with col2:
    if safe_get(entry, "general_thesaurus"):
        st.markdown(f"[Thesaurus]({safe_get(entry, 'general_thesaurus')})")

# Related headwords & regex
if safe_get(entry, "general_related_headword"):
    st.markdown(f"**Related headwords:** {safe_get(entry, 'general_related_headword')}")

if safe_get(entry, "general_related_regex"):
    st.markdown(f"**Related patterns (regex):** {safe_get(entry, 'general_related_regex')}")

st.markdown("---")

# =========================
# SENSE SECTIONS
# =========================
MAX_SENSES = 10  # safety upper bound

for i in range(1, MAX_SENSES + 1):
    prefix = f"sense{i}_headword"
    if prefix not in entry or pd.isna(entry[prefix]):
        continue

    sense_headword = safe_get(entry, f"sense{i}_headword")
    sense_pos = safe_get(entry, f"sense{i}_pos")
    sense_freq = safe_get(entry, f"sense{i}_frequency")
    sense_pmw = safe_get(entry, f"sense{i}_pmw")
    sense_zipf = safe_get(entry, f"sense{i}_zipf")
    sense_band = safe_get(entry, f"sense{i}_band")
    sense_def = safe_get(entry, f"sense{i}_definition")
    sense_coll = safe_get(entry, f"sense{i}_typical_collocates")
    sense_ex = safe_get(entry, f"sense{i}_example")
    sense_domain = safe_get(entry, f"sense{i}_domain")
    sense_register = safe_get(entry, f"sense{i}_register")
    sense_year = safe_get(entry, f"sense{i}_year")

    sense_box = f"""
    <div class="section-box">
        <div class="section-title">Sense {i}: {sense_headword} ({sense_pos})</div>
        <div class="meta-line"><span class="label">Frequency:</span> {sense_freq} | <span class="label">PMW:</span> {sense_pmw}</div>
        <div class="meta-line"><span class="label">Zipf:</span> {sense_zipf} | <span class="label">Band:</span> {sense_band}</div>
        <div class="meta-line"><span class="label">Domain:</span> {sense_domain} | <span class="label">Register:</span> {sense_register}</div>
        <div class="meta-line"><span class="label">Year(s):</span> {sense_year}</div>
        <div class="meta-line"><span class="label">Definition:</span> {sense_def}</div>
    </div>
    """
    st.markdown(sense_box, unsafe_allow_html=True)

    # Sense bigram & trigram chips
    sense_bigram = render_chips(safe_get(entry, f"sense{i}_bigram"))
    sense_trigram = render_chips(safe_get(entry, f"sense{i}_trigram"))

    if sense_bigram or sense_trigram:
        st.markdown(f"**N-grams (Sense {i})**")
        st.markdown(sense_bigram + sense_trigram, unsafe_allow_html=True)

    if sense_coll:
        st.markdown(f"**Typical collocates:** {sense_coll}")

    if sense_ex:
        st.markdown(f"**Example:** {sense_ex}")

    st.markdown("---")
