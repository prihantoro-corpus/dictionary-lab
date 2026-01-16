import streamlit as st
import pandas as pd
import os

# =========================
# Config
# =========================
st.set_page_config(
    page_title="Dictionary Lab",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================
# Styling (Cambridge-like)
# =========================
st.markdown("""
<style>
body {
    background-color: #0f1720;
    color: #e5e7eb;
}
.main {
    background-color: #0f1720;
}
h1, h2, h3, h4 {
    color: #facc15;
}
.sense-box {
    background-color: #111827;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
    border-left: 4px solid #facc15;
}
.label {
    color: #9ca3af;
    font-size: 0.85em;
}
.badge {
    display: inline-block;
    background: #1f2933;
    padding: 3px 8px;
    border-radius: 6px;
    margin-right: 6px;
    margin-bottom: 4px;
    font-size: 0.8em;
    color: #e5e7eb;
}
.badge-cefr {
    background: #2563eb;
}
.badge-ngsl {
    background: #059669;
}
.badge-academic {
    background: #7c3aed;
}
.zipf-bar {
    background: #1f2933;
    border-radius: 6px;
    height: 10px;
    width: 220px;
    margin-top: 5px;
}
.zipf-fill {
    background: #facc15;
    height: 10px;
    border-radius: 6px;
}
.ngram-item {
    margin-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)


# =========================
# Helpers
# =========================

def load_data():
    file_path = os.path.join(os.path.dirname(__file__), "sample_dictionary.xlsx")
    return pd.read_excel(file_path)


def zipf_to_percent(zipf):
    try:
        z = float(zipf)
        return min(max(z / 7 * 100, 0), 100)  # Zipf scale 0–7
    except:
        return 0


def render_zipf_bar(zipf_value):
    percent = zipf_to_percent(zipf_value)
    st.markdown(f"""
    <div class="zipf-bar">
        <div class="zipf-fill" style="width:{percent}%;"></div>
    </div>
    """, unsafe_allow_html=True)


def parse_ngrams(ngram_text):
    """
    Format:
    ADJ bank = online bank ; bank NN = bank service ;
    """
    results = []
    if pd.isna(ngram_text):
        return results

    parts = ngram_text.split(";")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            left, right = part.split("=", 1)
            results.append((left.strip(), right.strip()))
    return results


def parse_wordlist_badges(wordlist_text):
    """
    Format:
    NGSL=L12; CEFR=A2; academic=AC3;
    """
    badges = []
    if pd.isna(wordlist_text):
        return badges

    parts = wordlist_text.split(";")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
            badges.append((key.strip(), value.strip()))
    return badges


def render_wordlist_badges(wordlist_text):
    badges = parse_wordlist_badges(wordlist_text)
    html = ""

    for key, value in badges:
        key_lower = key.lower()

        css_class = "badge"
        if key_lower == "cefr":
            css_class = "badge badge-cefr"
        elif key_lower == "ngsl":
            css_class = "badge badge-ngsl"
        elif key_lower == "academic":
            css_class = "badge badge-academic"

        html += f"<span class='{css_class}'>{key}: {value}</span>"

    if html:
        st.markdown(html, unsafe_allow_html=True)


# =========================
# App
# =========================

st.title("Dictionary Lab")

data = load_data()

search_word = st.text_input("Search word", placeholder="e.g. bank")

if search_word:
    row = data[data["general_word"].str.lower() == search_word.lower()]

    if row.empty:
        st.warning("Word not found.")
    else:
        row = row.iloc[0]

        # =========================
        # Header
        # =========================
        st.markdown(f"## {row['general_word']}")

        # Wordlist badges (CEFR, NGSL, Academic, etc.)
        render_wordlist_badges(row.get("general_wordlist"))

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<span class='label'>Corpus:</span> {row['general_corpus']}", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<span class='label'>Frequency:</span> {row['general_frequency']}", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<span class='label'>PMW:</span> {row['general_pmw']}", unsafe_allow_html=True)

        st.markdown(f"<span class='label'>Band:</span> {row['general_band']}", unsafe_allow_html=True)
        render_zipf_bar(row["general_zipf"])

        st.markdown("---")

        # =========================
        # Senses (Tabs)
        # =========================
        sense_tabs = []
        sense_keys = []

        for i in range(1, 4):
            head = row.get(f"sense{i}_headword")
            if pd.notna(head):
                sense_tabs.append(f"Sense {i}")
                sense_keys.append(i)

        if sense_tabs:
            tabs = st.tabs(sense_tabs)

            for tab, i in zip(tabs, sense_keys):
                with tab:
                    st.markdown("<div class='sense-box'>", unsafe_allow_html=True)

                    st.markdown(
                        f"### {row[f'sense{i}_headword']} "
                        f"<span class='badge'>{row[f'sense{i}_pos']}</span>",
                        unsafe_allow_html=True
                    )

                    # Definition
                    st.markdown(f"**Definition:** {row[f'sense{i}_definition']}")

                    # Frequency info
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"<span class='label'>Frequency:</span> {row[f'sense{i}_frequency']}", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"<span class='label'>PMW:</span> {row[f'sense{i}_pmw']}", unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"<span class='label'>Band:</span> {row[f'sense{i}_band']}", unsafe_allow_html=True)

                    render_zipf_bar(row[f"sense{i}_zipf"])

                    # Example (NOT collapsible)
                    if pd.notna(row[f"sense{i}_example"]):
                        st.markdown(f"<span class='label'>Example:</span> {row[f'sense{i}_example']}", unsafe_allow_html=True)

                    # Typical collocates
                    if pd.notna(row[f"sense{i}_typical_collocates"]):
                        st.markdown(f"<span class='label'>Typical collocates:</span> {row[f'sense{i}_typical_collocates']}", unsafe_allow_html=True)

                    # Domain / Register / Year
                    meta = []
                    if pd.notna(row[f"sense{i}_domain"]):
                        meta.append(str(row[f"sense{i}_domain"]))
                    if pd.notna(row[f"sense{i}_register"]):
                        meta.append(str(row[f"sense{i}_register"]))
                    if pd.notna(row[f"sense{i}_year"]):
                        meta.append(str(row[f"sense{i}_year"]))

                    if meta:
                        st.markdown(
                            " ".join([f"<span class='badge'>{m}</span>" for m in meta]),
                            unsafe_allow_html=True
                        )

                    st.markdown("</div>", unsafe_allow_html=True)

        # =========================
        # N-GRAMS
        # =========================
        st.markdown("## N-grams")

        ngram_text = row.get("general_n-gram_POS")
        ngrams = parse_ngrams(ngram_text)

        if ngrams:
            for pattern, example in ngrams:
                st.markdown(
                    f"<div class='ngram-item'><span class='badge'>{pattern}</span> → {example}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown("<span class='label'>No n-grams available.</span>", unsafe_allow_html=True)

        # =========================
        # Related
        # =========================
        if pd.notna(row.get("general_related_headword")):
            st.markdown("## Related")
            st.write(row["general_related_headword"])
