import os
import csv

# Try importing cefrpy
try:
    from cefrpy import CEFRAnalyzer
    HAS_CEFR = True
except ImportError:
    HAS_CEFR = False
    print("cefrpy not installed.")

WORDLIST_DIR = "wordlist"
_cache = {}

def load_wordlists():
    """
    Loads all wordlists in the directory into memory.
    Format expected: CSV (token, level/value) or TXT (token).
    """
    global _cache
    if _cache: return _cache
    
    if not os.path.exists(WORDLIST_DIR):
        os.makedirs(WORDLIST_DIR)
        return {}

    loaded = {}
    
    for filename in os.listdir(WORDLIST_DIR):
        filepath = os.path.join(WORDLIST_DIR, filename)
        
        # SKIP DIRECTORIES (like __pycache__)
        if not os.path.isfile(filepath):
            continue
            
        name = os.path.splitext(filename)[0].upper()
        
        try:
            entries = {}
            with open(filepath, 'r', encoding='utf-8') as f:
                # auto-detect format
                if filename.endswith('.csv'):
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2:
                            entries[row[0].lower()] = row[1] # token -> level
                        elif len(row) == 1:
                            entries[row[0].lower()] = "yes"
                elif filename.endswith('.txt'):
                    # Assume text file one word per line
                     for line in f:
                         word = line.strip().lower()
                         if word:
                             entries[word] = "yes"
                else:
                    continue # Skip other types
            loaded[name] = entries
        except Exception as e:
            print(f"Failed to load {filename}: {e}")
            
    _cache = loaded
    return _cache

def check_token(token):
    """
    Returns list of dicts: {'name': 'NGSL', 'value': '1'}
    """
    lists = load_wordlists()
    badges = []
    
    token_lower = token.lower()
    
    # Check static lists
    for list_name, data in lists.items():
        if token_lower in data:
            badges.append({
                'name': list_name,
                'value': data[token_lower]
            })
            
    # Check CEFR (Library)
    if HAS_CEFR:
        try:
            # cefrpy usage: CEFRAnalyzer().get_pos_level_dict_for_word(word)
            analyzer = CEFRAnalyzer()
            res_dict = analyzer.get_pos_level_dict_for_word(token_lower)
            if res_dict:
                # Extract unique level names (A1, B2, etc.)
                levels = sorted(list(set([lvl.name for lvl in res_dict.values()])))
                if levels:
                    badges.append({'name': 'CEFR', 'value': ",".join(levels)})
        except Exception as e:
            pass
            
    return badges
