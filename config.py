import os
import json

CONFIG_FILE = "svn_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"svn_path": "", "username": ""}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)