import json
import os

def save_entries_to_json(entries, filepath):
    """
    Saves a list of dictionary entries to a JSON file.
    'entries' should be a list of dicts.
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving JSON: {e}")
        return False

def load_entries_from_json(filepath):
    """
    Loads dictionary entries from a JSON file.
    """
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return []
