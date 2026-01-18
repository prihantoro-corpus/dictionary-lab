import json
import os

def load_overrides(path):
    """Loads dictionary overrides from a JSON file."""
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading personal overrides: {e}")
        return {}

def save_overrides(path, data):
    """Saves dictionary overrides to a JSON file."""
    if not path:
        return False
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving personal overrides: {e}")
        return False
