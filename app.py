import streamlit as st
import pandas as pd
from glob import glob

st.set_page_config(layout="wide")

# =========================
# STYLING – Cambridge / Oxford Inspired
# =========================
st.markdown("""
<style>
body, .stApp {
    background-color: #0b0b0b;
    color: #ffffff;
    font-family: "Segoe UI", Arial, sans-serif;
}

h1 { font-size: 42px; margin-bottom: 4px; }
h2 { font-size: 28px; margin-bottom: 4px; }
h3 { font-size: 22px; margin-bottom: 4px; }

.block {
    background-color: #141414;
    padding: 20px 24px 22px 24px;
    border-radius: 12px;
    margin-bottom: 22px;
    box-shadow: 0 0 0 1px #1f1f1f;
}

.meta-line {
    color: #cfcfcf;
    font-size: 14px;
    margin-bottom: 6px;
}

.badge {
    display: inline-block;
    padding: 4px 10px;
    margin-right: 6px;
    margin-top: 4px;
    border-radius: 14px;
    background-color: #2b2b2b;
    color: #ffffff;
    font-size: 12px;
    font-weight: 500;
}

.badge-cefr { background-color: #2d6cdf; }
.badge-ngsl { background-color: #2f8f2f; }
.badge-academic { background-color: #8b5cf6; }

.chip {
    display: inline-block;
    padding: 5px 12px;
    margin: 4px 6px 4px 0;
    border-radius: 16px;
    background-color: #1f3a5f;
    color: #ffffff;
    font-size: 13px;
}

.section-label {
    font-size: 15px;
    font-weight: 600;
    color: #e6e6e6;
    margin-top: 14px;
    margin-bottom: 6px;
}

.zipf-bar {
    height: 8px;
    background-color: #f4c430;
    border-radius: 4px;
    margin: 6px 0 10px 0;
}

a { color: #5da9ff; text-decoration: none; }
a:hover { text-decoration: underline; }

.sense-header {
    font-size: 20px;
    font-weight: 600;
    margin-bottom: 4px;
}

.sense-meta {
    color: #cfcfcf;
    font-size: 14px;
    margin-bottom: 8px;
}

.example {
    color: #f1f1f1;
    font-style: italic;
    margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# HELPERS
# =========================
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

def render_wordlist_badges(wordlist_text):
    if not wordlist_text:
        return ""
    badges_html = ""
    parts = [p.strip() for p in wordlist_text.split(";") if p.strip()]
    for p in parts:
        lower = p.lower()
        cls = "badge"
        if "cefr" in lower:
            cls = "badge badge-cefr"
        elif "ngsl" in lower:
            cls = "badge badge-ngsl"
        elif "academic" in lower:
            cls = "badge badge-academic"
        badges_html += f"<span class='{cls}'>{p}</span>"
    return badges_html

# =========================
# LOAD ALL EXCEL FILES (GitHub-safe)
# =========================
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

st.title("Corpus-Based Dictionary")

if df.empty:
    st.error("No Excel files found in the project folder.")
    st.stop()

# =========================
# SEARCH
# =========================
query = st.text_input("Search headword", placeholder="e.g. bank, run, saw")

if not query:
    st.stop()

row = df[df["general_word"].str.lower() == query.lower()]

if row.empty:
    st.warning("Word not found.")
    st.stop()

row = row.iloc[0]

# =========================
# GENERAL BLOCK
# =========================
st.markdown("<div class='block'>", unsafe_allow_html=True)

st.markdown(f"<h1>{safe(row.get('general_word')).upper()}</h1>", unsafe_allow_html=True)

# ---- BADGES (CEFR / NGSL / Academic) ----
badges_html = render_wordlist_badges(safe(row.get("general_wordlist")))
if badges_html:
    st.markdown(badges_html, unsafe_allow_html=True)

st.markdown(f"<div class='meta-line'><b>Corpus:</b> {safe(row.get('general_corpus'))}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='meta-line'><b>Frequency:</b> {safe(row.get('general_frequency'))} | <b>PMW:</b> {safe(row.get('general_pmw'))}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='meta-line'><b>Zipf:</b> {safe(row.get('general_zipf'))} | <b>Band:</b> {safe(row.get('general_band'))}</div>", unsafe_allow_html=True)

st.markdown(zipf_bar(row.get("general_zipf")), unsafe_allow_html=True)

# ---- GENERAL N-GRAMS ----
general_bigram = safe(row.get("general_bigram"))
general_trigram = safe(row.get("general_trigram"))

if general_bigram or general_trigram:
    st.markdown("<div class='section-label'>N-grams</div>", unsafe_allow_html=True)
    st.markdown(render_chips(general_bigram + ";" + general_trigram), unsafe_allow_html=True)

# ---- LINKS ----
if safe(row.get("general_dictionary")):
    st.markdown(f"[Dictionary]({safe(row.get('general_dictionary'))})")
if safe(row.get("general_thesaurus")):
    st.markdown(f"[Thesaurus]({safe(row.get('general_thesaurus'))})")

# ---- RELATED ----
if safe(row.get("general_related_headword")):
    st.markdown(f"<div class='section-label'>Related headwords</div>{safe(row.get('general_related_headword'))}", unsafe_allow_html=True)
if safe(row.get("general_related_regex")):
    st.markdown(f"<div class='section-label'>Related patterns (regex)</div>{safe(row.get('general_related_regex'))}", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# =========================
# SENSES – TABBED LAYOUT
# =========================
sense_tabs = []
sense_indices = []

for i in range(1, 10):
    if safe(row.get(f"sense{i}_headword")):
        sense_tabs.append(f"Sense {i}")
        sense_indices.append(i)

if sense_tabs:
    tabs = st.tabs(sense_tabs)

    for tab, i in zip(tabs, sense_indices):
        with tab:
            st.markdown("<div class='block'>", unsafe_allow_html=True)

            head = safe(row.get(f"sense{i}_headword"))
            pos = safe(row.get(f"sense{i}_pos"))

            st.markdown(f"<div class='sense-header'>{head} ({pos})</div>", unsafe_allow_html=True)

            st.markdown(
                f"<div class='sense-meta'><b>Frequency:</b> {safe(row.get(f'sense{i}_frequency'))} | "
                f"<b>PMW:</b> {safe(row.get(f'sense{i}_pmw'))} | "
                f"<b>Zipf:</b> {safe(row.get(f'sense{i}_zipf'))} | "
                f"<b>Band:</b> {safe(row.get(f'sense{i}_band'))}</div>",
                unsafe_allow_html=True
            )

            st.markdown(zipf_bar(row.get(f"sense{i}_zipf")), unsafe_allow_html=True)

            st.markdown(
                f"<div class='sense-meta'><b>Domain:</b> {safe(row.get(f'sense{i}_domain'))} | "
                f"<b>Register:</b> {safe(row.get(f'sense{i}_register'))} | "
                f"<b>Year(s):</b> {safe(row.get(f'sense{i}_year'))}</div>",
                unsafe_allow_html=True
            )

            # ---- SENSE N-GRAMS ----
            sense_bigram = safe(row.get(f"sense{i}_bigram"))
            sense_trigram = safe(row.get(f"sense{i}_trigram"))

            if sense_bigram or sense_trigram:
                st.markdown("<div class='section-label'>N-grams</div>", unsafe_allow_html=True)
                st.markdown(render_chips(sense_bigram + ";" + sense_trigram), unsafe_allow_html=True)

            # ---- DEFINITION ----
            st.markdown(f"<div class='section-label'>Definition</div>{safe(row.get(f'sense{i}_definition'))}", unsafe_allow_html=True)

            # ---- COLLOCATES ----
            if safe(row.get(f'sense{i}_typical_collocates')):
                st.markdown(f"<div class='section-label'>Typical collocates</div>{safe(row.get(f'sense{i}_typical_collocates'))}", unsafe_allow_html=True)

            # ---- EXAMPLE ----
            if safe(row.get(f'sense{i}_example')):
                st.markdown(f"<div class='section-label'>Example</div><div class='example'>{safe(row.get(f'sense{i}_example'))}</div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
