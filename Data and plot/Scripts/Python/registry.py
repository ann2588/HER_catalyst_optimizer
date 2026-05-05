import json
import os

REGISTRY_PATH = "data_id.json"


with open(REGISTRY_PATH, "r") as f:
    REGISTRY = json.load(f)

def get_data(key):
    try:
        return REGISTRY[key]
    except KeyError:
        raise ValueError(f"[Data Registry] Key '{key}' not found in data_id.json")
    
def get_data_path(key):
    """Return absolute path (file or folder)."""
    rel = REGISTRY[key]
    return os.path.abspath(os.path.join(REGISTRY_PATH, "..", rel))

def get_data_folder(key):
    """Return path ONLY IF key is a folder."""
    path = get_data_path(key)
    if os.path.isdir(path):
        return path
    raise ValueError(f"Key '{key}' is a file, not a folder.")