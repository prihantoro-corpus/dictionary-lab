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
                    # Update current metadata state (merge)
                    current_metadata.update(data)
                    # If it's a closing tag like </text>, maybe we should clear some metadata?
                    # For now, assuming standard opening tags update context. 
                    # Complex nesting might require a stack, but user req says "xml tags will be used to read attribute values".
                    # Usually "segment" attributes like id, speaker, etc. are consistent within the segment.
                    
                elif type_ == 'token':
                    current_id += 1
                    # Prepare row
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
        conn.close()

    def _bulk_insert(self, conn, data):
        # Using Pandas for easy insertion into DuckDB
        df = pd.DataFrame(data)
        # duckdb.appender or convert to SQL
        # df.to_sql is slow. DuckDB 'INSERT INTO table SELECT * FROM df' is fast.
        conn.execute("INSERT INTO tokens SELECT * FROM df")

