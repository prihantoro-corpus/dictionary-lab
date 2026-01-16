import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Corpus Dictionary Viewer",
    page_icon="📘",
    layout="wide"
)

st.title("📘 Corpus-Based Dictionary Viewer")
st.markdown("Upload one or more Excel files and browse them in a dictionary-style view.")

# -----------------------------
# Helper functions
# -----------------------------

def load_excels(uploaded_files):
    dfs = []
    for file in uploaded_files:
        df = pd.read_excel(file)
        df.columns = df.columns.str.strip()
        dfs.append(df)
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

def safe(val):
    """Return empty string if NaN, else string."""
    if pd.isna(val):
        return ""
    return str(val)

def render_sense(row, sense_prefix):
    headword = safe(row.get(f"{sense_prefix}_headword"))
    if not headword:
        return  # no such sense, skip

    pos = safe(row.get(f"{sense_prefix}_pos"))
    definition = safe(row.get(f"{sense_prefix}_definition"))
    collocates = safe(row.get(f"{sense_prefix}_typical_collocates"))
    example = safe(row.get(f"{sense_prefix}_example"))
    domain = safe(row.get(f"{sense_prefix}_domain"))
    register = safe(row.get(f"{sense_prefix}_register"))
    year = safe(row.get(f"{sense_prefix}_year"))
    freq = safe(row.get(f"{sense_prefix}_frequency"))
    pmw = safe(row.get(f"{sense_prefix}_pmw"))
    zipf = safe(row.get(f"{sense_prefix}_zipf"))
    band = safe(row.get(f"{sense_prefix}_band"))

    st.markdown(f"**{headword}** *{pos}*")
    if definition:
        st.markdown(f"> {definition}")

    meta_parts = []
    if domain:
        meta_parts.append(f"**Domain:** {domain}")
    if register:
        meta_parts.append(f"**Register:** {register}")
    if year:
        meta_parts.append(f"**Year(s):** {year}")

    if meta_parts:
        st.markdown(" · ".join(meta_parts))

    if collocates:
        st.markdown(f"**Typical collocates:** {collocates}")

    if example:
        st.markdown(f"_Example:_ {example}")

    freq_parts = []
    if freq:
        freq_parts.append(f"Freq: {freq}")
    if pmw:
        freq_parts.append(f"PMW: {pmw}")
    if zipf:
        freq_parts.append(f"Zipf: {zipf}")
    if band:
        freq_parts.append(f"Band: {band}")

    if freq_parts:
        st.markdown(" | ".join(freq_parts))

    st.markdown("---")


# -----------------------------
# Upload section
# -----------------------------

uploaded_files = st.file_uploader(
    "Upload Excel file(s)",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Please upload one or more Excel files to begin.")
    st.stop()

df = load_excels(uploaded_files)

if df.empty:
    st.warning("No data found in uploaded files.")
    st.stop()

# -----------------------------
# Sidebar filters
# -----------------------------

st.sidebar.header("🔍 Filters")

headwords = sorted(
    set(
        df["sense1_headword"].dropna().astype(str).tolist() +
        df["sense2_headword"].dropna().astype(str).tolist() +
        df["sense3_headword"].dropna().astype(str).tolist()
    )
)

selected_headword = st.sidebar.selectbox("Select headword", [""] + headwords)

search_query = st.sidebar.text_input("Search (contains)")

# -----------------------------
# Main display
# -----------------------------

filtered_df = df.copy()

if selected_headword:
    mask = (
        (filtered_df["sense1_headword"] == selected_headword) |
        (filtered_df["sense2_headword"] == selected_headword) |
        (filtered_df["sense3_headword"] == selected_headword)
    )
    filtered_df = filtered_df[mask]

if search_query:
    filtered_df = filtered_df[
        filtered_df.apply(
            lambda row: row.astype(str).str.contains(search_query, case=False, na=False).any(),
            axis=1
        )
    ]

st.markdown(f"### Showing {len(filtered_df)} entry(ies)")

# -----------------------------
# Dictionary-style rendering
# -----------------------------

for idx, row in filtered_df.iterrows():
    general_band = safe(row.get("general_band"))
    general_dict = safe(row.get("general_dictionary"))
    general_thes = safe(row.get("general_thesaurus"))
    related_hw = safe(row.get("general_related_headword"))
    related_rx = safe(row.get("general_related_regex"))

    st.markdown("## " + (safe(row.get("sense1_headword")) or safe(row.get("sense2_headword")) or safe(row.get("sense3_headword"))))

    meta = []
    if general_band:
        meta.append(f"**Band:** {general_band}")
    if general_dict:
        meta.append(f"[Dictionary]({general_dict})")
    if general_thes:
        meta.append(f"[Thesaurus]({general_thes})")

    if meta:
        st.markdown(" · ".join(meta))

    if related_hw:
        st.markdown(f"**Related headwords:** {related_hw}")
    if related_rx:
        st.markdown(f"**Related regex:** {related_rx}")

    st.markdown("---")

    # Render senses
    render_sense(row, "sense1")
    render_sense(row, "sense2")
    render_sense(row, "sense3")

    st.markdown("----")
