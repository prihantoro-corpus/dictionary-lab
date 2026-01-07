# app.py
# CORTEX DICTIONARY LAB – Single File Prototype
# Data-driven + Excel-driven Lexicography Lab
# Per-sense collocates and per-sense KWIC

import streamlit as st
import pandas as pd
import numpy as np
import re
import math
import random
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

# ===============================
# Page config
# ===============================
st.set_page_config(page_title="CORTEX DICTIONARY LAB", layout="wide")
st.title("🧠 CORTEX DICTIONARY LAB – Prototype (Single File)")

# ===============================
# Utilities
# ===============================

PUNCTUATION = set(list(".,!?;:()[]{}\"'—–-…"))

def tokenize(text):
    text = re.sub(r"([^\w\s])", r" \1 ", text)
    return [t for t in text.split() if t.strip()]

def pmw_to_zipf(pmw):
    if pmw <= 0:
        return None
    return round(math.log10(pmw) + 3, 2)

def zipf_to_band(zipf):
    if zipf is None:
        return None
    if zipf >= 7: return 1
    if zipf >= 6: return 2
    if zipf >= 5: return 3
    if zipf >= 4: return 4
    return 5

def build_dictionary_link(word, lang):
    if lang == "EN":
        return f"https://www.collinsdictionary.com/dictionary/english/{word}"
    elif lang == "ID":
        return f"https://kbbi.kemdikbud.go.id/entri/{word}"
    return "NA"

def build_thesaurus_link(word, lang):
    if lang == "EN":
        return f"https://www.collinsdictionary.com/dictionary/english-thesaurus/{word}"
    elif lang == "ID":
        return f"https://tesaurus.kemendikdasmen.go.id/tematis/lema/{word}"
    return "NA"

# ===============================
# XML Parsing
# ===============================

def parse_xml_file(file):
    content = file.read().decode("utf-8", errors="ignore")
    root = ET.fromstring(content)

    rows = []
    attributes_detected = defaultdict(set)

    for elem in root.iter():
        for k, v in elem.attrib.items():
            attributes_detected[k].add(v)

    sent_id = 0
    for sent in root.findall(".//s") + root.findall(".//sent"):
        sent_id += 1
        tokens = sent.findall(".//w")
        if tokens:
            for w in tokens:
                token = w.text.strip() if w.text else ""
                pos = w.get("pos", "NA")
                lemma = w.get("lemma", "NA")
                row = {
                    "token": token,
                    "pos": pos,
                    "lemma": lemma,
                    "sent_id": sent_id
                }
                for k, v in sent.attrib.items():
                    row[k] = v
                rows.append(row)
        else:
            raw = "".join(sent.itertext())
            toks = tokenize(raw)
            for t in toks:
                rows.append({
                    "token": t,
                    "pos": "NA",
                    "lemma": "NA",
                    "sent_id": sent_id
                })

    return pd.DataFrame(rows), attributes_detected

# ===============================
# N-gram computation
# ===============================

def compute_ngrams(tokens, target):
    tokens = [t for t in tokens if t not in PUNCTUATION]
    bigrams = Counter()
    trigrams = Counter()

    for i in range(len(tokens) - 1):
        bg = (tokens[i], tokens[i+1])
        bigrams[bg] += 1

    for i in range(len(tokens) - 2):
        tg = (tokens[i], tokens[i+1], tokens[i+2])
        trigrams[tg] += 1

    wc = {bg: c for bg, c in bigrams.items() if bg[0].lower() == target.lower()}
    cw = {bg: c for bg, c in bigrams.items() if bg[1].lower() == target.lower()}

    top_wc = sorted(wc.items(), key=lambda x: x[1], reverse=True)[:2]
    top_cw = sorted(cw.items(), key=lambda x: x[1], reverse=True)[:2]

    wcc = {tg: c for tg, c in trigrams.items() if tg[0].lower() == target.lower()}
    cwc = {tg: c for tg, c in trigrams.items() if tg[1].lower() == target.lower()}
    ccw = {tg: c for tg, c in trigrams.items() if tg[2].lower() == target.lower()}

    top_wcc = sorted(wcc.items(), key=lambda x: x[1], reverse=True)[:1]
    top_cwc = sorted(cwc.items(), key=lambda x: x[1], reverse=True)[:1]
    top_ccw = sorted(ccw.items(), key=lambda x: x[1], reverse=True)[:1]

    result = []
    for (bg, _) in top_wc + top_cw:
        result.append(" ".join(bg))
    for (tg, _) in top_wcc + top_cwc + top_ccw:
        result.append(" ".join(tg))

    return result

