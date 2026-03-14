import re

eco = set()
sport = set()

in_eco = False
in_sport = False

with open(r'c:\Users\priha\Documents\dictionary-lab\corpora\EN-BPPT-tagged.xml', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line.startswith('<document '):
            domain = re.search(r'domain="([^"]+)"', line)
            if domain:
                d = domain.group(1).lower()
                in_eco = 'economy' in d
                in_sport = 'sport' in d
            else:
                in_eco = False
                in_sport = False
            continue
            
        elif line.startswith('<') or not line:
            # Skip XML tags and empty lines
            continue
            
        # Text line like: Minister    NP    Minister
        if (in_eco and len(eco) < 10) or (in_sport and len(sport) < 10):
            parts = line.split('\t')
            if len(parts) >= 3:
                word = parts[0].strip().lower()
                pos = parts[1].strip()
                if pos.startswith('N') and len(word) > 4 and word.isalpha():
                    if in_eco:
                        eco.add(word)
                    elif in_sport:
                        sport.add(word)

        if len(eco) >= 10 and len(sport) >= 10:
            break

print("Economy:", list(eco))
print("Sport:", list(sport))

with open(r'c:\Users\priha\Documents\dictionary-lab\wordlist\economy.txt', 'w', encoding='utf-8') as f:
    for w in eco:
        f.write(w + '\n')

with open(r'c:\Users\priha\Documents\dictionary-lab\wordlist\sport.txt', 'w', encoding='utf-8') as f:
    for w in sport:
        f.write(w + '\n')

print("Files created.")
