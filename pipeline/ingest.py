import re
import duckdb
import pandas as pd
import json
from .indexing import get_connection, safe_execute

class CorpusParser:
    def __init__(self):
        # Regex to capture attributes: key="value" or key='value'
        self.attr_pattern = re.compile(r'(\w+)=["\']([^"\']+)["\']')
        self.tag_pattern = re.compile(r'^<.*>$')

    def parse_line(self, line):
        line = line.strip()
        if not line:
            return None, None
        
        # Check for metadata tag
        if line.startswith('<') and line.endswith('>'):
            # It's a tag, extract attributes
            attrs = dict(self.attr_pattern.findall(line))
            return 'metadata', attrs
        else:
            # It's a token line (split by tabs or multiple spaces)
            parts = [p.strip() for p in re.split(r'\t+', line) if p.strip()]
            if not parts:
                return None, None
                
            if len(parts) >= 3:
                return 'token', {'token': parts[0], 'tag': parts[1], 'lemma': parts[2]}
            elif len(parts) == 2:
                 return 'token', {'token': parts[0], 'tag': parts[1], 'lemma': parts[0]}
            else:
                 return 'token', {'token': parts[0], 'tag': 'UNK', 'lemma': parts[0]}

    def ingest_file(self, filepath):
        """Simplifies ingestion by using filename as corpus name."""
        import os
        corpus_name = os.path.splitext(os.path.basename(filepath))[0]
        self.process_file(filepath, corpus_name)

    def process_file(self, filepath, corpus_name):
        conn, is_shared = get_connection()
        try:
            # Sanity Check: If file looks like a JSON dictionary, warn
            with open(filepath, 'r', encoding='utf-8', errors='replace') as test_f:
                head = test_f.read(100).strip()
                if head.startswith('{') or head.startswith('['):
                    print("WARNING: This file looks like JSON. Are you sure it's a corpus file (vertical text)?")

            # Idempotency: Remove existing data for this corpus name if it exists
            print(f"Clearing existing data for corpus '{corpus_name}'...")
            safe_execute(conn, "DELETE FROM tokens WHERE corpus = ?", (corpus_name,))
            
            # Get current max ID to continue sequence
            try:
                 res = safe_execute(conn, "SELECT MAX(id) FROM tokens").fetchone()
                 current_id = res[0] if res[0] is not None else 0
            except:
                current_id = 0

            current_metadata = {}
            batch_data = []
            batch_size = 50000
            
            print(f"Processing {filepath}...")
            
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    type_, data = self.parse_line(line)
                    
                    if type_ == 'metadata':
                        current_metadata.update(data)
                    elif type_ == 'token':
                        current_id += 1
                        row = {
                            'id': current_id,
                            'token': data['token'],
                            'tag': data['tag'],
                            'lemma': data['lemma'],
                            'corpus': corpus_name,
                            'metadata': json.dumps(current_metadata),
                            'file_id': filepath
                        }
                        batch_data.append(row)
                    
                    if len(batch_data) >= batch_size:
                        self._bulk_insert(conn, batch_data)
                        batch_data = []
            
            if batch_data:
                self._bulk_insert(conn, batch_data)
            
            print(f"Finished processing {filepath}. Total tokens: {current_id}")
        except Exception as e:
            print(f"CRITICAL ERROR during ingestion: {e}")
            raise e
        finally:
            if not is_shared:
                conn.close()

    def _bulk_insert(self, conn, data):
        if not data: return
        try:
            df = pd.DataFrame(data)
            # Register the dataframe with a fixed name to avoid scoping issues in safe_execute
            conn.register("batch_df", df)
            safe_execute(conn, "INSERT INTO tokens (id, token, tag, lemma, corpus, metadata, file_id) SELECT id, token, tag, lemma, corpus, metadata, file_id FROM batch_df")
            conn.unregister("batch_df")
        except Exception as e:
            print(f"Bulk insert failed: {e}")
            raise e