# ===============================
# Collocates (PER SENSE)
# ===============================

def compute_collocates(df, target, window=5):
    coll = Counter()
    tokens = df["token"].tolist()

    for i, t in enumerate(tokens):
        if t.lower() == target.lower():
            start = max(0, i - window)
            end = min(len(tokens), i + window + 1)
            for j in range(start, end):
                if j != i:
                    candidate = tokens[j].lower()
                    if candidate not in PUNCTUATION and candidate != target.lower():
                        coll[candidate] += 1

    return coll.most_common(20)

# ===============================
# KWIC (PER SENSE)
# ===============================

def generate_kwic(df, target, max_examples=3):
    rows = []
    grouped = df.groupby("sent_id")

    for _, group in grouped:
        tokens = group["token"].tolist()
        lowered = [t.lower() for t in tokens]

        if target.lower() in lowered:
            idxs = [i for i, t in enumerate(lowered) if t == target.lower()]
            for idx in idxs:
                left = " ".join(tokens[max(0, idx-7):idx])
                node = tokens[idx]
                right = " ".join(tokens[idx+1:idx+8])
                rows.append((left, node, right))

    random.shuffle(rows)
    return rows[:max_examples]

# ===============================
# Excel processing
# ===============================

def process_excel(df):
    df.columns = [c.strip().lower() for c in df.columns]
    entries = []

    for _, row in df.iterrows():
        entry = {"general": {}, "senses": {}}

        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                continue

            if col.startswith("general_"):
                key = col.replace("general_", "")
                entry["general"][key] = val

            elif col.startswith("sense"):
                m = re.match(r"sense(\d+)_(.+)", col)
                if m:
                    sense_no = int(m.group(1))
                    field = m.group(2)
                    if sense_no not in entry["senses"]:
                        entry["senses"][sense_no] = {}
                    entry["senses"][sense_no][field] = val

        entries.append(entry)

    return entries

# ===============================
# Session state
# ===============================

if "corpora" not in st.session_state:
    st.session_state["corpora"] = {}

# ===============================
# UI – Mode selection
# ===============================

mode = st.radio("Choose mode", ["Data-driven (Corpus)", "Excel-driven"])

# ===============================
# Data-driven mode
# ===============================

