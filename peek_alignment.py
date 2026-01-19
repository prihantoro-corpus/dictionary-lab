import re

def get_first_n_sentences(filepath, count=5):
    results = []
    current_n = None
    current_tokens = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = re.search(r'<s\s+n="(\d+)"', line)
            if m:
                if current_n is not None:
                    results.append((current_n, " ".join(current_tokens)))
                    if len(results) >= count: return results
                current_n = m.group(1)
                current_tokens = []
            elif '</s>' in line:
                pass
            elif not line.strip().startswith('<'):
                parts = line.split('\t')
                if len(parts) > 0:
                    current_tokens.append(parts[0].strip())
    return results

en_first = get_first_n_sentences('corpora/EN-BPPT-tagged.xml')
id_first = get_first_n_sentences('corpora/ID-BPPT-tagged.xml')

print("EN First 5:")
for n, txt in en_first:
    print(f"n={n}: {txt}")

print("\nID First 5:")
for n, txt in id_first:
    print(f"n={n}: {txt}")
