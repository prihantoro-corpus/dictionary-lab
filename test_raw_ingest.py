
import os
import sys
import duckdb
import shutil

# Mock Streamlit session state for sidebar calls if needed, but here we call ingest directly
# Add current dir to path
sys.path.append(os.getcwd())

from pipeline import ingest, indexing

TEST_FILE = "test_raw_ingest.txt"
TEST_CORPUS = "test_raw_ingest"
DB_PATH = "dictionary_lab.duckdb"

def setup_test_file():
    content = """this <sample att="val"> is </sample> sentence

this DET this
<sample att="val">
is COP be
</sample>
sentence NN sentence
"""
    with open(TEST_FILE, "w", encoding="utf-8") as f:
        f.write(content)

def verify_results():
    conn = duckdb.connect(DB_PATH, read_only=True)
    try:
        # Check alignment of tags
        print("Checking tokens...")
        res = conn.execute(f"SELECT token, tag, lemma, metadata FROM tokens WHERE corpus='{TEST_CORPUS}' ORDER BY id").fetchall()
        for r in res:
            print(f"Token: {r[0]}, Tag: {r[1]}, Lemma: {r[2]}")
            
    finally:
        conn.close()

def main():
    setup_test_file()
    print("Test file created.")
    
    parser = ingest.CorpusParser()
    
    # We use 'other' to avoid downloading/loading Stanza models in this quick test unless user has them
    # For thoroughness, let's try 'English' if we think it might work, 
    # but 'other' is safer for a quick checks of the SPLITTING logic first.
    # Actually, let's test the splitting logic primarily. 'other' uses the whitespace fallback which 
    # is enough to test the XML isolation.
    
    print("Running process_file (lang='other')...")
    parser.process_file(TEST_FILE, TEST_CORPUS, lang_code='Other')
    
    verify_results()
    
    # Clean up
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

if __name__ == "__main__":
    main()
