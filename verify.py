from pipeline import indexing, ingest, search
from stats import frequency, collocation, kwic
from wordlist import manager
import os
import shutil

CORPORA_DIR = r"c:\Users\priha\Documents\dictionary-lab\corpora"

def run_verify():
    print("Testing Search Helpers...")
    # Lemma
    # In sample_corpus.txt, we have "apples" -> "apple" if we had it. 
    # Let's check a word from BPPT if ingested, or sample.
    # Sample has "apple" -> lemma "apple".
    
    lemma = search.get_lemma("apple")
    print(f"Lemma for 'apple': {lemma}")
    
    # Forms
    forms = search.get_forms_by_lemma("apple")
    print(f"Forms for lemma 'apple': {forms}")
    
    # POS
    pos = search.get_pos_tags("apple")
    print(f"POS tags for 'apple': {pos}")
    
    # Wordlist / CEFR
    badges = manager.check_token("apple")
    print(f"Badges for 'apple': {badges}")
    if any(b['name'] == 'CEFR' for b in badges):
        print("PASS CEFR Detection")
    else:
        print("FAIL CEFR Detection (Check if cefrpy is working)")

    # Related Words
    related = search.get_related_words("apple")
    print(f"Related words to 'apple': {related}")

    print("\nTesting KWIC Helpers...")
    kwic_res = kwic.get_kwic_lines("apple", limit=5)
    print(f"KWIC lines for 'apple': {len(kwic_res)}")
    
    col_kwic = kwic.get_collocate_kwic("apple", "eat", limit=5)
    print(f"Collocate KWIC (apple+eat): {len(col_kwic)}")
    if len(col_kwic) > 0:
        print("PASS Collocate KWIC")
    else:
        # Check sample_corpus.txt to see if apple and eat are close
        print("FAIL Collocate KWIC (Check co-occurrence in corpus)")

    print("\nTesting N-Grams (New Structure)...")
    # This should now work without exception even with filters (passed as params to get_ngrams, though verify script might default params)
    # The verify script calls get_ngrams("apple") -> params=().
    ngrams = collocation.get_ngrams("apple")
    print("Keys in ngrams:", list(ngrams.keys()))
    if 'bi_search_word' in ngrams:
        print("PASS Structure")
    else:
        print("FAIL Structure")
        
    print("\nTesting Collocate Filters (Advanced)...")
    # Test 1: Wildcard *pp* (should find apple/apples if self-match allowed/present nearby)
    collocs_wc = collocation.get_collocates("apple", allowed_words=["*pp*"])
    print(f"Wildcard *pp*: {collocs_wc}")
    
    # Test 2: Regex (app|eat)
    collocs_re = collocation.get_collocates("apple", allowed_words=["(app|eat)"])
    print(f"Regex (app|eat): {collocs_re}")
    
    # Test 3: Skip Punctuation (default True)
    # Hard to test without punctuation in sample. But we can ensure it runs.
    collocs_punct = collocation.get_collocates("apple", skip_punct=True)
    print(f"Skip Punct True: Runs OK")
    
    print("\nTesting N-Grams (Filters)...")
    # Check if stop words removal works (hide 'is')
    ngrams_sw = collocation.get_ngrams("apple", stop_words=["is"])
    # If 'apple is' was a bigram, it should now be gone from 'bi_search_word'
    print("N-Grams with SW: Runs OK")
    
    print("\nTesting Metadata Extraction...")
    from layout import sidebar
    # Need to pass corpora list now or None
    # Passing None to test "all"
    keys = sidebar.get_metadata_keys(corpora=None)
    print(f"Metadata Keys (All): {keys}")
    if keys:
        vals = sidebar.get_metadata_values(keys[0], corpora=None)
        print(f"Values for {keys[0]} (All): {vals}")
        
    print("Done.")

if __name__ == "__main__":
    run_verify()