if mode == "Data-driven (Corpus)":
    st.subheader("📚 Corpus Manager")

    new_corpus = st.text_input("New corpus name")
    if st.button("Add corpus"):
        if new_corpus:
            st.session_state["corpora"][new_corpus] = []
            st.success(f"Corpus '{new_corpus}' added.")

    corpus_names = list(st.session_state["corpora"].keys())

    if corpus_names:
        selected_corpus = st.selectbox("Select corpus", corpus_names)
        uploaded_files = st.file_uploader(
            "Upload files (txt or xml)", type=["txt", "xml"], accept_multiple_files=True
        )

        if uploaded_files:
            for f in uploaded_files:
                if f.name.endswith(".xml"):
                    df, attrs = parse_xml_file(f)
                else:
                    text = f.read().decode("utf-8", errors="ignore")
                    toks = tokenize(text)
                    df = pd.DataFrame({
                        "token": toks,
                        "pos": ["NA"] * len(toks),
                        "lemma": ["NA"] * len(toks),
                        "sent_id": list(range(1, len(toks)+1))
                    })
                df["corpus"] = selected_corpus
                st.session_state["corpora"][selected_corpus].append(df)

            st.success("Files added to corpus.")

    # ===============================
    # Query
    # ===============================

    st.subheader("🔎 Dictionary Query")
    query_word = st.text_input("Enter word")

    if query_word:
        all_dfs = []
        for c, dfs in st.session_state["corpora"].items():
            for d in dfs:
                all_dfs.append(d)

        if not all_dfs:
            st.warning("No data.")
        else:
            full_df = pd.concat(all_dfs, ignore_index=True)

            total_tokens = len(full_df)
            freq = (full_df["token"].str.lower() == query_word.lower()).sum()
            pmw = (freq / total_tokens) * 1_000_000 if total_tokens > 0 else 0
            zipf = pmw_to_zipf(pmw)
            band = zipf_to_band(zipf)

            corpora_used = ", ".join(sorted(full_df[full_df["token"].str.lower() == query_word.lower()]["corpus"].unique()))

            related_head = sorted(set(full_df[full_df["lemma"].str.lower() == query_word.lower()]["token"]))
            related_regex = sorted(set(full_df[full_df["token"].str.contains(query_word, case=False)]["token"]))

            lang = st.selectbox("Language", ["EN", "ID", "OTHER"])

            st.markdown("## General")
            gen_cols = st.columns(4)
            gen_cols[0].metric("Frequency", freq)
            gen_cols[1].metric("PMW", round(pmw, 2))
            gen_cols[2].metric("Zipf", zipf if zipf else "NA")
            gen_cols[3].metric("Band", band if band else "NA")

            st.write(f"**Corpus:** {corpora_used if corpora_used else 'NA'}")
            st.write(f"**Related words (headword):** {', '.join(related_head) if related_head else 'NA'}")
            st.write(f"**Related words (regex):** {', '.join(related_regex) if related_regex else 'NA'}")

            st.write(f"**Dictionary:** {build_dictionary_link(query_word, lang)}")
            st.write(f"**Thesaurus:** {build_thesaurus_link(query_word, lang)}")

            tokens_all = full_df["token"].tolist()
            ngrams = compute_ngrams(tokens_all, query_word)
            st.write(f"**N-grams:** {', '.join(ngrams) if ngrams else 'NA'}")

            # ===============================
            # Sense handling (PER POS)
            # ===============================

            pos_tags = full_df[full_df["token"].str.lower() == query_word.lower()]["pos"].unique()
            if len(pos_tags) == 0 or all(p == "NA" for p in pos_tags):
                pos_tags = ["NA"]

            for i, pos in enumerate(pos_tags, start=1):
                st.markdown(f"## Sense {i} ({pos})")

                if pos != "NA":
                    sense_df = full_df[(full_df["token"].str.lower() == query_word.lower()) & (full_df["pos"] == pos)]
                    sense_context_df = full_df[full_df["pos"] == pos]
                else:
                    sense_df = full_df[full_df["token"].str.lower() == query_word.lower()]
                    sense_context_df = full_df

                sfreq = len(sense_df)
                spmw = (sfreq / total_tokens) * 1_000_000 if total_tokens > 0 else 0
                szipf = pmw_to_zipf(spmw)
                sband = zipf_to_band(szipf)

                cols = st.columns(4)
                cols[0].metric("Frequency", sfreq)
                cols[1].metric("PMW", round(spmw, 2))
                cols[2].metric("Zipf", szipf if szipf else "NA")
                cols[3].metric("Band", sband if sband else "NA")

                lemma_vals = sense_df["lemma"].unique()
                lemma = lemma_vals[0] if len(lemma_vals) > 0 else "NA"
                st.write(f"**Headword (lemma):** {lemma}")
                st.write(f"**POS:** {pos}")

                # Collocates – per sense
                coll = compute_collocates(sense_context_df, query_word)
                with st.expander("Typical collocates (top 20) – per sense"):
                    if coll:
                        for w, c in coll:
                            st.write(f"{w} ({c})")
                    else:
                        st.write("NA")

                # KWIC – per sense
                kwic = generate_kwic(sense_context_df, query_word, max_examples=3)
                st.markdown("**Examples (KWIC – per sense):**")
                if kwic:
                    for left, node, right in kwic:
                        st.markdown(f"{left} **{node}** {right}")
                else:
                    st.write("NA")

                # Attributes (XML)
                attr_cols = [c for c in sense_df.columns if c not in ["token", "pos", "lemma", "sent_id", "corpus"]]
                for ac in attr_cols:
                    vals = sense_df[ac].dropna().unique()
                    if len(vals) > 0:
                        st.write(f"**{ac}:** {', '.join(vals)}")

# ===============================
# Excel-driven mode
# ===============================

else:
    st.subheader("📄 Excel Upload")
    excel_file = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])

    if excel_file:
        df = pd.read_excel(excel_file)
        entries = process_excel(df)

        query_word = st.text_input("Search word (general_word)")

        if query_word:
            found = False
            for entry in entries:
                if entry["general"].get("word", "").lower() == query_word.lower():
                    found = True

                    st.markdown("## General")
                    for k, v in entry["general"].items():
                        st.write(f"**{k}:** {v}")

                    for sense_no, sense_data in entry["senses"].items():
                        st.markdown(f"## Sense {sense_no}")
                        for k, v in sense_data.items():
                            st.write(f"**{k}:** {v}")

            if not found:
                st.warning("No entry found.")
