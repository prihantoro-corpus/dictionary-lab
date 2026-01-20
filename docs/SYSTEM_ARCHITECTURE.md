# CORTEX Dictionary Lab - System Architecture

## Overview
CORTEX Dictionary Lab is a stream-processing web application built with **Streamlit**. It uses **DuckDB** as a high-performance, in-process analytical SQL engine to handle large linguistic corpora efficiently.

## Backend Stack
- **Language**: Python 3.9+
- **Core Framework**: Streamlit (Backend & Frontend handling)
- **Database**: DuckDB (`dictionary.duckdb`)
- **Data Processing**: Pandas, NumPy
- **Linguistics**: `eng_to_ipa`, Custom NLP implementations

## Directory Structure

### `layout/`
Contains the UI logic for the Streamlit application.
- `main_view.py`: The central hub. Handles search logic, rendering of dictionary entries, N-grams, collocates, and the "Corpus Statistic" tab.
- `sidebar.py`: Manages the sidebar widget state. Handles corpus loading, metadata filtering, and personal override file I/O.
- `components.py`: Reusable UI snippets (e.g., specific graph renderers, KWIC line formatting).

### `pipeline/`
Handles data ingestion and database management.
- `ingest.py`: Core logic for parsing raw files (`.txt`, `.xml`, etc.) and inserting them into DuckDB. It tokenizes text and creates initial indices.
- `indexing.py`: Database connection management (`get_connection()`). Handles `duckdb` connections and cursor safety.
- `search.py`: High-level search interface used by the UI to query the database.
- `cache_manager.py`: Intermediary layer for caching expensive queries (N-grams using `st.cache_data`).
- `overrides_io.py`: Handling read/write operations for the user's `personal_overrides.json`.

### `stats/`
Contains the mathematical and statistical logic.
- `frequency.py`: Calculates raw token counts, simple frequencies, and per-million-word (PMW) normalization.
- `collocation.py`: Complex queries for N-gram extraction and Collocate calculation (using Log-Likelihood).
- `kwic.py`: Logic for retrieving Key Word In Context windows.

### `corpora/`
A directory acting as the repository for raw corpus files. Files placed here are detected by `sidebar.py` as "Built-in Corpora".

### `wordlist/`
Contains logic for checking words against standard lists (GSL, AWL, CEFR) and rendering the corresponding badges.

## Dataflow
1.  **Ingestion**: `CorpusParser` reads a file -> Tokenizes -> SQL INSERT into `tokens` table in DuckDB.
2.  **Querying**: User inputs text in `search_box` -> `search.py` constructs SQL -> `stats` modules execute analytical SQL (e.g., Window functions for collocates) -> Results returned as Dicts/Pandas DataFrames.
3.  **Rendering**: `main_view.py` takes the data -> Uses pure HTML/CSS injection for custom badges/tables -> Streamlit widgets for interaction.

## Key Design Patterns
- **Embedded Database**: Using DuckDB prevents the need for a separate server process (like PostgreSQL), identifying it as a "lab" tool for easy local deployment.
- **Session State**: Extensive use of `st.session_state` to persist navigation, loaded corpora, and search queries across Streamlit's reruns.
- **Caching**: Heavy SQL queries (like N-gram generation) are cached using `@st.cache_data` to ensure instant responsiveness on repeated lookups.
