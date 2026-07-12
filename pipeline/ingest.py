import re
import duckdb
import pandas as pd
import json
import os
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
            # It's a tag, extract name and attributes
            tag_name_match = re.search(r'^<(/?[a-zA-Z0-9]+)', line)
            tag_name = tag_name_match.group(1).lower() if tag_name_match else ""
            attrs = dict(self.attr_pattern.findall(line))
            return 'metadata', (tag_name, attrs)
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
                 return 'token', {'token': parts[0], 'tag': 'NA', 'lemma': parts[0]}

    def ingest_file(self, filepath):
        """Simplifies ingestion by using filename as corpus name."""
        import os
        corpus_name = os.path.splitext(os.path.basename(filepath))[0]
        self.process_file(filepath, corpus_name)

    def process_file(self, filepath, corpus_name, lang_code=None, progress_callback=None):
        conn, is_shared = get_connection(allow_fallback=False)
        try:
            # 1. Detect Format
            is_vertical = True
            with open(filepath, 'r', encoding='utf-8', errors='replace') as test_f:
                # Check first few non-empty lines for tabs
                lines_checked = 0
                for line in test_f:
                    stripped = line.strip()
                    if stripped:
                        # A vertical tag should be just the tag, e.g., <doc id="1">
                        # Lines like <u ...>text</u> have the first '>' not at the end.
                        is_single_tag = stripped.startswith('<') and stripped.endswith('>') and stripped.find('>') == len(stripped) - 1
                        if '\t' not in stripped and not is_single_tag:
                            # Found a line that is NOT a tag and has NO tabs -> likely raw text
                            is_vertical = False
                            break
                        lines_checked += 1
                        if lines_checked > 10: break
            
            if not is_vertical:
                if progress_callback: progress_callback(0.01, f"Initializing SpaCy for {lang_code}...")
                print(f"Detected RAW text for {filepath}. Processing with Stanza (Language: {lang_code})...")
                self.process_raw_text(filepath, corpus_name, lang_code, conn, progress_callback=progress_callback)
                return

            # --- EXISTING VERTICAL PROCESSING ---
            print(f"Clearing existing data for corpus '{corpus_name}'...")
            safe_execute(conn, "DELETE FROM tokens WHERE corpus = ?", (corpus_name,))
            
            # Get current max ID to continue sequence
            # Get current max ID to continue sequence
            try:
                 res = safe_execute(conn, "SELECT MAX(id) FROM tokens").fetchone()
                 current_id = res[0] if res[0] is not None else 0
            except:
                current_id = 0

            # --- ROOT TAG INJECTION ---
            # <root attribute="filename">
            # We treat this as initial metadata that applies to the whole file
            root_attr_value = os.path.splitext(os.path.basename(filepath))[0]
            current_metadata = {"attribute": root_attr_value}
            
            start_id = current_id
            current_sentence_id = 0
            current_doc_id = 0
            current_sentence_num = 0
            batch_data = []
            batch_size = 10000
            
            print(f"Processing {filepath} (Vertical)...")
            
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    type_, data = self.parse_line(line)
                    
                    if type_ == 'metadata':
                        tag_name, attrs = data
                        if tag_name == 's' or tag_name == 'sentence':
                             current_sentence_id += 1
                             current_sentence_num = int(attrs.get('n', 0))
                        elif tag_name.startswith('doc'):
                             current_doc_id += 1
                        current_metadata.update(attrs)
                    elif type_ == 'token':
                        current_id += 1
                        row = {
                            'id': current_id,
                            'token': data['token'],
                            'tag': data['tag'],
                            'lemma': data['lemma'],
                            'corpus': corpus_name,
                            'metadata': json.dumps(current_metadata),
                            'file_id': filepath,
                            'sentence_id': current_sentence_id,
                            'doc_id': current_doc_id,
                            'sentence_num': current_sentence_num
                        }
                        batch_data.append(row)
                    
                    if len(batch_data) >= batch_size:
                        self._bulk_insert(conn, batch_data)
                        batch_data = []
            
            if batch_data:
                self._bulk_insert(conn, batch_data)
            
            print(f"Finished processing {filepath}. Total tokens: {current_id - start_id}")
        except Exception as e:
            print(f"CRITICAL ERROR during ingestion: {e}")
            raise e
        finally:
            if not is_shared:
                conn.close()

    def process_raw_text(self, filepath, corpus_name, lang_code, conn, progress_callback=None):
        import spacy
        import os
        from spacy.cli import download
        
        # SpaCy Setup
        spacy_model = 'en_core_web_sm' # Default
        if lang_code:
            lang_map = {
                'English': 'en_core_web_sm', 
                'Chinese': 'zh_core_web_sm', 
                'Japanese': 'ja_core_news_sm', 
                'Korean': 'ko_core_news_sm', 
                # Spanish, French, German, etc. could be added. 
                # Indonesian/Arabic/Javanese don't have official lightweight core models in Spacy out-of-the-box,
                # so we will use the multi-language model (xx_ent_wiki_sm) as a fallback.
                'Indonesian': 'xx_ent_wiki_sm',
                'Arabic': 'xx_ent_wiki_sm',
                'Javanese': 'xx_ent_wiki_sm',
                'Other': 'xx_ent_wiki_sm'
            }
            spacy_model = lang_map.get(lang_code, 'xx_ent_wiki_sm')
        
        nlp = None
        if spacy_model:
            try:
                # Try to load, if fails, download
                if not spacy.util.is_package(spacy_model):
                    print(f"Downloading SpaCy model {spacy_model}...")
                    download(spacy_model)
                nlp = spacy.load(spacy_model, disable=['ner', 'parser', 'textcat'])
                if spacy_model.startswith('xx_'):
                    nlp.add_pipe('sentencizer') # Multi-lang needs sentencizer
            except Exception as e:
                print(f"Failed to load SpaCy model {spacy_model}: {e}. Falling back to whitespace.")
                nlp = None

        
        # Clear existing
        print(f"Clearing existing data for corpus '{corpus_name}'...")
        safe_execute(conn, "DELETE FROM tokens WHERE corpus = ?", (corpus_name,))
        
        try:
             res = safe_execute(conn, "SELECT MAX(id) FROM tokens").fetchone()
             current_id = res[0] if res[0] is not None else 0
        except:
            current_id = 0
            
        start_id = current_id

        # --- ROOT TAG INJECTION ---
        root_attr_value = os.path.splitext(os.path.basename(filepath))[0]
        current_metadata = {"attribute": root_attr_value}
        
        current_sentence_id = 0
        current_doc_id = 0
        current_sentence_num = 0
        batch_data = []
        batch_size = 10000

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        # Split by XML tags
        # Captures tags like <...> as separate items in the list due to parens in split regex
        parts = re.split(r'(<[^>]+>)', content)
        
        for part in parts:
            if not part: continue
            
            # Check if it is a tag
            if part.startswith('<') and part.endswith('>'):
                # Handle Metadata / Tag
                # Requirement: Indent tag hard left (remove whitespace around it, keep internal structure)
                clean_tag = part.strip() 
                
                # Check if it's a structural tag we track (like <s>, <doc>)
                # Use existing parse_line logic for metadata extraction
                type_, data = self.parse_line(clean_tag)
                if type_ == 'metadata':
                    tag_name, attrs = data
                    if tag_name == 's' or tag_name == 'sentence':
                            current_sentence_id += 1
                    elif tag_name.startswith('doc'):
                            current_doc_id += 1
                    # Merge metadata (simple approach: update current state)
                    current_metadata.update(attrs)
                    
                # NOTE: In our DB structure, tags aren't stored as rows unless they are tokens.
                # The user requirement "indent tag hard left" suggests they care about the *XML output* 
                # later or how it's treated. For Ingestion, we just consume it as metadata.
                # If the user means "treat as a token but untokenized", that's different.
                # Assuming standard behavior: Tags -> Metadata state updates.
                continue
            
            # Process Text Content
            text_segment = part.strip()
            if not text_segment: continue
            
            # SENTENCE SPLITTING FIRST (before tokenization)
            # Use user's regex pattern: /.*?[\.\!\?](?=\s|\n|$)/s
            # Python equivalent with DOTALL flag
            sentence_pattern = r'.*?[\.\!\?](?=\s|\n|$)'
            sentences = re.findall(sentence_pattern, text_segment, re.DOTALL)
            
            # If no sentences found (no punctuation), treat whole segment as one sentence
            if not sentences:
                sentences = [text_segment]
            
            # Progress reporting logic
            total_sentences = len(sentences)
            
            # Process each sentence
            for idx, sentence_text in enumerate(sentences):
                if progress_callback and idx % max(1, total_sentences // 20) == 0:
                    fraction = min(0.99, idx / total_sentences)
                    progress_callback(fraction, f"SpaCy NLP Parsing: Sentence {idx}/{total_sentences}")
                    
                sentence_text = sentence_text.strip()
                if not sentence_text: continue
                
                # Increment sentence counters
                current_sentence_id += 1
                current_sentence_num += 1
                
                tokens_to_add = []
                
                if nlp:
                    # SpaCy Processing (per sentence)
                    try:
                        doc = nlp(sentence_text)
                        for word in doc:
                            tokens_to_add.append({
                                'token': word.text,
                                'tag': word.pos_ if word.pos_ else 'NA',
                                'lemma': word.lemma_ if word.lemma_ else word.text
                            })
                    except Exception as e:
                        print(f"SpaCy processing failed: {e}. Using fallback.")
                        # Fallback to whitespace
                        words = sentence_text.split()
                        for w in words:
                            tokens_to_add.append({
                                'token': w,
                                'tag': 'NA',
                                'lemma': w
                            })
                else:
                    # Whitespace Fallback
                    words = sentence_text.split()
                    for w in words:
                        tokens_to_add.append({
                            'token': w,
                            'tag': 'NA',
                            'lemma': w
                        })
                
                # Add to Batch
                for t in tokens_to_add:
                    current_id += 1
                    row = {
                        'id': current_id,
                        'token': t['token'],
                        'tag': t['tag'],
                        'lemma': t['lemma'],
                        'corpus': corpus_name,
                        'metadata': json.dumps(current_metadata),
                        'file_id': filepath,
                        'sentence_id': current_sentence_id,
                        'doc_id': current_doc_id,
                        'sentence_num': current_sentence_num
                    }
                    batch_data.append(row)
                    if len(batch_data) >= batch_size:
                        self._bulk_insert(conn, batch_data)
                        batch_data = []

        if batch_data:
            self._bulk_insert(conn, batch_data)
        
        print(f"Finished processing RAW {filepath}. Total tokens: {current_id - start_id}")

    def _bulk_insert(self, conn, data):
        try:
            values = [(d['id'], d['token'], d['tag'], d['lemma'], d['corpus'], d['metadata'], d['file_id'], d['sentence_id'], d['doc_id'], d['sentence_num']) for d in data]
            conn.executemany("INSERT INTO tokens (id, token, tag, lemma, corpus, metadata, file_id, sentence_id, doc_id, sentence_num) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
        except Exception as e:
            print(f"Bulk insert failed: {e}")
            raise e
