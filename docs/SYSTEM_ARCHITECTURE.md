# CORTEX Dictionary Lab - System Architecture

## Overview
CORTEX Dictionary Lab is a stream-processing web application built with **Streamlit**. It uses **DuckDB** as a high-performance, in-process analytical SQL engine to handle large linguistic corpora efficiently.

---

## 🌟 Key Features

### Advanced NLP Pipeline
- **Stanza Integration**: Automatic tokenization, POS tagging, and lemmatization for 6+ languages
- **Sentence Detection**: Regex-based sentence boundary detection (`.*?[\.\!\?](?=\s|\n|$)`)
- **XML Tag Preservation**: Structural tags preserved as JSON metadata
- **Dual-mode Processing**: Vertical (pre-tagged) and raw text support

### Corpus Analysis
- **N-gram Extraction**: Bigrams and trigrams with directional analysis
- **Collocate Analysis**: Log-Likelihood scoring with network visualization
- **KWIC Display**: Sentence-level examples with `<s>` tag markers
- **Parallel Corpus**: Aligned bilingual text support
- **Vocabulary Profiler**: Coverage analysis across multiple wordlists (GSL, AWL, CEFR) with 3D visualizations and hierarchical Excel reports.

### Dictionary Editing
- **Entry Management**: Create and edit dictionary entries
- **Sense-level Control**: Multiple POS senses per word
- **Personal Overrides**: JSON-based persistent storage
- **Corpus Integration**: Combine manual and corpus-derived data
- **AI-Powered Assistance**: Generate definitions and examples automatically using local (Ollama) or cloud (Google Gemini) models

---


## Backend Stack
- **Language**: Python 3.9+
- **Core Framework**: Streamlit (Backend & Frontend handling)
- **Database**: DuckDB (`dictionary.duckdb`)
- **Data Processing**: Pandas, NumPy
- **NLP**: Stanza (multi-language), `eng_to_ipa`, custom implementations
- **AI Integration**: `google-generativeai` (Gemini), `requests` (Ollama) via `utils/ai_helper.py`
- **Visualization**: Matplotlib (network graphs, frequency bands, 3D profiler charts via `mpl_toolkits.mplot3d`)

---

## Directory Structure

### `layout/`
Contains the UI logic for the Streamlit application.
- **`main_view.py`**: Central hub. Handles search logic, rendering of dictionary entries, N-grams, collocates, and the "Corpus Statistic" tab.
- **`sidebar.py`**: Manages sidebar widget state. Handles corpus loading, metadata filtering, and personal override file I/O.
- **`components.py`**: Reusable UI snippets (e.g., network graph renderer, KWIC line formatting with collocate highlighting).

### `pipeline/`
Handles data ingestion and database management.
- **`ingest.py`**: Core logic for parsing files (`.txt`, `.xml`, etc.) and inserting into DuckDB
  - **Format Detection**: Auto-detects vertical vs raw text
  - **Sentence Splitting**: Regex-based sentence boundary detection
  - **XML Handling**: Preserves tags as metadata, extracts attributes
  - **Root Tag Injection**: Adds `<root attribute="filename">` for file-based filtering
  - **Stanza Processing**: Language-specific NLP pipeline
- **`indexing.py`**: Database connection management (`get_connection()`). Handles `duckdb` connections and cursor safety.
- **`profiler.py`**: Core logic for vocabulary coverage analysis. Calculates distribution across wordlists at aggregate, corpus, and file levels.
- **`search.py`**: High-level search interface used by the UI to query the database.
- **`cache_manager.py`**: Intermediary layer for caching expensive queries (N-grams, collocates) using `st.cache_data`.
- **`overrides_io.py`**: Handling read/write operations for the user's `personal_overrides.json`.

### `stats/`
Contains the mathematical and statistical logic.
- **`frequency.py`**: Calculates raw token counts, simple frequencies, and per-million-word (PMW) normalization.
- **`collocation.py`**: Complex queries for N-gram extraction and Collocate calculation (using Log-Likelihood).
- **`kwic.py`**: Logic for retrieving Key Word In Context windows
  - **Sentence-level Retrieval**: Uses `sentence_id` for full sentence context
  - **Window Fallback**: Fixed-width window when sentence boundaries unavailable
  - **Collocate Examples**: Filters examples by collocate presence
  - **Parallel Support**: Fetches aligned translations via `get_parallel_extra()`

