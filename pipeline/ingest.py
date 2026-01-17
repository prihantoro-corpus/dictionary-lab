import re
import duckdb
import pandas as pd
import json
from .indexing import get_connection

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
            # It's a token line
            parts = line.split('\t')
            if len(parts) >= 3:
                return 'token', {'token': parts[0], 'tag': parts[1], 'lemma': parts[2]}
            elif len(parts) == 1:
                 # robust fallback
                 return 'token', {'token': parts[0], 'tag': 'UNK', 'lemma': parts[0]}
            else:
                 return 'token', {'token': parts[0], 'tag': parts[1] if len(parts)>1 else 'UNK', 'lemma': parts[2] if len(parts)>2 else parts[0]}

    def ingest_file(self, filepath):
        """Simplifies ingestion by using filename as corpus name."""
        import os
        corpus_name = os.path.splitext(os.path.basename(filepath))[0]
        self.process_file(filepath, corpus_name)

    def process_file(self, filepath, corpus_name):
        conn = get_connection()
        try:
            # Get current max ID to continue sequence
            try:
                 res = conn.execute("SELECT MAX(id) FROM tokens").fetchone()
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
            conn.close()

    def _bulk_insert(self, conn, data):
        if not data: return
        try:
            df = pd.DataFrame(data)
            conn.execute("INSERT INTO tokens SELECT * FROM df")
        except Exception as e:
            print(f"Bulk insert failed: {e}")
            raise e

