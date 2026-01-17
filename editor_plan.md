# Dictionary Editor Implementation Plan

## State Management
We will use a centralized session state `st.session_state['dictionary_overrides']` to store all changes made by the user.
Structure:
```json
{
  "token": {
    "POS": {
      "definition": "...",
      "pronunciation": "...",
      "frequency": 123,
      "examples": [
        {"left": "...", "node": "...", "right": "..."}
      ]
    }
  }
}
```

## Proposed Changes

### [Navigation]
- Update `main_view.py`: replace `st.write` of lists with a row of small buttons or clickable elements that update `st.session_state['search_input']`.

### [Editor UI]
- **Edit Mode**: Add an "Edit" button to each corpus sense. Clicking it toggles an edit form.
- **Add Sense**: Expand the existing tab to include text inputs/areas for ALL dictionary fields.
- **Save All**: A dedicated layout in `main_view.py` or `sidebar.py` to trigger full state export.

### [Sidebar Persistence]
- **File Uploader (Corpus)**: `st.sidebar.file_uploader` for `.txt`. Trigger `ingest.CorpusParser`.
- **File Uploader (Changes)**: `st.sidebar.file_uploader` for `.json`. Parse and merge into `st.session_state['dictionary_overrides']`.

## Verification Plan
1. Add a sense for "research" (e.g., POS: 'EX', Def: 'Manual Test'). Verify it persists across searches.
2. Edit "research" (POS: NN) to change its frequency. Verify change.
3. Export JSON -> Refresh app -> Upload JSON. Verify data restored.
4. Click "researchers" in related words. Verify it searches "researchers".
