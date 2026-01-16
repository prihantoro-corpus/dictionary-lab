import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Corpus Dictionary", page_icon="📘", layout="wide")

# =========================
# Cambridge-like Dark CSS
# =========================
st.markdown("""
<style>
html, body, [class*="css"]  {
    background-color: #0f1115;
    color: #e6e6e6;
}

/* Headword */
.headword {
    font-size: 44px;
    font-weight: 800;
    color: #ffd200;
    margin-bottom: 0px;
}

/* Phonetic + CEFR */
.phonetic {
    color: #9aa0a6;
    font-size: 18px;
    margin-bottom: 10px;
}

/* Meta line */
.meta {
    color: #cfcfcf;
    font-size: 15px;
    margin-bottom: 8px;
}

/* POS tag */
.pos {
    color: #00e676;
    font-weight: 600;
}

/* Definition */
.definition {
    font-size: 20px;
    margin-top: 10px;
    color: #ffffff;
}

/* Sense number */
.sense-number {
    color: #ffd200;
    font-weight: 700;
    margin-right: 6px;
}

/* Collocates */
.collocates {
    color: #64b5f6;
    margin-top: 6px;
}

/* Example */
.example {
    font-style: italic;
    color: #e0e0e0;
}

/* Box sections (ngrams, collocates, etc) */
.box {
    background: #1a1d23;
    padding: 12px;
    border-radius: 8px;
    margin-top: 10px;
}

/* Tabs */
.stTabs [data-baseweb="tab"] {
    background-color: #1a1d23;
    color: #cfcfcf;
    border-radius: 6px 6px 0 0;
    padding: 8px 16px;
}

.stTabs [aria-selected="true"] {
    background-color: #ffd200 !important;
    color: #000000 !important;
    font-weight: 700;
}

/* Expander */
.streamlit-expanderHeader {
    background-color: #1a1d23;
    color: #ffd200;
    font-weight: 600;
}

/* Links */
a {
    color: #4fc3f7;
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
}
</style>
""", unsafe_allow_html=True)

st.title("")

# =========================
# Helpers
# =========================

def safe(val):
    if pd.isna(val):
        return ""
    return str(val)

def load_excels(files):
    dfs = []
    for f in files:
        df = pd.read_excel(f)
        df.columns = df.columns.str.strip()
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def get_sense(row, prefix):
    return {
        "headword": safe(row.get(f"{prefix}_headword")),
        "pos": safe(row.get(f"{prefix}_pos")),
        "definition": safe(row.get(f"{prefix}_definition")),
        "collocates": safe(row.get(f"{prefix}_typical_collocates")),
        "example": safe(row.get(f"{prefix}_example")),
        "domain": safe(row.get(f"{prefix}_domain")),
        "register": safe(row.get(f"{prefix}_register")),
        "year": safe(row.get(f"{prefix}_year")),
        "frequency": safe(row.get(f"{prefix}_frequency")),
        "pmw": safe(row.get(f"{prefix}_pmw")),
        "zipf": safe(row.get(f"{prefix}_zipf")),
        "band": safe(row.get(f"{prefix}_band")),
    }

def plot_freq(sense_label, sense):
    values, labels = [], []

    if sense["frequency"]:
        values.append(float(sense["frequency"]))
        labels.append("Freq")
    if sense["pmw"]:
        values.append(float(sense["pmw"]))
        labels.append("PMW")
    if sense["zipf"]:
        values.append(float(sense["zipf"]))
        labels.append("Zipf")

    if not values:
        st.info("No frequency data available.")
        return

    fig, ax = plt.subplots()
    ax.bar(labels, values)
    ax.set_title(f"{sense_label} Frequency Profile")
    ax.set_facecolor("#1a1d23")
    fig.patch.set_facecolor("#1a1d23")
    ax.tick_params(colors="white")
    ax.title.set_color("white")
    ax.yaxis.label.set_color("white")

    st.pyplot(fig)

# =========================
# Upload
# =========================

uploaded = st.file_uploader("Upload Excel file(s)", type=["xlsx", "xls"], accept_multiple_files=True)

if not uploaded:
    st.info("Upload your dictionary Excel file(s) to begin.")
    st.stop()

df = load_excels(uploaded)

# =========================
# Sidebar Search
# =========================

st.sidebar.header("🔍 Search")

headwords = sorted(set(
    df["sense1_headword"].dropna().astype(str).tolist() +
    df["sense2_headword"].dropna().astype(str).tolist() +
    df["sense3_headword"].dropna().astype(str).tolist()
))

selected = st.sidebar.selectbox("Headword", [""] + headwords)
query = st.sidebar.text_input("Contains")

filtered = df.copy()

if selected:
    filtered = filtered[
        (filtered["sense1_headword"] == selected) |
        (filtered["sense2_headword"] == selected) |
        (filtered["sense3_headword"] == selected)
    ]

if query:
    filtered = filtered[
        filtered.apply(lambda r: r.astype(str).str.contains(query, case=False, na=False).any(), axis=1)
    ]

# =========================
# Render Entries
# =========================

for _, row in filtered.iterrows():

    main_hw = safe(row.get("sense1_headword")) or safe(row.get("sense2_headword")) or safe(row.get("sense3_headword"))

    phonetic = "/bæŋk/"  # placeholder – later you can add column
    cefr = f"(CEFR: A2)"  # placeholder – later from column

    general_band = safe(row.get("general_band"))
    general_dict = safe(row.get("general_dictionary"))
    general_thes = safe(row.get("general_thesaurus"))

    st.markdown(f'<div class="headword">{main_hw}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="phonetic">{phonetic} {cefr}</div>', unsafe_allow_html=True)

    meta_parts = []
    if general_band:
        meta_parts.append(f"Band: {general_band}")
    if general_dict:
        meta_parts.append(f'<a href="{general_dict}" target="_blank">Cambridge</a>')
    if general_thes:
        meta_parts.append(f'<a href="{general_thes}" target="_blank">Collins Thesaurus</a>')

    if meta_parts:
        st.markdown(f'<div class="meta">{" · ".join(meta_parts)}</div>', unsafe_allow_html=True)

    # Collect senses
    senses = []
    for i in [1, 2, 3]:
        s = get_sense(row, f"sense{i}")
        if s["headword"]:
            senses.append((i, s))

    tabs = st.tabs([f"{i}" for i, _ in senses])

    for tab, (i, sense) in zip(tabs, senses):
        with tab:
            st.markdown(
                f'<span class="sense-number">{i}</span>'
                f'<span class="pos">[{sense["pos"]}]</span> '
                f'<span class="definition">{sense["definition"]}</span>',
                unsafe_allow_html=True
            )

            meta_line = []
            if sense["domain"]:
                meta_line.append(f"Domain: {sense['domain']}")
            if sense["register"]:
                meta_line.append(f"Register: {sense['register']}")
            if sense["year"]:
                meta_line.append(f"Year(s): {sense['year']}")

            if meta_line:
                st.markdown(f'<div class="meta">{" · ".join(meta_line)}</div>', unsafe_allow_html=True)

            if sense["collocates"]:
                st.markdown(
                    f'<div class="box"><b>Top collocates:</b> {sense["collocates"]}</div>',
                    unsafe_allow_html=True
                )

            if sense["example"]:
                with st.expander("Show example"):
                    st.markdown(f'<div class="example">{sense["example"]}</div>', unsafe_allow_html=True)

            st.markdown("#### Frequency")
            plot_freq(f"Sense {i}", sense)

    st.markdown("<hr style='border:1px solid #333'>", unsafe_allow_html=True)
