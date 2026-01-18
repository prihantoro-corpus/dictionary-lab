import os
import csv
import re

# Library checks
try:
    from cefrpy import CEFRAnalyzer
    HAS_CEFR = True
except ImportError:
    HAS_CEFR = False
    print("cefrpy not installed.")

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False
    print("pypdf not installed.")

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    print("python-docx not installed.")

WORDLIST_DIR = "wordlist"
_cache = {}

def load_wordlists():
    """
    Loads known wordlists with specific parsing logic.
    Returns dict: { 'LIST_NAME': { 'word': 'value/rank' } }
    """
    global _cache
    if _cache: return _cache
    
    if not os.path.exists(WORDLIST_DIR):
        os.makedirs(WORDLIST_DIR)
        return {}

    loaded = {}
    
    for filename in os.listdir(WORDLIST_DIR):
        filepath = os.path.join(WORDLIST_DIR, filename)
        if not os.path.isfile(filepath): continue
        
        fname_lower = filename.lower()
        
        try:
            # 1. NGSL (CSV)
            if "ngsl" in fname_lower and fname_lower.endswith(".csv"):
                entries = {}
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader, None) # Skip Header
                    for row in reader:
                        if len(row) >= 2:
                            # Col 0 = Lemma, Col 1 = Rank
                            lemma = row[0].strip().lower()
                            rank = row[1].strip()
                            entries[lemma] = rank
                loaded['NGSL'] = entries

            # 2. GSL (PDF)
            elif "general-service-list" in fname_lower and fname_lower.endswith(".pdf"):
                if HAS_PDF:
                    entries = {}
                    reader = PdfReader(filepath)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    # Split by whitespace
                    tokens = text.split()
                    for t in tokens:
                        # Clean simple punctuation if needed, but usually PDF extract is okay
                        clean_t = re.sub(r'[^a-zA-Z\-\']', '', t).lower()
                        if clean_t:
                            entries[clean_t] = "Yes"
                    loaded['GSL'] = entries

            # 3. AWL (DOCX)
            elif "academic-word-list" in fname_lower and fname_lower.endswith(".docx"):
                if HAS_DOCX:
                    entries = {}
                    doc = Document(filepath)
                    for para in doc.paragraphs:
                        txt = para.text.strip()
                        if not txt: continue
                        # Match "word   number"
                        m = re.search(r'([a-zA-Z\-]+)\s+(\d+)', txt)
                        if m:
                            word = m.group(1).lower()
                            sublist = m.group(2)
                            entries[word] = f"Sublist {sublist}"
                        else:
                            # Fallback if just word
                            clean_t = re.sub(r'[^a-zA-Z\-\']', '', txt).lower()
                            if clean_t: entries[clean_t] = "Yes"
                    loaded['AWL'] = entries
            
            # 4. Basic/Fallback (CSV/TXT) - for legacy "basic_english.csv" etc.
            elif fname_lower == "basic_english.csv":
                 entries = {}
                 with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2:
                            entries[row[0].strip().lower()] = row[1].strip()
                        elif row:
                            entries[row[0].strip().lower()] = "Yes"
                 loaded['BASIC'] = entries

        except Exception as e:
            print(f"Error loading {filename}: {e}")

    _cache = loaded
    return _cache

def check_token(token, lemma=None):
    """
    Checks token against loaded lists.
    Priority:
    1. Check TOKENS (exact match).
    2. Check LEMMA (if provided).
    
    Returns list of dicts: {'name': 'NGSL', 'value': '1'}
    """
    lists = load_wordlists()
    badges = []
    
    t_lower = token.lower().strip()
    l_lower = lemma.lower().strip() if lemma else None
    
    # Check File-based Lists
    for list_name, data in lists.items():
        found_val = None
        
        # 1. Check Token
        if t_lower in data:
            found_val = data[t_lower]
        
        # 2. Check Lemma (if not found in token)
        elif l_lower and l_lower in data:
            found_val = data[l_lower]
            
        if found_val:
            badges.append({'name': list_name, 'value': found_val})
            
    # Check CEFR (Library)
    if HAS_CEFR:
        try:
            analyzer = CEFRAnalyzer()
            # Try token first
            res_dict = analyzer.get_pos_level_dict_for_word(t_lower)
            if not res_dict and l_lower:
                res_dict = analyzer.get_pos_level_dict_for_word(l_lower)
                
            if res_dict:
                # Extract unique level names (A1, B2, etc.)
                levels = sorted(list(set([lvl.name for lvl in res_dict.values()])))
                if levels:
                    badges.append({'name': 'CEFR', 'value': ",".join(levels)})
        except Exception as e:
            pass # CEFR lookup failed safely
            
    return badges
