import duckdb
import os
import sys

# Mocking the pipeline.indexing.get_connection
import pipeline.indexing

TEST_DB = "test_collocate_ex.duckdb"

def mock_get_connection(allow_fallback=True):
    if os.path.exists(TEST_DB):
         conn = duckdb.connect(TEST_DB, read_only=False)
         return conn, False
    return duckdb.connect(TEST_DB), False

pipeline.indexing.get_connection = mock_get_connection

from pipeline import ingest
from stats import kwic

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
    # We want: ... word1 word2 ... collocate ...
    with open("test_corpus.txt", "w", encoding="utf-8") as f:
        # Match 1: central bank ... policy
        f.write("the\tDT\tthe\n")
        f.write("central\tJJ\tcentral\n")
        f.write("bank\tNN\tbank\n")
        f.write("announced\tVBD\tannounce\n")
        f.write("a\tDT\ta\n")
        f.write("new\tJJ\tnew\n")
        f.write("policy\tNN\tpolicy\n")
        f.write(".\t.\t.\n")
        
        # Match 2: central bank ... (no policy)
        f.write("another\tDT\tanother\n")
        f.write("central\tJJ\tcentral\n")
        f.write("bank\tNN\tbank\n")
        f.write("is\tVBZ\tbe\n")
        f.write("here\tRB\there\n")
        f.write(".\t.\t.\n")
        
    # Ingest
    parser = ingest.CorpusParser()
    parser.ingest_file("test_corpus.txt")

def test_collocate_ex():
    print("Testing 'central bank' with collocate 'policy'...")
    res = kwic.get_phrase_collocate_kwic("central bank", "policy", window=10)
    print(f"Result count: {len(res)}")
    for r in res:
        print(f"Match: {' '.join(r['left'])} | {r['node']} | {' '.join(r['right'])} (Col: {r['col_token']})")
    
    if len(res) == 1:
        print("PASS: Found exactly 1 occurrence containing both phrase and collocate.")
    else:
        print(f"FAIL: Expected 1, got {len(res)}")

if __name__ == "__main__":
    setup_test_db()
    test_collocate_ex()
    
    # Cleanup
    if os.path.exists(TEST_DB):
        try:
             os.remove(TEST_DB)
        except: pass
    if os.path.exists("test_corpus.txt"):
        os.remove("test_corpus.txt")