### `corpora/`
A directory acting as the repository for raw corpus files. Files placed here are detected by `sidebar.py` as "Built-in Corpora".

### `wordlist/`
Contains logic for checking words against standard lists (GSL, AWL, CEFR) and rendering the corresponding badges.

### `utils/`
Utility functions for language-specific processing.
- **`indo_g2p.py`**: Indonesian grapheme-to-phoneme conversion
- **`ai_helper.py`**: Manages API connections and prompt generation for the AI Assistant (Ollama & Gemini)

### `docs/`
Documentation files.
- **`USERS_MANUAL.md`**: Comprehensive user guide
- **`SYSTEM_ARCHITECTURE.md`**: This document

---

## Database Schema

### `tokens` Table
```sql
CREATE TABLE tokens (
    id BIGINT,              -- Unique token ID
    token VARCHAR,          -- The word/token
    tag VARCHAR,            -- POS tag (e.g., NN, VV, DET)
    lemma VARCHAR,          -- Base form
    corpus VARCHAR,         -- Corpus name
    metadata JSON,          -- Flexible metadata (genre, year, attribute, etc.)
    file_id VARCHAR,        -- Source file path
    sentence_id BIGINT,     -- Sentence identifier (0 if unavailable)
    doc_id BIGINT,          -- Document identifier
    sentence_num BIGINT     -- Sentence number within document
);
```

### Indexes
- `idx_tokens_token`: Fast token lookup
- `idx_tokens_corpus`: Corpus filtering
- `idx_tokens_file_id_id`: File-based queries

---

## Dataflow

### 1. Ingestion Pipeline
```
File Upload → Format Detection → Processing Path
                                    ↓
                    ┌───────────────┴───────────────┐
                    ↓                               ↓
            Vertical Format                   Raw Text
                    ↓                               ↓
        Parse tabs & XML tags          Sentence Splitting (regex)
                    ↓                               ↓
        Extract metadata               Stanza NLP / Whitespace
                    ↓                               ↓
                    └───────────────┬───────────────┘
                                    ↓
                        Batch INSERT to DuckDB
                                    ↓
                            Create Indexes
```

### 2. Query Pipeline
```
User Search → search.py → SQL Query → DuckDB
                                        ↓
                    ┌───────────────────┴───────────────────┐
                    ↓                   ↓                   ↓
              Frequency          Collocates            N-grams
                    ↓                   ↓                   ↓
            frequency.py        collocation.py      collocation.py
                    ↓                   ↓                   ↓
                    └───────────────────┬───────────────────┘
                                        ↓
                            cache_manager.py (caching)
                                        ↓
                                main_view.py (rendering)
```

### 3. KWIC Retrieval
```
Search Term → kwic.py → Find matching tokens
                            ↓
                    Get sentence_id
                            ↓
            ┌───────────────┴───────────────┐
            ↓                               ↓
    sentence_id > 0                  sentence_id = 0
            ↓                               ↓
    Fetch full sentence              Fixed window (±7 tokens)
            ↓                               ↓
    Wrap with <s>...</s>             Return window
            ↓                               ↓
            └───────────────┬───────────────┘
                            ↓
                    Format for display
                            ↓
                    Highlight node & collocate
```

---

## Key Design Patterns

### Embedded Database
Using DuckDB prevents the need for a separate server process (like PostgreSQL), making it ideal as a "lab" tool for easy local deployment. DuckDB's columnar storage and vectorized execution provide excellent performance for analytical queries.

### Session State Management
Extensive use of `st.session_state` to persist:
- Navigation state (current tab, page numbers)
- Loaded corpora and filters
- Search queries and results
- Personal overrides

### Intelligent Caching
Heavy SQL queries are cached using `@st.cache_data`:
- **Corpus Hash**: Uses total token count as cache key
- **N-grams**: Cached by (corpus_hash, query, filters)
- **Collocates**: Cached by (corpus_hash, query, window, filters)
- **Metrics**: Cached by (corpus_hash, query, pos_tag, filters)

