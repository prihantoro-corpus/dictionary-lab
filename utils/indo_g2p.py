"""
Indonesian Grapheme-to-Phoneme (G2P) Converter
Heuristic, rule-based transcription to IPA.
"""

import re

VOWELS = "aiueoəɛɔ"

# Default exception lexicon for 'e' (can be extended)
DEFAULT_LEX_E = {
    "emas": "əmas",
    "merah": "mɛrah",
    "berak": "bɛrak",
    "enak": "enak",
    "empat": "əmpat",
    "enam": "ənam",
}

def handle_o(text):
    """Handle o pronunciation: o before consonant -> ɔ"""
    text = re.sub(r"o(?=[bcdfghjklmnpqrstvwxyz])", "ɔ", text)
    text = re.sub(r"o(?=[aiueo])", "o", text)
    text = re.sub(r"o\b", "o", text)
    return text

def handle_e_word(word, lex_e=None):
    """Handle e pronunciation with exception lexicon"""
    if lex_e is None:
        lex_e = DEFAULT_LEX_E
    
    if word in lex_e:
        return lex_e[word]
    
    w = word
    
    # Common prefixes -> schwa
    w = re.sub(r"^(be|me|pe|ke|se|te)(?=[bcdfghjklmnpqrstvwxyz])",
               lambda m: m.group(1)[0] + "ə", w)
    
    # Heavy/expressive tendency -> ɛ
    w = re.sub(r"e(?=[rktp])", "ɛ", w)
    
    # Word-initial e + consonant -> e
    w = re.sub(r"^e(?=[bcdfghjklmnpqrstvwxyz])", "e", w)
    
    # Remaining e -> schwa
    w = re.sub(r"e", "ə", w)
    
    return w

# Core G2P rules
RULES = [
    # Diphthongs
    (r"ai", "ai̯"),
    (r"au", "au̯"),
    (r"oi", "oi̯"),
    
    # Digraphs
    (r"ng", "ŋ"),
    (r"ny", "ɲ"),
    (r"sy", "ʃ"),
    (r"kh", "x"),
    (r"dz", "dz"),
    
    # Letters
    (r"c", "tʃ"),
    (r"j", "dʒ"),
    (r"y", "j"),
    (r"x", "ks"),
    (r"q", "k"),
    
    # Consonants
    (r"b", "b"),
    (r"d", "d"),
    (r"f", "f"),
    (r"g", "g"),
    (r"h", "h"),
    (r"k", "k"),
    (r"l", "l"),
    (r"m", "m"),
    (r"n", "n"),
    (r"p", "p"),
    (r"r", "r"),
    (r"s", "s"),
    (r"t", "t"),
    (r"v", "v"),
    (r"w", "w"),
    (r"z", "z"),
]

def handle_final_k(ipa):
    """Convert final /k/ to glottal stop"""
    return re.sub(r"k\b", "ʔ", ipa)

def syllabify_onset_max(word):
    """
    Onset-maximising heuristic for Indonesian:
    - V.V -> split
    - VCV -> split before C (C goes to onset)
    - VCCV -> split C.C
    """
    chars = list(word)
    syllables = []
    current = ""
    i = 0
    
    while i < len(chars):
        c = chars[i]
        current += c
        
        if c in VOWELS:
            if i + 1 < len(chars):
                nxt = chars[i + 1]
                
                # V V -> boundary
                if nxt in VOWELS:
                    syllables.append(current)
                    current = ""
                
                # V C V -> boundary before C
                elif nxt not in VOWELS and i + 2 < len(chars) and chars[i + 2] in VOWELS:
                    syllables.append(current)
                    current = ""
                
                # V C C V -> split C.C
                elif (
                    nxt not in VOWELS
                    and i + 2 < len(chars)
                    and chars[i + 2] not in VOWELS
                    and i + 3 < len(chars)
                    and chars[i + 3] in VOWELS
                ):
                    current += nxt
                    syllables.append(current)
                    current = ""
                    i += 1  # consume extra consonant
        
        i += 1
    
    if current:
        syllables.append(current)
    
    return ".".join(syllables)

def convert(word, syllabify=False):
    """
    Convert Indonesian word to IPA transcription.
    
    Args:
        word: Indonesian word to convert
        syllabify: If True, add syllable boundaries
    
    Returns:
        IPA transcription string
    """
    if not word or not isinstance(word, str):
        return word
    
    w = word.lower()
    
    # Handle e and o
    w = handle_e_word(w, DEFAULT_LEX_E)
    w = handle_o(w)
    
    # Apply all G2P rules
    ipa = w
    for pattern, repl in RULES:
        ipa = re.sub(pattern, repl, ipa)
    
    # Final k -> glottal stop
    ipa = handle_final_k(ipa)
    
    # Optional syllabification
    if syllabify:
        ipa = syllabify_onset_max(ipa)
    
    return ipa
