import streamlit as st
import pandas as pd

st.set_page_config(page_title="Lexical Entry Viewer", layout="wide")

# =========================
# CSS – dark, visible
# =========================
st.markdown("""
<style>
body { background-color: #0f172a; color: #e5e7eb; }

.section-box {
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 16px;
    background-color: #020617;
}

.section-title {
    font-weight: 700;
    font-size: 1.1rem;
    margin-bottom: 8px;
    color: #f8fafc;
}

.meta-line { font-size: 0.95rem; margin-bottom: 4px; color: #e5e7eb; }

.label { font-weight: 600; color: #38bdf8; }

.chip-container {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 6px;
    margin-bottom: 10px;
}

.chip {
    padding: 5px 12px;
    background-color: #1e293b;
    border-radius: 999px;
    font-size: 0.85rem;
    color: #f8fafc;
    border: 1px solid #38bdf8;
    white-space: nowrap;
}
</style>
""", unsafe_allow_html=True)

# =========================
# Helpers
# =========================
def safe(row, col):
    col = col.strip()
    if col in row.index and pd.notna(row[col]):
        return str(row[col]).strip()
    return ""

def render_chips(text):
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\\", " ")
    parts = [p.strip() for p in text.replace(",", ";").split(";") if p.strip()]
    if not parts:
        return ""
    html = '<div class="chip-container">'
    for p in parts:
        html += f'<div class="chip">{p}</div>'
    html += '</div>'
    return html

# =========================
# Load Excel
# =========================
st.sidebar.title("Data")
uploaded = st.sidebar.file_uploader("Upload your Excel", type=["xlsx"])

if not uploaded:
    st.info("⬅️ Upload your Excel file")
    st.stop()

df = pd.read_excel(uploaded)

# 🔴 CRITICAL FIX: normalize column names
df.columns = [c.strip().replace("\n", "").replace("\r", "") for c in df.columns]

# Debug (can comment later)
# st.sidebar.write("Detected columns:", df.columns.tolist())

# =========================
# Headword selector
# =========================
if "general_word" not in df.columns:
    st.error("Column 'general_word' not found. Check your Excel header.")
    st.stop()

words = sorted(df["general_word"].dropna().unique())
word = st.sidebar.selectbox("Select headword", words)

row = df[df["general_word"] == word].iloc[0]

# =========================
# GENERAL
# =========================
st.markdown(f"## {word.upper()}")

general_html = f"""
<div class="section-box">
  <div class="section-title">General</div>
  <div class="meta-line"><span class="label">Corpus:</span> {safe(row,'general_corpus')}</div>
  <div class="meta-line"><span class="label">Frequency:</span> {safe(row,'general_frequency')} | <span class="label">PMW:</span> {safe(row,'general_pmw')}</div>
  <div class="meta-line"><span class="label">Zipf:</span> {safe(row,'general_zipf')} | <span class="label">Band:</span> {safe(row,'general_band')}</div>
</div>
"""
st.markdown(general_html, unsafe_allow_html=True)

# ===== GENERAL N-GRAMS (PLACED HERE, as you requested)
gen_bigram = safe(row, "general_bigram")
gen_trigram = safe(row, "general_trigram")

if gen_bigram or gen_trigram:
    st.markdown("**N-grams**")
    st.markdown(render_chips(gen_bigram) + render_chips(gen_trigram), unsafe_allow_html=True)

# ===== Links
c1, c2 = st.columns(2)
with c1:
    if safe(row, "general_dictionary"):
        st.markdown(f"[Dictionary]({safe(row,'general_dictionary')})")
with c2:
    if safe(row, "general_thesaurus"):
        st.markdown(f"[Thesaurus]({safe(row,'general_thesaurus')})")

# ===== Related
if safe(row, "general_related_headword"):
    st.markdown(f"**Related headwords:** {safe(row,'general_related_headword')}")

if safe(row, "general_related_regex"):
    st.markdown(f"**Related patterns (regex):** {safe(row,'general_related_regex')}")

st.markdown("---")

# =========================
# SENSES
# =========================
for i in range(1, 6):
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

    # ===== SENSE N-GRAMS (PLACED HERE, before collocates)
    s_bigram = safe(row, f"sense{i}_bigram")
    s_trigram = safe(row, f"sense{i}_trigram")

    if s_bigram or s_trigram:
        st.markdown("**N-grams**")
        st.markdown(render_chips(s_bigram) + render_chips(s_trigram), unsafe_allow_html=True)

    if safe(row, f"sense{i}_typical_collocates"):
        st.markdown(f"**Typical collocates:** {safe(row,f'sense{i}_typical_collocates')}")

    if safe(row, f"sense{i}_example"):
        st.markdown(f"**Example:** {safe(row,f'sense{i}_example')}")

    st.markdown("---")
