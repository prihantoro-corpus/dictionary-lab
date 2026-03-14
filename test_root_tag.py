
import os
import sys
import duckdb
import json
import shutil

# Add current dir to path
sys.path.append(os.getcwd())

# IMPORTANT: Import ingest after verifying paths, or assume it works
from pipeline import ingest, indexing

TEST_FILE = "test_root_tag.txt"
TEST_CORPUS = "test_root_tag"
TEST_DB = "test_root.duckdb"

def setup_test_file():
    # Simple content
    content = "This is a test sentence."
    with open(TEST_FILE, "w", encoding="utf-8") as f:
        f.write(content)

def verify_results():
    conn = duckdb.connect(TEST_DB, read_only=True)
    try:
        print("Checking tokens for metadata...")
        res = conn.execute(f"SELECT token, metadata FROM tokens WHERE corpus='{TEST_CORPUS}' LIMIT 1").fetchone()
        if res:
            token, metadata_json = res
            metadata = json.loads(metadata_json)
            print(f"Token: {token}")
            print(f"Metadata: {metadata}")
            
            # Use 'test_root_tag' as the expected attribute value because 
            # filename is test_root_tag.txt -> splitext -> test_root_tag
            expected_attr = "test_root_tag"
            if metadata.get("attribute") == expected_attr:
                print("SUCCESS: Root attribute found correctly.")
            else:
                print(f"FAILURE: Expected attribute '{expected_attr}', found '{metadata.get('attribute')}'")
        else:
            print("FAILURE: No tokens found.")
            
    finally:
        conn.close()

def main():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    setup_test_file()
    
    # Initialize DB (create schema)
    # We do this manually as we are bypassing the app's full init flow
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
    
    # Patch DB Path for ingest
    indexing.DB_PATH = TEST_DB
    
    parser = ingest.CorpusParser()
    
    # Using 'Other' (whitespace) to avoid Stanza model reqs for this quick check
    print("Processing file (Raw mode, lang='Other')...")
    parser.process_file(TEST_FILE, TEST_CORPUS, lang_code='Other')
    
    verify_results()
    
    # Clean up
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

if __name__ == "__main__":
    main()
