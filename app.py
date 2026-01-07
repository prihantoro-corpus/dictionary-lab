# app.py
# CORTEX DICTIONARY LAB – TreeTagger + inline XML prototype

import streamlit as st
import pandas as pd
import numpy as np
import re
import math
import random
from collections import Counter, defaultdict

st.set_page_config(page_title="CORTEX DICTIONARY LAB", layout="wide")
st.title("🧠 CORTEX DICTIONARY LAB – TreeTagger + Inline XML")

PUNCTUATION = set(list(".,!?;:()[]{}\"'—–-…"))

# =========================================================
# Utilities
# =========================================================

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

# =========================================================
# CORE: TreeTagger + Inline XML Parser (THIS IS THE KEY)
# =========================================================

def parse_treetagger_with_inline_xml(file):
    rows = []
    active_attrs = {}   # e.g. {"domain": "spoken", "year": "2013"}

    content = file.read().decode("utf-8", errors="ignore")
    lines = content.splitlines()

    sent_id = 0

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # -----------------------------------------
        # Opening tag: <domain=spoken>, <year=2013>
        # -----------------------------------------
        if line.startswith("<") and line.endswith(">") and not line.startswith("</"):
            inner = line[1:-1].strip()
            if "=" in inner:
                k, v = inner.split("=", 1)
                active_attrs[k.strip()] = v.strip()
            continue

        # -----------------------------------------
        # Closing tag: </domain>
        # -----------------------------------------
        if line.startswith("</") and line.endswith(">"):
            tag = line[2:-1].strip()
            if tag in active_attrs:
                del active_attrs[tag]
            continue

        # -----------------------------------------
        # TreeTagger token line: token \t POS \t lemma
        # -----------------------------------------
        parts = line.split("\t")
        if len(parts) < 3:
            continue

        token = parts[0].strip()
        pos = parts[1].strip()
        lemma = parts[2].strip()

        sent_id += 1

        row = {
            "token": token,
            "pos": pos,
            "lemma": lemma,
            "sent_id": sent_id
        }

        # attach active XML attributes
        for k, v in active_attrs.items():
            row[k] = v

        rows.append(row)

    df = pd.DataFrame(rows)
    return df

# =========================================================
# N-grams
# =========================================================

def compute_ngrams(tokens, target):
    tokens = [t for t in tokens if t not in PUNCTUATION]
    bigrams = Counter()
    trigrams = Counter()

    for i in range(len(tokens) - 1):
        bigrams[(tokens[i], tokens[i+1])] += 1

    for i in range(len(tokens) - 2):
        trigrams[(tokens[i], tokens[i+1], tokens[i+2])] += 1

    wc = {bg: c for bg, c in bigrams.items() if bg[0].lower() == target.lower()}
    cw = {bg: c for bg, c in bigrams.items() if bg[1].lower() == target.lower()}

    wcc = {tg: c for tg, c in trigrams.items() if tg[0].lower() == target.lower()}
    cwc = {tg: c for tg, c in trigrams.items() if tg[1].lower() == target.lower()}
    ccw = {tg: c for tg, c in trigrams.items() if tg[2].lower() == target.lower()}

    result = []
    result += [" ".join(bg) for bg, _ in sorted(wc.items(), key=lambda x: x[1], reverse=True)[:2]]
    result += [" ".join(bg) for bg, _ in sorted(cw.items(), key=lambda x: x[1], reverse=True)[:2]]
    result += [" ".join(tg) for tg, _ in sorted(wcc.items(), key=lambda x: x[1], reverse=True)[:1]]
    result += [" ".join(tg) for tg, _ in sorted(cwc.items(), key=lambda x: x[1], reverse=True)[:1]]
    result += [" ".join(tg) for tg, _ in sorted(ccw.items(), key=lambda x: x[1], reverse=True)[:1]]

    return result

# =========================================================
# Collocates (PER SENSE)
# =========================================================

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

# =========================================================
# KWIC (PER SENSE)
# =========================================================

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

# =========================================================
# Session state
# =========================================================

if "corpora" not in st.session_state:
    st.session_state["corpora"] = {}

# =========================================================
# UI – Data-driven only (corpus)
# =========================================================

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
        "Upload TreeTagger corpus files (with inline XML)",
        type=["txt", "xml"],
        accept_multiple_files=True
    )

    if uploaded_files:
        for f in uploaded_files:
            df = parse_treetagger_with_inline_xml(f)
            df["corpus"] = selected_corpus
            st.session_state["corpora"][selected_corpus].append(df)

        st.success("Files added to corpus.")

# =========================================================
# Query
# =========================================================

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

        # =================================================
        # SENSES = POS-BASED
        # =================================================

        pos_tags = full_df[full_df["token"].str.lower() == query_word.lower()]["pos"].unique()
        if len(pos_tags) == 0:
            pos_tags = ["NA"]

        for i, pos in enumerate(pos_tags, start=1):
            st.markdown(f"## Sense {i} ({pos})")

            sense_df = full_df[(full_df["token"].str.lower() == query_word.lower()) & (full_df["pos"] == pos)]
            sense_context_df = full_df[full_df["pos"] == pos]

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

            # -----------------------------
            # Collocates (per sense)
            # -----------------------------
            coll = compute_collocates(sense_context_df, query_word)
            with st.expander("Typical collocates (top 20) – per sense"):
                if coll:
                    for w, c in coll:
                        st.write(f"{w} ({c})")
                else:
                    st.write("NA")

            # -----------------------------
            # KWIC (per sense)
            # -----------------------------
            kwic = generate_kwic(sense_context_df, query_word, max_examples=3)
            st.markdown("**Examples (KWIC – per sense):**")
            if kwic:
                for left, node, right in kwic:
                    st.markdown(f"{left} **{node}** {right}")
            else:
                st.write("NA")

            # -----------------------------
            # ATTRIBUTES (domain, year, etc.)
            # -----------------------------
            attr_cols = [c for c in sense_df.columns if c not in ["token", "pos", "lemma", "sent_id", "corpus"]]
            for ac in attr_cols:
                vals = sense_df[ac].dropna().unique()
                if len(vals) > 0:
                    st.write(f"**{ac}:** {', '.join(vals)}")
