import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Corpus Dictionary",
    page_icon="📘",
    layout="wide"
)

# -----------------------------
# CSS (Cambridge-like style)
# -----------------------------
st.markdown("""
<style>
/* Main headword */
.headword {
    font-size: 42px;
    font-weight: 700;
    margin-bottom: 0;
    color: #1f1f1f;
}

/* POS */
.pos {
    font-size: 18px;
    color: #555;
    margin-left: 10px;
}

/* Definition */
.definition {
    font-size: 20px;
    margin-top: 10px;
}

/* Meta line */
.meta {
    color: #666;
    font-size: 14px;
    margin-bottom: 10px;
}

/* Collocates */
.collocates {
    color: #0b5394;
    font-size: 15px;
    margin-top: 6px;
}

/* Example */
.example {
    font-style: italic;
    color: #333;
}

/* Section separator */
hr {
    margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)

st.title("📘 Corpus-Based Dictionary")

# -----------------------------
# Helpers
# -----------------------------

def safe(val):
    if pd.isna(val):
        return ""
    return str(val)

def load_excels(uploaded_files):
    dfs = []
    for file in uploaded_files:
        df = pd.read_excel(file)
        df.columns = df.columns.str.strip()
        dfs.append(df)
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

def get_sense_data(row, sense_prefix):
    return {
        "headword": safe(row.get(f"{sense_prefix}_headword")),
        "pos": safe(row.get(f"{sense_prefix}_pos")),
        "definition": safe(row.get(f"{sense_prefix}_definition")),
        "collocates": safe(row.get(f"{sense_prefix}_typical_collocates")),
        "example": safe(row.get(f"{sense_prefix}_example")),
        "domain": safe(row.get(f"{sense_prefix}_domain")),
        "register": safe(row.get(f"{sense_prefix}_register")),
        "year": safe(row.get(f"{sense_prefix}_year")),
        "frequency": safe(row.get(f"{sense_prefix}_frequency")),
        "pmw": safe(row.get(f"{sense_prefix}_pmw")),
        "zipf": safe(row.get(f"{sense_prefix}_zipf")),
        "band": safe(row.get(f"{sense_prefix}_band")),
    }

def plot_frequency_chart(sense_label, sense_data):
    values = []
    labels = []

    if sense_data["frequency"]:
        values.append(float(sense_data["frequency"]))
        labels.append("Frequency")
    if sense_data["pmw"]:
        values.append(float(sense_data["pmw"]))
        labels.append("PMW")
    if sense_data["zipf"]:
        values.append(float(sense_data["zipf"]))
        labels.append("Zipf")

    if not values:
        st.info("No frequency data available.")
        return

    fig, ax = plt.subplots()
    ax.bar(labels, values)
    ax.set_title(f"{sense_label} – Frequency Profile")
    ax.set_ylabel("Value")

    st.pyplot(fig)

# -----------------------------
# Upload
# -----------------------------

uploaded_files = st.file_uploader(
    "Upload Excel file(s)",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Please upload one or more Excel files.")
    st.stop()

df = load_excels(uploaded_files)

if df.empty:
    st.warning("No data found.")
    st.stop()

# -----------------------------
# Sidebar search
# -----------------------------

st.sidebar.header("🔍 Search")

headwords = sorted(
    set(
        df["sense1_headword"].dropna().astype(str).tolist() +
        df["sense2_headword"].dropna().astype(str).tolist() +
        df["sense3_headword"].dropna().astype(str).tolist()
    )
)

selected_headword = st.sidebar.selectbox("Headword", [""] + headwords)
search_query = st.sidebar.text_input("Contains")

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

# -----------------------------
# Render dictionary entries
# -----------------------------

for _, row in filtered_df.iterrows():

    # General info
    general_band = safe(row.get("general_band"))
    general_dict = safe(row.get("general_dictionary"))
    general_thes = safe(row.get("general_thesaurus"))
    related_hw = safe(row.get("general_related_headword"))
    related_rx = safe(row.get("general_related_regex"))

    # Determine main headword
    main_headword = (
        safe(row.get("sense1_headword")) or
        safe(row.get("sense2_headword")) or
        safe(row.get("sense3_headword"))
    )

    st.markdown(f'<div class="headword">{main_headword}</div>', unsafe_allow_html=True)

    meta_parts = []
    if general_band:
        meta_parts.append(f"Band {general_band}")
    if general_dict:
        meta_parts.append(f'<a href="{general_dict}" target="_blank">Dictionary</a>')
    if general_thes:
        meta_parts.append(f'<a href="{general_thes}" target="_blank">Thesaurus</a>')

    if meta_parts:
        st.markdown(f'<div class="meta">{" · ".join(meta_parts)}</div>', unsafe_allow_html=True)

    if related_hw:
        st.markdown(f"**Related headwords:** {related_hw}")
    if related_rx:
        st.markdown(f"**Related regex:** {related_rx}")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Collect senses
    senses = []
    for i in [1, 2, 3]:
        sense = get_sense_data(row, f"sense{i}")
        if sense["headword"]:
            senses.append((f"Sense {i}", sense))

    if not senses:
        st.warning("No senses available.")
        continue

    # Tabs for senses
    tab_labels = [label for label, _ in senses]
    tabs = st.tabs(tab_labels)

    for tab, (label, sense) in zip(tabs, senses):
        with tab:
            st.markdown(
                f'<span class="definition">{sense["definition"]}</span> '
                f'<span class="pos">({sense["pos"]})</span>',
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
                st.markdown(f'<div class="collocates"><b>Typical collocates:</b> {sense["collocates"]}</div>', unsafe_allow_html=True)

            # Collapsible example
            if sense["example"]:
                with st.expander("Show example"):
                    st.markdown(f'<div class="example">{sense["example"]}</div>', unsafe_allow_html=True)

            st.markdown("### Frequency")
            plot_frequency_chart(label, sense)

    st.markdown("<hr style='border:1px solid #ddd'>", unsafe_allow_html=True)
