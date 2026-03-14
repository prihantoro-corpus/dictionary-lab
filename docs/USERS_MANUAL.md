# CORTEX Dictionary Lab - User Manual

## Introduction
Welcome to **CORTEX Dictionary Lab**, a powerful tool for linguistic analysis, corpus management, and dictionary creation. This manual will guide you through the application's features and workflows.

---

## 🌟 Advanced Features

CORTEX Dictionary Lab offers cutting-edge capabilities for corpus linguistics and lexicography:

### 🤖 Automatic Tagging
- **Stanza NLP Integration**: Automatic tokenization, POS tagging, and lemmatization for 6+ languages
- **Multi-language Support**: English, Indonesian, Chinese, Japanese, Korean, Arabic
- **Smart Fallback**: Regex-based processing for unsupported languages
- **Sentence Detection**: Intelligent sentence boundary detection using advanced regex patterns

### 📊 Pattern Extraction (N-gram Analysis)
- **Bigrams & Trigrams**: Automatically extract 2-word and 3-word patterns
- **Directional Analysis**: Forward and backward patterns (e.g., "word + X" vs "X + word")
- **Frequency-based Ranking**: Discover the most common multi-word expressions
- **CSV Export**: Download complete N-gram lists for external analysis
- **Stop Word Filtering**: Focus on meaningful patterns by excluding function words

### 🌐 Parallel Corpus Support
- **Aligned Translation Display**: View source sentences with aligned translations
- **Document-level Alignment**: Support for `doc_id` and `sentence_num` matching
- **Bilingual Analysis**: Compare usage patterns across languages
- **Side-by-side Examples**: KWIC examples show both source and target text

### 🎯 Examples by Collocates
- **Targeted Examples**: See how words combine in real usage
- **Collocate Highlighting**: Visual distinction between search term (red) and collocate (blue)
- **Top Collocate Sections**: Expandable views for each strong word partner
- **Contextual Learning**: Understand semantic relationships through authentic examples

### 🏷️ Examples by Corpus Domain
- **Metadata-based Filtering**: Filter examples by genre, year, author, or custom attributes
- **File-level Filtering**: Automatic `attribute` metadata from filename (e.g., "economy", "sport")
- **Domain-specific Analysis**: Compare word usage across different text types
- **Flexible JSON Metadata**: Support for complex metadata structures

### 📝 XML Corpora Support
- **Vertical Format**: Tab-separated token files with XML structural tags
- **Tag Preservation**: XML tags (`<doc>`, `<s>`, custom tags) preserved as metadata
- **Attribute Extraction**: Automatic parsing of XML attributes (e.g., `<doc id="123">`)
- **Mixed Content**: Handle both tagged and raw text files seamlessly
- **Sentence-level Display**: Examples wrapped in `<s>...</s>` tags for clarity

### 📈 Chart Visualization
- **Network Graph**: Radial collocate visualization (LancsBox-style)
  - **Distance = Strength**: Closer bubbles = stronger association
  - **Size = Score**: Larger bubbles = higher Log-Likelihood
  - **Position = Direction**: Left vs Right collocate dominance
  - **Color = POS**: Visual POS tag distinction
- **Interactive Controls**: Adjustable chart size for detailed inspection
- **PMW & Zipf Bands**: Visual frequency indicators with progress bars

### ✏️ Dictionary Editor
- **Entry-level Editing**: Create new dictionary entries for any word
- **Sense-level Editing**: Manage multiple senses per word (by POS tag)
- **Rich Metadata**: 
  - Custom definitions
  - Pronunciation overrides (IPA/phonetic)
  - Manual frequency adjustment
  - Custom examples and collocates
- **Persistent Storage**: JSON-based personal overrides file
- **Corpus Integration**: Combine manual edits with corpus-derived data
- **AI-Powered Assistance**: Generate definitions and examples automatically via Local (Ollama) or Cloud (Google Gemini) models.
- **Batch Export**: Download complete frequency lists with definitions

---

## 1. Getting Started

### Running the Application
```bash
streamlit run app.py
```

### Sidebar Navigation
The sidebar is your main control center:

#### Language Selection
- **Corpus Language**: Choose the language of your corpus (English, Indonesian, Chinese, Japanese, Korean, Arabic, Javanese, or Other)
- This affects:
  - Pronunciation generation (IPA for English, phonetic for Indonesian)
  - Stanza NLP model selection for raw text processing
  - Dictionary links (Collins for English, KBBI for Indonesian)

