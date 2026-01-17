from pipeline import indexing, ingest, search
from stats import frequency, collocation, kwic
from wordlist import manager
import os

def run_verify():
    print("Resetting DB...")
    indexing.reset_db()
    
    print("Ingesting Corpus...")
    parser = ingest.CorpusParser()
    parser.process_file(r"c:\Users\priha\Documents\dictionary-lab\corpora\sample_corpus.txt", "SAMPLE")
    
    print("Testing Search (Exact)...")
    res = search.search_exact("apple")
    print(f"Found 'apple': {len(res)} times")
    if len(res) == 2: print("PASS")
    else: print("FAIL")
    
    print("Testing Stats...")
    metrics = frequency.get_metrics("apple")
    print(f"Metrics for 'apple': {metrics}")
    # Total tokens = 15. Count = 2. PMW = (2/15)*1M = 133333.33
    if metrics['frequency'] == 2: print("PASS")
    else: print("FAIL")
    
    print("Testing Wordlist...")
    badges = manager.check_token("apple")
    print(f"Badges for 'apple': {badges}")
    if any(b['name'] == 'BASIC_ENGLISH' for b in badges): print("PASS")
    else: print("FAIL")
    
    print("Testing KWIC...")
    lines = kwic.get_kwic_lines("apple", window=2)
    for line in lines:
        print(f"KWIC: {line['left']} [{line['node']}] {line['right']}")
        
    print("Testing IPA...")
    try:
        import eng_to_ipa as ipa
        pron = ipa.convert("apple")
        try:
            print(f"IPA for 'apple': {pron}")
        except UnicodeEncodeError:
            print(f"IPA for 'apple': {pron.encode('utf-8')}") # Fallback for Windows console
        if pron: print("PASS")
        else: print("FAIL (Empty)")
    except ImportError:
        print("FAIL (ImportError)")
        
    print("Done.")

if __name__ == "__main__":
    run_verify()
