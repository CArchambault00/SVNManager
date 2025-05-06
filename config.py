import os
import json
from tkinter import messagebox

CONFIG_FILE = "svn_config.json"
neededVar = ["svn_path", "username", "current_patches"]   # , "instant_client"
specialvar = ["dsn_name"]

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"svn_path": "", "username": "", "current_patches": "D:/cyframe/jtdev/Patches/Current", "dsn_name" : "CYFRAMEPROD"}   # , "instant_client": ""

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

def verify_config():
    config = load_config()
    for var in neededVar:
        if not config.get(var):
            return False
    return True
    
def get_unset_var():
    config = load_config()
    unsetVar = []
    for var in neededVar:
        if not config.get(var):
            unsetVar.append(var)
    return unsetVar

def verify_config():
    unsetVar = get_unset_var()
    if unsetVar:
        raise ValueError(f"The following variables are not set: {', '.join(unsetVar)}")
    
def log_error(message):
    with open("./SVNManager_log.txt", "a") as log_file:
        log_file.write(f"{message}\n")