#### Corpus Selection
- **Monolingual Mode**: Select a single language and load corpora
- **Parallel Mode**: Toggle "Parallel Corpus Mode" to work with aligned source and target texts
- **Upload**: Upload your own files:
  - **Raw Text** (`.txt`): Automatically tokenized and POS-tagged using Stanza
  - **Vertical/Tagged** (`.txt`, `.xml`): Pre-tokenized format with tabs (token, POS, lemma)
  - **Spreadsheet** (`.xlsx`, `.csv`): For structured data
- **Built-in**: Select from pre-loaded corpora available on disk

#### Personal Overrides
- Manage your custom dictionary edits
- **File Path**: Set the path to your `personal_overrides.json` file
- **Load/Sync**: Load existing overrides or sync changes from the file

- **Collocate Filter**: Whitelist specific words for collocate analysis

#### 📝 User-Defined Wordlists
- **Upload Own Wordlists**: You can upload standard text `.txt` files containing one word per line.
- **Save and Apply**: Click "Save Wordlists" to make them active.
- **Visual Badges**: Words from these custom lists will automatically appear as badges on the Dictionary Entry view (similar to standard GSL/AWL badges), helping you tag or categorize words according to your own custom vocabulary lists.

#### 🤖 AI Assistant
- **AI Provider**: Choose between "None", "Local (Ollama)", or "Google Gemini"
- **Model Selection**: Select the specific model (e.g., `llama3.2`, `gemini-2.0-flash-exp`)
- **API Key**: Required for Cloud providers like Gemini
- **Test Connection**: Verify that your configuration is correct before generating content

---

## 2. File Upload & Processing

### Supported Formats

#### Raw Text Files (`.txt`)
- **Automatic Processing**: Files are automatically detected as raw text if they don't contain tab-separated values
- **Language Detection**: Uses the "Corpus Language" setting from the sidebar
- **Sentence Splitting**: Automatically splits text into sentences using regex pattern: `.*?[\.\!\?](?=\s|\n|$)`
- **Tokenization & POS Tagging**:
  - **Stanza Mode**: For supported languages (English, Indonesian, Chinese, Japanese, Korean, Arabic)
  - **Fallback Mode**: Whitespace tokenization for "Other" languages
- **XML Tag Handling**: XML tags in raw text (e.g., `<doc>`, `<sample>`) are isolated and preserved as metadata
- **Sentence Markers**: Each sentence is wrapped with `<s>` and `</s>` tags for display

#### Vertical/Tagged Files (`.txt`, `.xml`)
Format: Tab-separated values per line
```
token	POS	lemma
<s>
this	DET	this
is	COP	be
sentence	NN	sentence
</s>
```
- Lines starting with `<` are treated as metadata tags
- Supports `<s>`, `<doc>`, and custom XML tags with attributes

#### Root Tag Injection
- **Automatic**: All uploaded files get a `<root attribute="filename">` metadata entry
- **Purpose**: Allows filtering by source file using metadata filters
- **Example**: `economy.txt` → `<root attribute="economy">`

#### Additional XML Metadata (e.g., BAWE Corpus)
- **Text ID**: `<text id="filename">` tags are parsed resulting in an `id="filename"` metadata attribute.
- **Structure Segments**: `<structure segment="abstract">` and similar XML structure tags are fully supported and their attributes become filterable metadata.

---

## 3. Searching

Type a word in the **"Search word"** box on the main screen.

- **Exact Match**: The app searches for the exact word in the loaded corpus
- **Fuzzy Match**: If not found, the app suggests similar words (useful for typos)
- **Multi-word Phrases**: Enter a phrase (e.g., "central bank") to analyze it as a unit
- **Autocomplete**: Suggestions appear as you type or if your query isn't found immediately

---

## 4. Analysis Views

### Search Tab
This is the default view after searching.

#### 1. Dictionary Entry
- **Header**: Word, Pronunciation (IPA/phonetic), and Audio links (US/UK for English)
- **Statistics**: 
  - **Frequency**: Raw count in the filtered corpus
  - **PMW**: Per Million Words (relative frequency)
  - **Zipf Band**: 1-5 scale (1 = very rare, 5 = very common)
- **Badges**: Wordlist status indicators. Built-in lists include GSL, AWL, CEFR levels. Additionally, any active **User-Defined Wordlists** uploaded via the sidebar will appear here as customized badges.
- **Sense Definitions**: View and edit definitions for different POS tags
- **External Links**: Quick access to Collins Dictionary, KBBI (Indonesian), Google Search, etc.

