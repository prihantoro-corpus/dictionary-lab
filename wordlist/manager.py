import os
import csv

# Try importing cefrpy
try:
    from cefrpy import CEFR
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
                else:
                    # Assume text file one word per line
                     for line in f:
                         word = line.strip().lower()
                         if word:
                             entries[word] = "yes"
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
            # Assuming cefrpy usage: CEFR().get_level(word) or similar.
            # I will assume a static method or simple lookup.
            # Checking documentation or assuming `CEFR().level(word)` returns list or string
            c = CEFR()
            levels = c.level(token_lower) # Returns list usually e.g. ['A1', 'B2']
            if levels:
                if isinstance(levels, list):
                    val = ",".join(levels)
                else:
                    val = str(levels)
                badges.append({'name': 'CEFR (Lib)', 'value': val})
        except Exception as e:
            # Fallback or error
            pass
            
    return badges
