
import os
import sys
import duckdb
import shutil
import json

# Add current dir to path
sys.path.append(os.getcwd())

# IMPORTANT: Import ingest after verifying paths, or assume it works
from pipeline import ingest

TEST_FILE = "test_raw_sentence.txt"
TEST_CORPUS = "test_raw_sentence"
# Use a temp DB to avoid lock issues with the main app
TEST_DB = "test_ingest.duckdb"

def setup_test_file():
    # Test case: 
    # 1. Existing XML tag with indentation (should be stripped/isolated)
    # 2. Multiple sentences (should be split and have diff sentence_ids)
    content = """
    <doc id="1">
This is sentence one. This is sentence two.
    <sample att="val">
is
    </sample>
sentence three.
"""
    with open(TEST_FILE, "w", encoding="utf-8") as f:
        f.write(content)

def verify_results():
    conn = duckdb.connect(TEST_DB, read_only=True)
    try:
        print("Checking tokens...")
        res = conn.execute(f"SELECT token, tag, lemma, sentence_id, metadata FROM tokens WHERE corpus='{TEST_CORPUS}' ORDER BY id").fetchall()
        
        last_sid = -1
        for r in res:
            token, tag, lemma, sid, meta = r
            print(f"Token: '{token}', Tag: {tag}, SID: {sid}")
            
            # Check if metadata captured the tags
            # meta is JSON string
            # We can't easily see the "event" of the tag unless we check if side effects happened (like doc_id or sentence_id incrementing unexpectedly?)
            # But we can verify "This" (SID X), "This" (SID X+1)
            
    finally:
        conn.close()

def main():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    setup_test_file()
    print("Test file created.")
    
    # Mocking get_connection to use our TEST_DB
    # We need to monkeypatch or modify how ingest gets the connection
    # distinct from the main app's DB.
    # ingest.py imports get_connection from indexing.
    # We can override indexing.DB_PATH before calling process_file?
    
    import pipeline.indexing
    pipeline.indexing.DB_PATH = TEST_DB
    conn = duckdb.connect(TEST_DB, read_only=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id BIGINT,
            token VARCHAR,
            tag VARCHAR,
            lemma VARCHAR,
            corpus VARCHAR,
            metadata JSON,
            file_id VARCHAR,
            sentence_id BIGINT,
            doc_id BIGINT,
            sentence_num BIGINT
        );
    """)
    conn.close()

    print(f"Patched DB_PATH to {pipeline.indexing.DB_PATH}")
    
    parser = ingest.CorpusParser()
    
    # Use 'other' to test splitting logic without needing Stanza models download
    print("Running process_file (lang='other')...")
    parser.process_file(TEST_FILE, TEST_CORPUS, lang_code='Other')
    
    verify_results()
    
    # Clean up
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

if __name__ == "__main__":
    main()