#### 2. N-Grams
- **Bigrams**: Words frequently found immediately before or after your search term
  - `search + Word` (forward)
  - `Word + search` (backward)
- **Trigrams**: Three-word patterns involving your search term
  - `search + W1 + W2`
  - `W1 + search + W2`
  - `W1 + W2 + search`
- **Download**: Export N-gram lists to CSV

#### 3. Collocates
- **Top-20 List**: Words that strongly associate with your search term
  - Scored using Log-Likelihood (LL)
  - Shows frequency and POS tag
  - Clickable to search for that word
- **Network Graph**: Visual representation
  - **Distance from center**: Inversely proportional to score (closer = stronger)
  - **Bubble size**: Proportional to score (bigger = stronger)
  - **Position**: Left vs Right dominance
  - **Color**: Based on POS tag
  - **Adjustable**: Use the slider to resize the chart

#### 4. Examples (KWIC - Key Word In Context)
- **Sentence-Level Display**: Examples are shown at the sentence level
- **Sentence Markers**: Each example is wrapped with `<s>` and `</s>` tags
- **Format**:
  ```
  <s> left context node right context </s>
  ```
- **Highlighting**: 
  - Search term in red
  - Collocate (if applicable) in blue
- **Parallel View**: If in Parallel Mode, see the aligned translation below each example
- **Full Sentence**: When sentence boundaries are detected, the entire sentence is shown (not just a fixed window)

#### 5. Examples by Collocates
- Expandable sections for top collocates
- Shows usage examples where both the search term and collocate appear together
- Helps understand how words combine in context

---

### Corpus Statistic Tab
Switch to this tab via the top navigation radio button.

- **Global Stats**: Total tokens, lemmas, and unique POS tags in the current selection
- **POS Distribution**: Visual badges of available Parts of Speech
- **Frequency List**:
  - Browse the most frequent words in the filtered corpus
  - Sorted by definition status (words with definitions first) then frequency
  - **Pagination**: Navigate through pages (50 items per page)
  - **Download Excel**: Export the full frequency list for offline analysis
  - **Clickable**: Click any word to search for it

---

## 5. Editing & Dictionary Creation

You can turn the corpus tool into a dictionary editor.

### Editing a Sense
1. **Edit Sense**: In the Search Tab, expand "📝 Edit Sense" under any POS tag
2. **Fields**:
   - **Pronunciation**: Override the auto-generated IPA/phonetic
   - **Frequency**: Set a manual frequency (overrides corpus data)
   - **Definition**: Write your own definition
   - **Manual Statistics**: Add custom data if corpus data is insufficient:
     - **Bigrams**: Format: `node word | 10` (one per line)
     - **Trigrams**: Format: `node w1 w2 | 3` (one per line)
     - **Collocates**: Format: `word | score` (one per line)
     - **KWIC Examples**: Format: `left | node | right` (one per line)
     - **Collocate Examples**: Format: `collocate | left | node | right` (one per line)
3. **✨ Generate with AI**: (Requires AI enabled in sidebar)
   - Click to automatically analyze the word using your selected AI model (Ollama or Gemini).
   - The AI uses context from your current corpus (N-grams, Collocates, and KWIC) to create accurate suggestions for the specific POS.
   - You can preview the suggested definitions, examples, and phonetic transcription.
   - Click "Apply AI Suggestions" to populate the form fields. (If the generation fails or produces unexpected JSON, click again to retry).
4. **Save**: Click "Save Changes" to write to your `personal_overrides.json`

### Adding a New Sense
1. Use the "➕ Add Sense" tab
2. Create a new entry for a word (e.g., adding a Noun sense to a word that only appears as a Verb)
3. Fill in the fields and save

### Creating Entries for Missing Words
1. Search for a word not in the corpus
2. Click "➕ Create Entry for '[word]'"
3. A default "General" sense is created
4. Edit and customize as needed

---

## 6. Advanced Features

### Metadata Filtering
- **JSON-based**: Metadata is stored as JSON in the database
- **Common Fields**:
  - `attribute`: Auto-generated from filename (e.g., "economy", "sport")
  - Custom fields from XML tags (e.g., `genre`, `year`, `author`)
- **Usage**: Enter key-value pairs in the sidebar to filter
  - Example: `attribute = economy` to show only tokens from `economy.txt`

### Parallel Corpus Mode
1. Toggle "Parallel Corpus Mode" in the sidebar
2. Select **Source** and **Target** corpora
3. Requirements:
   - Both corpora must have aligned `doc_id` and `sentence_num` values
   - Typically from parallel vertical files with matching `<doc>` and `<s>` tags
