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
    
    print("\nTesting N-Grams (New Structure)...")
    ngrams = collocation.get_ngrams("apple")
    print("Keys in ngrams:", list(ngrams.keys()))
    if 'bi_search_word' in ngrams:
        print("PASS Structure")
    else:
        print("FAIL Structure")
        
    print("\nTesting Collocate Filters...")
    # Filter for 'eat' only
    collocs = collocation.get_collocates("apple", allowed_words=["eat"])
    print(f"Collocates for 'apple' (allowed=['eat']): {collocs}")
    
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
