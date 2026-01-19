import re

def analyze_corpus(filepath):
    doc_stats = []
    current_sents = 0
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '<document' in line:
                if current_sents > 0 or doc_stats:
                    doc_stats.append(current_sents)
                current_sents = 0
            m = re.search(r'<s\s+n="(\d+)"', line)
            if m:
                current_sents += 1
        doc_stats.append(current_sents)
    return doc_stats

en_stats = analyze_corpus('corpora/EN-BPPT-tagged.xml')
id_stats = analyze_corpus('corpora/ID-BPPT-tagged.xml')

print(f"EN Doc Sentence Counts: {en_stats}, Total: {sum(en_stats)}")
print(f"ID Doc Sentence Counts: {id_stats}, Total: {sum(id_stats)}")

if len(en_stats) != len(id_stats):
    print("WARNING: Number of documents mismatch!")
else:
    for i, (e, d) in enumerate(zip(en_stats, id_stats)):
        if e == d:
            print(f"Doc {i+1}: Aligned ({e} sentences)")
        else:
            print(f"Doc {i+1}: MISMATCH! EN={e}, ID={d}")