4. **Display**: Examples show source sentence with translation below

### Stop Words & Collocate Filtering
- **Stop Words**: Exclude common words from N-gram and collocate analysis
  - Useful for focusing on content words
  - Enter one word per line in the sidebar text area
- **Collocate Filter**: Whitelist specific words
  - Only these words will appear in collocate results
  - Useful for targeted analysis

---

## 7. Troubleshooting

### Common Issues

#### "Database is locked"
- **Cause**: Another process is accessing the database
- **Solution**: 
  - Restart the Streamlit app
  - Close other instances of the app
  - Check for background processes

#### "Failed to load [corpus]: name 'X' is not defined"
- **Cause**: Missing import or code error
- **Solution**: Check the terminal for full error message and report as a bug

#### Sentence Splitting Not Working
- **Check**: Language setting in sidebar
- **For Indonesian**: Set to "Indonesian" (not "Other") to use Stanza
- **For Other Languages**: Uses regex-based splitting
- **Verify**: Look at examples - each should have separate `<s>` tags

#### Entire Article Shown as One Sentence
- **Cause**: File may already have `<s>` tags wrapping the entire text
- **Solution**: Remove existing `<s>` tags from source file before upload
- **Note**: The system adds sentence tags automatically during processing

#### Missing Words in Search
- **Check**: Metadata filters in sidebar
- **Solution**: Clear filters or adjust to include the word's metadata
- **Indicator**: App will show "exists in database but hidden by filters"

#### Slow Performance
- **Large Corpus**: Processing may take time
- **Solutions**:
  - Use smaller files for testing
  - Wait for indexing to complete
  - Close other heavy applications

---

## 8. Tips & Best Practices

### For Raw Text Upload
1. **Set Language First**: Choose the correct language before uploading
2. **Clean Text**: Remove unwanted formatting or characters
3. **Sentence Boundaries**: Ensure proper punctuation (`.`, `!`, `?`) for sentence detection
4. **XML Tags**: Use standard XML format for metadata (e.g., `<doc id="1">`)

### For Vertical Files
1. **Tab-Separated**: Use tabs (not spaces) between columns
2. **Three Columns**: token, POS, lemma (minimum)
3. **Sentence Tags**: Use `<s>` and `</s>` to mark sentence boundaries
4. **Document Tags**: Use `<doc id="X">` to mark document boundaries

### For Dictionary Creation
1. **Start with Corpus**: Let the corpus provide frequency and examples
2. **Override Selectively**: Only override when corpus data is insufficient
3. **Save Regularly**: Sync to your personal file frequently
4. **Backup**: Keep backups of your `personal_overrides.json`

### For Analysis
1. **Use Filters**: Narrow down to specific genres, time periods, or files
2. **Compare**: Use parallel mode to compare languages
3. **Export**: Download frequency lists and N-grams for external analysis
4. **Visualize**: Use the network graph to understand collocate relationships

---

## 9. File Formats Reference

### Personal Overrides JSON
```json
{
  "word": {
    "POS_TAG": {
      "definition": "Your definition here",
      "pronunciation": "/custom/",
      "frequency": 100,
      "manual_bigrams": "word1 | 10\nword2 | 5",
      "manual_trigrams": "w1 w2 | 3",
      "manual_collocates": "collocate | 15.5",
      "manual_examples": "left | node | right",
      "manual_collo_ex": "col | left | node | right",
      "is_manual": true
    }
  }
}
```

### Vertical File Format
```
<text id="sample_01">
<doc id="1">
<structure segment="abstract">
<s>
This	DET	this
is	COP	be
a	DET	a
sentence	NN	sentence
.	PUNCT	.
</s>
</structure>
<s>
Another	DET	another
sentence	NN	sentence
.	PUNCT	.
</s>
</doc>
</text>
```

---

## 10. Keyboard Shortcuts & UI Tips

- **Search Box**: Press Enter to search
- **Clickable Words**: Throughout the app, words are clickable to search
- **Expandable Sections**: Click to expand/collapse detailed information
- **Tabs**: Use tabs to switch between List View and Network Graph
- **Pagination**: Use Previous/Next buttons for long lists
- **Download Buttons**: Look for 📥 icons to export data

---

## Support & Resources

- **Manual**: This document
- **System Architecture**: See `docs/SYSTEM_ARCHITECTURE.md` for technical details
- **Issues**: Report bugs or request features through your project management system
- **Updates**: Check for new features and improvements regularly

---

**Version**: 2.0  
**Last Updated**: January 2026
