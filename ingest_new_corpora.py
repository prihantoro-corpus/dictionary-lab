from pipeline import ingest, indexing
import os

CORPORA_DIR = "corpora"

def run():
    parser = ingest.CorpusParser()
    
    # Ingest BPPT
    path_bppt = os.path.join(CORPORA_DIR, "EN-BPPT-tagged.xml")
    if os.path.exists(path_bppt):
        print(f"Ingesting {path_bppt}...")
        parser.process_file(path_bppt, "BPPT")
    else:
        print(f"File not found: {path_bppt}")

    # Ingest KOSLAT
    path_koslat = os.path.join(CORPORA_DIR, "KOSLAT-full.xml")
    if os.path.exists(path_koslat):
        print(f"Ingesting {path_koslat}...")
        parser.process_file(path_koslat, "KOSLAT")
    else:
        print(f"File not found: {path_koslat}")

    print("Ingestion complete.")
    
    # Quick count check
    conn, is_shared = indexing.get_connection()
    res = indexing.safe_execute(conn, "SELECT corpus, COUNT(*) FROM tokens GROUP BY corpus").fetchall()
    print("Corpus stats:")
    for r in res:
        print(f" - {r[0]}: {r[1]} tokens")
    if not is_shared:
        conn.close()

if __name__ == "__main__":
    run()
