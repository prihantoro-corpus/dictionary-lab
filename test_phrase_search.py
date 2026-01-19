import duckdb
import os
import sys

# Mocking the pipeline.indexing.get_connection
import pipeline.indexing

TEST_DB = "test_phrase.duckdb"

def mock_get_connection(allow_fallback=True):
    # Retrieve the connection from the test database
    if os.path.exists(TEST_DB):
         conn = duckdb.connect(TEST_DB, read_only=False)
         return conn, False
    return duckdb.connect(TEST_DB), False

pipeline.indexing.get_connection = mock_get_connection

from pipeline import ingest
from stats import frequency

def setup_test_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    # Create tables
    conn, _ = mock_get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER,
            token VARCHAR,
            tag VARCHAR,
            lemma VARCHAR,
            corpus VARCHAR,
            metadata VARCHAR,
            file_id VARCHAR
        )
    """)
    conn.close()

    # Create a dummy corpus file
    with open("test_corpus.txt", "w", encoding="utf-8") as f:
        # Case 1: Adjacent (Should match)
        f.write("central\tJJ\tcentral\n")
        f.write("bank\tNN\tbank\n")
        
        # Case 2: Punctuation (Should NOT match strict)
        f.write("central\tJJ\tcentral\n")
        f.write(",\t,\t,\n")
        f.write("bank\tNN\tbank\n")
        
        # Case 3: Sentence boundary (Should NOT match strict)
        f.write("central\tJJ\tcentral\n")
        f.write(".\t.\t.\n")
        f.write("Bank\tNN\tbank\n")
        
    # Ingest
    parser = ingest.CorpusParser()
    parser.ingest_file("test_corpus.txt")

def test_search():
    print("Testing 'central bank' search...")
    
    # Test 1: skip_punct=True (Default)
    res_relaxed = frequency.get_phrase_metrics("central bank", skip_punct=True)
    print(f"Relaxed Result: {res_relaxed}")
    
    if res_relaxed['frequency'] == 3:
        print("PASS: Relaxed search found 3 occurrences (Adjacent, Comma, Period).")
    else:
        print(f"FAIL: Relaxed search expected 3, got {res_relaxed['frequency']}")

    # Test 2: skip_punct=False
    res_strict = frequency.get_phrase_metrics("central bank", skip_punct=False)
    print(f"Strict Result: {res_strict}")
    
    if res_strict['frequency'] == 1:
        print("PASS: Strict search found exactly 1 occurrence.")
    else:
        print(f"FAIL: Strict search expected 1, got {res_strict['frequency']}")

if __name__ == "__main__":
    setup_test_db()
    test_search()
    
    # Cleanup
    if os.path.exists(TEST_DB):
        try:
             os.remove(TEST_DB)
        except: pass
    if os.path.exists("test_corpus.txt"):
        os.remove("test_corpus.txt")
