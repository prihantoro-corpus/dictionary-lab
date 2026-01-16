import streamlit as st
import pandas as pd
import os

# =========================
# Page config
# =========================
st.set_page_config(
    page_title="Dictionary Lab",
    layout="wide"
)

# =========================
# Light CSS (box-focused only)
# =========================
st.markdown("""
<style>

/* Sense box */
.sense-box {
    background-color: #f8f9fa;
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    border-left: 5px solid #2a5db0;
}

/* Labels */
.label {
    color: #555;
    font-size: 0.85em;
    font-weight: 600;
}

/* Badges */
.badge {
    display: inline-block;
    background: #e6eefc;
    color: #1f3a8a;
    padding: 3px 8px;
    border-radius: 6px;
    margin-right: 6px;
    margin-bottom: 4px;
    font-size: 0.8em;
    font-weight: 600;
}

/* CEFR */
.badge-cefr {
    background: #2563eb;
    color: white;
}

/* NGSL */
.badge-ngsl {
    background: #059669;
    color: white;
}

/* Academic */
.badge-academic {
    background: #7c3aed;
    color: white;
}

/* Zipf bar */
.zipf-bar {
    background: #e5e7eb;
    border-radius: 6px;
    height: 10px;
    width: 220px;
    margin-top: 4px;
}

.zipf-fill {
    background: #facc15;
    height: 10px;
    border-radius: 6px;
}

/* N-gram item */
.ngram-item {
    background: #f1f5f9;
    padding: 6px 10px;
    border-radius: 6px;
    margin-bottom: 6px;
    border-left: 4px solid #2a5db0;
    font-size: 0.9em;
}

</style>
""", unsafe_allow_html=True)

# =========================
# Helpers
# =========================

def list_excel_files():
    base_dir = os.path.dirname(__file__)
    files = [f for f in os.listdir(base_dir) if f.lower().endswith(".xlsx")]
    return files


def load_excel(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    return pd.read_excel(path)


def zipf_to_percent(zipf):
    try:
        z = float(zipf)
        return min(max(z / 7 * 100, 0), 100)
    except:
        return 0


def render_zipf_bar(zipf_value):
    percent = zipf_to_percent(zipf_value)
    st.markdown(f"""
    <div class="zipf-bar">
        <div class="zipf-fill" style="width:{percent}%;"></div>
    </div>
    """, unsafe_allow_html=True)


def parse_wordlist_badges(wordlist_text):
    badges = []
    if pd.isna(wordlist_text):
        return badges

    parts = str(wordlist_text).split(";")
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


def parse_ngrams_structured(ngram_text):
    """
    Supports:
    bigram > V see = see results ; see ADJ = see clearly ;
    trigram > see DT NN = see the difference ;
    """
    if pd.isna(ngram_text):
        return {}

    result = {}
    current_section = None

    text = str(ngram_text).replace("\n", " ")

    tokens = text.split(";")
    for token in tokens:
        token = token.strip()
        if not token:
            continue

        if ">" in token:
            section, rest = token.split(">", 1)
            current_section = section.strip().lower()
            result[current_section] = []
            token = rest.strip()

        if "=" in token and current_section:
            left, right = token.split("=", 1)
            result[current_section].append((left.strip(), right.strip()))

    return result


# =========================
# App
# =========================

st.title("Dictionary Lab")

excel_files = list_excel_files()

if not excel_files:
    st.error("No Excel files found in the repository folder.")
    st.stop()

selected_file = st.selectbox("Select dictionary file", excel_files)

data = load_excel(selected_file)

search_word = st.text_input("Search word", placeholder="e.g. saw, bank, run")

if search_word:
    row = data[data["general_word"].astype(str).str.lower() == search_word.lower()]

    if row.empty:
        st.warning("Word not found.")
    else:
        row = row.iloc[0]

        # =========================
        # Header
        # =========================
        st.markdown(f"## {row['general_word']}")

        render_wordlist_badges(row.get("general_wordlist"))

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<span class='label'>Corpus:</span> {row.get('general_corpus','')}", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<span class='label'>Frequency:</span> {row.get('general_frequency','')}", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<span class='label'>PMW:</span> {row.get('general_pmw','')}", unsafe_allow_html=True)

        st.markdown(f"<span class='label'>Band:</span> {row.get('general_band','')}", unsafe_allow_html=True)
        render_zipf_bar(row.get("general_zipf"))

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
                        f"### {row.get(f'sense{i}_headword','')} "
                        f"<span class='badge'>{row.get(f'sense{i}_pos','')}</span>",
                        unsafe_allow_html=True
                    )

                    # Definition
                    st.markdown(f"**Definition:** {row.get(f'sense{i}_definition','')}")

                    # Frequency info
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"<span class='label'>Frequency:</span> {row.get(f'sense{i}_frequency','')}", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"<span class='label'>PMW:</span> {row.get(f'sense{i}_pmw','')}", unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"<span class='label'>Band:</span> {row.get(f'sense{i}_band','')}", unsafe_allow_html=True)

                    render_zipf_bar(row.get(f"sense{i}_zipf"))

                    # Example (not collapsible)
                    if pd.notna(row.get(f"sense{i}_example")):
                        st.markdown(f"<span class='label'>Example:</span> {row.get(f'sense{i}_example')}", unsafe_allow_html=True)

                    # Typical collocates
                    if pd.notna(row.get(f"sense{i}_typical_collocates")):
                        st.markdown(f"<span class='label'>Typical collocates:</span> {row.get(f'sense{i}_typical_collocates')}", unsafe_allow_html=True)

                    # Domain / Register / Year
                    meta = []
                    if pd.notna(row.get(f"sense{i}_domain")):
                        meta.append(str(row.get(f"sense{i}_domain")))
                    if pd.notna(row.get(f"sense{i}_register")):
                        meta.append(str(row.get(f"sense{i}_register")))
                    if pd.notna(row.get(f"sense{i}_year")):
                        meta.append(str(row.get(f"sense{i}_year")))

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
        ngram_groups = parse_ngrams_structured(ngram_text)

        if ngram_groups:
            for section, pairs in ngram_groups.items():
                st.markdown(f"### {section.capitalize()}")

                for pattern, example in pairs:
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
            st.markdown("## Related headwords")
            st.write(row.get("general_related_headword"))
