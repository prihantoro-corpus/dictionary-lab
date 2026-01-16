# app.py
import pandas as pd
import streamlit as st

# Page config
st.set_page_config(page_title="Excel N-gram Dashboard", layout="wide")
st.title("📊 Excel Dashboard: Words, Senses, and N-grams")

# CSS for styling
st.markdown("""
<style>
h3 { color: #1f77b4; }
h4 { color: #ff7f0e; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ddd; padding: 8px; }
th { background-color: #f2f2f2; text-align: left; }
td { background-color: #fcfcfc; }
.code-box { background-color: #f4f4f4; border-left: 4px solid #1f77b4; padding: 10px; margin-bottom: 10px; font-family: monospace; white-space: pre-wrap; }
.collapsible { background-color: #e7f0f7; cursor: pointer; padding: 10px; border: none; text-align: left; outline: none; font-size: 16px; width: 100%; margin-bottom: 5px; }
.content { padding: 0 15px; display: none; overflow: hidden; background-color: #f9f9f9; margin-bottom: 10px;}
.badge { display: inline-block; padding: 5px 10px; border-radius: 12px; color: white; margin-right: 5px; font-size: 12px; font-weight: bold;}
.badge-cefr { background-color: #1f77b4; }
.badge-ngsl { background-color: #2ca02c; }
.badge-academic { background-color: #ff7f0e; }
.badge-other { background-color: #ffdb58; color: #333; }
</style>
""", unsafe_allow_html=True)

# Upload file
st.sidebar.header("Upload Excel/CSV")
uploaded_file = st.sidebar.file_uploader("Choose a file", type=["xlsx", "csv"])

if uploaded_file:
    # Load file
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)

    if 'general_word' not in df.columns:
        st.error("The file must contain a 'general_word' column.")
    else:
        # Sidebar select
        word_list = df['general_word'].unique()
        selected_word = st.sidebar.selectbox("Select word", word_list)

        # Filter row
        row = df[df['general_word'] == selected_word].iloc[0]

        # Display badges for general_wordlist
        if 'general_wordlist' in df.columns and pd.notna(row['general_wordlist']):
            st.markdown("### 🏷 Wordlist Badges")
            badges = [b.strip() for b in row['general_wordlist'].split(";")]
            badge_html = ""
            for b in badges:
                if b.lower().startswith("cefr"):
                    badge_html += f"<span class='badge badge-cefr'>{b}</span>"
                elif b.lower().startswith("ngsl"):
                    badge_html += f"<span class='badge badge-ngsl'>{b}</span>"
                elif b.lower().startswith("academic"):
                    badge_html += f"<span class='badge badge-academic'>{b}</span>"
                else:
                    badge_html += f"<span class='badge badge-other'>{b}</span>"
            st.markdown(badge_html, unsafe_allow_html=True)

        # Create 3-column layout
        col1, col2, col3 = st.columns(3)

        # --- Column 1: General metadata ---
        with col1:
            st.subheader("📁 General Metadata")
            general_cols = [c for c in df.columns if c.startswith('general_') and c != 'general_wordlist']
            general_data = row[general_cols].to_frame().rename(columns={selected_word: "Value"})
            st.table(general_data)

        # --- Column 2: Senses ---
        with col2:
            st.subheader("🧩 Senses")
            for i in range(1, 4):
                sense_head = f'sense{i}_headword'
                if sense_head in df.columns and pd.notna(row[sense_head]):
                    st.markdown(f"<button class='collapsible'>Sense {i}: {row[sense_head]} ({row.get(f'sense{i}_pos', '')})</button>", unsafe_allow_html=True)
                    sense_cols = [c for c in df.columns if c.startswith(f'sense{i}_')]
                    sense_data = row[sense_cols].to_frame().rename(columns={selected_word: "Value"})
                    st.markdown(f"<div class='content'>{sense_data.to_html(classes='table', header=True, index=True)}</div>", unsafe_allow_html=True)

        # --- Column 3: N-grams ---
        with col3:
            st.subheader("🔗 N-gram Patterns")
            if 'general_n-gram_POS' in df.columns and pd.notna(row['general_n-gram_POS']):
                ngram_lines = [line.strip() for line in row['general_n-gram_POS'].split("\n") if line.strip()]
                for line in ngram_lines:
                    if line.lower().startswith("bigram"):
                        st.markdown(f"<div class='code-box'><strong>Bigram:</strong> {line[len('bigram >'):].strip()}</div>", unsafe_allow_html=True)
                    elif line.lower().startswith("trigram"):
                        st.markdown(f"<div class='code-box'><strong>Trigram:</strong> {line[len('trigram >'):].strip()}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='code-box'>{line}</div>", unsafe_allow_html=True)

        # --- JS for collapsible sections ---
        st.markdown("""
        <script>
        var coll = document.getElementsByClassName("collapsible");
        for (var i = 0; i < coll.length; i++) {
          coll[i].addEventListener("click", function() {
            this.classList.toggle("active");
            var content = this.nextElementSibling;
            if (content.style.display === "block") {
              content.style.display = "none";
            } else {
              content.style.display = "block";
            }
          });
        }
        </script>
        """, unsafe_allow_html=True)

else:
    st.info("Upload an Excel or CSV file to visualise its contents.")