### Metadata as JSON
Flexible metadata storage allows:
- Custom attributes from XML tags (e.g., `<text id="filename">`, `<structure segment="abstract">`)
- File-based filtering via `attribute` field
- Genre, year, author, and other domain-specific metadata
- Complex filtering without schema changes

### Dual-mode Processing
- **Vertical Files**: Pre-tagged corpora with XML structure
- **Raw Text**: Automatic NLP processing with Stanza
- **Format Detection**: Automatic based on file content
- **Unified Storage**: Both formats stored in same schema

---

## Advanced Features Implementation

### Automatic Tagging (Stanza Integration)
```python
# pipeline/ingest.py
nlp = stanza.Pipeline(lang, processors='tokenize,pos,lemma')
doc = nlp(text_segment)
for sentence in doc.sentences:
    for word in sentence.words:
        # Extract token, POS, lemma
```

### Sentence Splitting
```python
# Regex pattern: /.*?[\.\!\?](?=\s|\n|$)/s
sentence_pattern = r'.*?[\.\!\?](?=\s|\n|$)'
sentences = re.findall(sentence_pattern, text, re.DOTALL)
```

### Collocate Network Visualization
```python
# layout/components.py
# Radial layout with:
# - Distance inversely proportional to LL score
# - Bubble size proportional to score
# - Left/Right positioning based on directional frequency
# - **Color = POS**: Visual POS tag distinction
- **3D Projections**: The Vocabulary Profiler uses `mpl_toolkits.mplot3d` to render isometric 3D bar charts for category distribution and shadowed pie charts for coverage.
```python
# projection='3d' with ax.bar3d for isometric bars
```

### Parallel Corpus Alignment
```python
# stats/kwic.py
def get_parallel_extra(src_results, tgt_corpus):
    # Match by doc_id and sentence_num
    # Fetch aligned sentence from target corpus
    # Append as 'translation' field
```

### AI Dictionary Generation
```python
# utils/ai_helper.py
def generate_entry(self, word, context_sentences, pos_tag=None):
    # Formats the system prompt with corpus context
    # Calls Ollama (local) or Gemini (cloud)
    # Returns structured JSON with definition, phonetic, collocates, examples
```

---

## Performance Considerations

### Indexing Strategy
- Drop indexes before bulk INSERT
- Recreate indexes after ingestion
- Composite indexes for common query patterns

### Batch Processing
- 50,000 token batch size for INSERT operations
- Pandas DataFrame registration for efficient bulk loading
- Connection pooling with shared connections

### Query Optimization
- Window functions for collocate calculation
- CTE (Common Table Expressions) for complex N-gram queries
- Parameterized queries to prevent SQL injection

---

## File Format Support

### Vertical Format
```
<doc id="1">
<s>
token	POS	lemma
...
</s>
</doc>
```

### Raw Text
- Plain text files
- Automatic sentence detection
- Stanza NLP processing
- XML tag preservation

### Personal Overrides
```json
{
  "word": {
    "POS": {
      "definition": "...",
      "pronunciation": "...",
      "frequency": 100,
      "manual_bigrams": "...",
      "is_manual": true
    }
  }
}
```

---

## Extension Points

### Adding New Languages
1. Add language to `lang_map` in `ingest.py`
2. Ensure Stanza model availability
3. Add pronunciation logic in `main_view.py`
4. Add dictionary links in `components.py`

### Custom Metadata Fields
1. Add XML tags to source files
2. Metadata automatically extracted and stored as JSON
3. Add filter UI in `sidebar.py`
4. Query using JSON operators in SQL

### New Statistical Measures
1. Add calculation logic to `stats/` modules
2. Cache results in `cache_manager.py`
3. Render in `main_view.py` or `components.py`

---

## Dependencies

### Core
- `streamlit` - Web framework
- `duckdb` - Database engine
- `pandas` - Data manipulation
- `numpy` - Numerical operations

### NLP
- `stanza` - Multi-language NLP
- `eng_to_ipa` - English pronunciation
- `Levenshtein` - Fuzzy matching

### AI APIs
- `google-generativeai` - Google Gemini integration
- `requests` - Local Ollama API connections

### Visualization
- `matplotlib` - Charts and graphs

### Utilities
- `openpyxl` - Excel export
- `xlsxwriter` - Excel generation

---

**Version**: 2.0  
**Last Updated**: January 2026
