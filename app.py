import streamlit as st
import pandas as pd
from glob import glob
import re

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

.band-badge {
    display: inline-block;
    padding: 4px 10px;
    margin-right: 6px;
    border-radius: 14px;
    background-color: #f4c430;
    color: #000000;
    font-size: 12px;
    font-weight: 600;
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

.section-label {
    font-size: 15px;
    font-weight: 600;
    color: #e6e6e6;
    margin-top: 14px;
    margin-bottom: 6px;
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

.pron {
    font-size: 18px;
    color: #b6e3ff;
    margin-bottom: 6px;
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
# LOAD ALL EXCEL FILES
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
# STATISTICS LANDING PAGE (SERIOUS LEXICOGRAPHIC STATS)
# =========================
st.markdown("<div class='block'>", unsafe_allow_html=True)
st.markdown("<h2>Dictionary Overview</h2>", unsafe_allow_html=True)

stats_rows = []

# Number of entries
num_entries = df["general_word"].nunique()
stats_rows.append({"Metric": "Number of entries (headwords)", "Value": num_entries})

# Number of senses
sense_cols = [c for c in df.columns if re.match(r"sense\d+_headword", c)]
num_senses = sum(df[c].notna().sum() for c in sense_cols)
stats_rows.append({"Metric": "Number of senses (total)", "Value": num_senses})

# POS inventory
pos_cols = [c for c in df.columns if re.match(r"sense\d+_pos", c)]
pos_values = []
for c in pos_cols:
    pos_values.extend(df[c].dropna().astype(str).tolist())

unique_pos = sorted(set(p.strip() for p in pos_values if p.strip()))
stats_rows.append({"Metric": "Number of POS categories", "Value": len(unique_pos)})
stats_rows.append({"Metric": "POS tags", "Value": ", ".join(unique_pos)})

# Domain inventory
domain_cols = [c for c in df.columns if re.match(r"sense\d+_domain", c)]
domain_values = []
for c in domain_cols:
    domain_values.extend(df[c].dropna().astype(str).tolist())
unique_domains = sorted(set(d.strip() for d in domain_values if d.strip()))
stats_rows.append({"Metric": "Domains", "Value": ", ".join(unique_domains)})
stats_rows.append({"Metric": "Number of domains", "Value": len(unique_domains)})

# Register inventory
register_cols = [c for c in df.columns if re.match(r"sense\d+_register", c)]
register_values = []
for c in register_cols:
    register_values.extend(df[c].dropna().astype(str).tolist())
unique_registers = sorted(set(r.strip() for r in register_values if r.strip()))
stats_rows.append({"Metric": "Registers", "Value": ", ".join(unique_registers)})
stats_rows.append({"Metric": "Number of registers", "Value": len(unique_registers)})

# Frequency bands
band_cols = [c for c in df.columns if c.endswith("_band")]
band_values = []
for c in band_cols:
    band_values.extend(df[c].dropna().astype(str).tolist())
unique_bands = sorted(set(band_values))
stats_rows.append({"Metric": "Frequency bands used", "Value": ", ".join(unique_bands)})
stats_rows.append({"Metric": "Number of frequency bands", "Value": len(unique_bands)})

# Pronunciation coverage
if "general_pronunciation" in df.columns:
    pron_general_count = df["general_pronunciation"].notna().sum()
    stats_rows.append({"Metric": "Entries with general pronunciation", "Value": pron_general_count})

sense_pron_cols = [c for c in df.columns if re.match(r"sense\d+_pronunciation", c)]
sense_pron_count = sum(df[c].notna().sum() for c in sense_pron_cols)
stats_rows.append({"Metric": "Senses with pronunciation", "Value": sense_pron_count})

# N-gram coverage
ngram_cols = [c for c in df.columns if c.endswith("_bigram") or c.endswith("_trigram")]
ngram_count = sum(df[c].notna().sum() for c in ngram_cols)
stats_rows.append({"Metric": "Entries/Senses with n-grams", "Value": ngram_count})

# Collocate coverage
collocate_cols = [c for c in df.columns if c.endswith("_typical_collocates")]
collocate_count = sum(df[c].notna().sum() for c in collocate_cols)
stats_rows.append({"Metric": "Senses with collocate data", "Value": collocate_count})

# Example coverage
example_cols = [c for c in df.columns if c.endswith("_example")]
example_count = sum(df[c].notna().sum() for c in example_cols)
stats_rows.append({"Metric": "Senses with example sentences", "Value": example_count})

stats_df = pd.DataFrame(stats_rows)

st.dataframe(stats_df, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

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

# Pronunciation
if safe(row.get("general_pronunciation")):
    st.markdown(f"<div class='pron'>/{safe(row.get('general_pronunciation'))}/</div>", unsafe_allow_html=True)

# Wordlist badges
badges_html = render_wordlist_badges(safe(row.get("general_wordlist")))
if badges_html:
    st.markdown(badges_html, unsafe_allow_html=True)

st.markdown(f"<div class='meta-line'><b>Corpus:</b> {safe(row.get('general_corpus'))}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='meta-line'><b>Frequency:</b> {safe(row.get('general_frequency'))} | <b>PMW:</b> {safe(row.get('general_pmw'))}</div>", unsafe_allow_html=True)

if safe(row.get("general_band")):
    st.markdown(f"<span class='band-badge'>Band {safe(row.get('general_band'))}</span>", unsafe_allow_html=True)

# N-grams
general_bigram = safe(row.get("general_bigram"))
general_trigram = safe(row.get("general_trigram"))
if general_bigram or general_trigram:
    st.markdown("<div class='section-label'>N-grams</div>", unsafe_allow_html=True)
    st.markdown(render_chips(general_bigram + ";" + general_trigram), unsafe_allow_html=True)

# Links
if safe(row.get("general_dictionary")):
    st.markdown(f"[Dictionary]({safe(row.get('general_dictionary'))})")
if safe(row.get("general_thesaurus")):
    st.markdown(f"[Thesaurus]({safe(row.get('general_thesaurus'))})")

# Related
if safe(row.get("general_related_headword")):
    st.markdown(f"<div class='section-label'>Related headwords</div>{safe(row.get('general_related_headword'))}", unsafe_allow_html=True)
if safe(row.get("general_related_regex")):
    st.markdown(f"<div class='section-label'>Related patterns (regex)</div>{safe(row.get('general_related_regex'))}", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# =========================
# SENSES
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

            if safe(row.get(f"sense{i}_pronunciation")):
                st.markdown(f"<div class='pron'>/{safe(row.get(f'sense{i}_pronunciation'))}/</div>", unsafe_allow_html=True)

            st.markdown(
                f"<div class='sense-meta'><b>Frequency:</b> {safe(row.get(f'sense{i}_frequency'))} | "
                f"<b>PMW:</b> {safe(row.get(f'sense{i}_pmw'))}</div>",
                unsafe_allow_html=True
            )

            if safe(row.get(f"sense{i}_band")):
                st.markdown(f"<span class='band-badge'>Band {safe(row.get(f'sense{i}_band'))}</span>", unsafe_allow_html=True)

            st.markdown(
                f"<div class='sense-meta'><b>Domain:</b> {safe(row.get(f'sense{i}_domain'))} | "
                f"<b>Register:</b> {safe(row.get(f'sense{i}_register'))} | "
                f"<b>Year(s):</b> {safe(row.get(f'sense{i}_year'))}</div>",
                unsafe_allow_html=True
            )

            sense_bigram = safe(row.get(f"sense{i}_bigram"))
            sense_trigram = safe(row.get(f"sense{i}_trigram"))
            if sense_bigram or sense_trigram:
                st.markdown("<div class='section-label'>N-grams</div>", unsafe_allow_html=True)
                st.markdown(render_chips(sense_bigram + ";" + sense_trigram), unsafe_allow_html=True)

            st.markdown(f"<div class='section-label'>Definition</div>{safe(row.get(f'sense{i}_definition'))}", unsafe_allow_html=True)

            if safe(row.get(f'sense{i}_typical_collocates')):
                st.markdown(f"<div class='section-label'>Typical collocates</div>{safe(row.get(f'sense{i}_typical_collocates'))}", unsafe_allow_html=True)

            if safe(row.get(f'sense{i}_example')):
                st.markdown(f"<div class='section-label'>Example</div><div class='example'>{safe(row.get(f'sense{i}_example'))}</div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
