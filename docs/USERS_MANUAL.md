# CORTEX Dictionary Lab - User Manual

## Introduction
Welcome to **CORTEX Dictionary Lab**, a powerful tool for linguistic analysis, corpus management, and dictionary creation. This manual will guide you through the application's features and workflows.

## 1. Getting Started

### Sidebar Navigation
The sidebar is your main control center.
- **Manual**: Click the "📖 Manual" link at the top to access the online Google Doc documentation.
- **Corpus Selection**:
    - **Monolingual Mode**: Select a single language and load corpora.
    - **Parallel Mode**: Toggle "Parallel Corpus Mode" to work with aligned source and target texts.
    - **Upload**: Upload your own `.txt`, `.xml`, `.xlsx`, or `.csv` files.
    - **Built-in**: Select from pre-loaded corpora available on the server.
- **Personal Overrides**:
    - Manage your custom dictionary edits.
    - **File Path**: Set the path to your `personal_overrides.json` file.
    - **Load/Sync**: Load existing overrides or sync changes from the file.
- **Metadata & Filters**:
    - Filter the active corpus by metadata (e.g., Genre, Year) if available.
    - **Skip Punctuation**: Toggle to ignore punctuation in analysis.
    - **Stop Words**: detailed list of words to exclude from N-gram and collocate analysis.

## 2. Searching
Type a word in the **"Search word"** box on the main screen.

- **Exact Match**: The app searches for the exact word in the loaded corpus.
- **Fuzzy Match**: If not found, the app suggests similar words (useful for typos).
- **Multi-word Phrases**: Enter a phrase (e.g., "central bank") to analyze it as a unit.
- **Autocomplete**: Suggestions appear as you type or if your query isn't found immediately.

## 3. Analysis Views

### Search Tab
This is the default view after searching.
1.  **Dictionary Entry**:
    - **Header**: Word, Pronunciation (IPA), and Audio links (US/UK).
    - **Statistics**: Raw Frequency, PMW (Per Million Words), and Zipf Band.
    - **Badges**: Wordlist status (e.g., GSL, AWL, CEFR).
    - **Sense Definitions**: View and edit definitions for different POS tags.
    - **External Links**: Quick access to Collins Dictionary, KBBI (Indonesian), etc.
2.  **N-Grams**:
    - **Bigrams**: Words frequently found immediately before or after your search term.
    - **Trigrams**: Three-word patterns involving your search term.
    - **Download**: Export N-gram lists to CSV.
3.  **Collocates**:
    - **Top-20 List**: Words that strongly associate with your search term (Log-Likelihood score).
    - **Network Graph**: Visual representation of collocate strength and position (Left/Right).
4.  **Examples (KWIC)**:
    - **Key Word In Context**: See your word used in actual sentences from the corpus.
    - **Parallel View**: If in Parallel Mode, see the aligned translation next to the source sentence.

### Corpus Statistic Tab
Switch to this tab via the top navigation radio button.
- **Global Stats**: Total tokens, lemmas, and unique POS tags in the current selection.
- **POS Distribution**: Visual badges of available Parts of Speech.
- **Frequency List**:
    - Browse the most frequent words in the filtered corpus.
    - **Download Excel**: Export the full frequency list for offline analysis.

## 4. Editing & Dictionary Creation
You can turn the corpus tool into a dictionary editor.
1.  **Edit Sense**: In the Search Tab, expand "📝 Edit Sense" under any POS tag.
2.  **Fields**:
    - **Definition**: Write your own definition.
    - **Pronunciation**: Override the auto-generated IPA.
    - **Manual Stats**: Add manual Bigrams, Trigrams, or Examples if the corpus data is insufficient.
3.  **Save**: Click "Save Changes" to write to your `personal_overrides.json`.
4.  **Add New Sense**: Use the "➕ Add Sense" tab to create a new entry for a word (e.g., adding a Noun sense to a word that only appears as a Verb).

## 5. Troubleshooting
- **Corpus Hangs**: If loading takes too long, try a smaller file or ensure no other heavy processes are running.
- **Missing Words**: Check your "Filters" in the sidebar. Used metadata filters might be hiding the word.
- **Database Lock**: If you see "database locked", try restarting the app or ensuring no other instance is accessing the `duckdb` file.
