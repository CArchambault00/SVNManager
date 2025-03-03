import tkinter as tk
from tkinter import messagebox

from db_handler import dbClass

db = dbClass()

revision, major, minor = 0, 0, 0

def next_version(module):
    global revision, major, minor
    max_version = db.get_max_version(module)
    if max_version:
        revision = max_version[0]["REVISION"]
        major = max_version[0]["MAJOR"]
        minor = max_version[0]["MINOR"]
        revision += 1
        new_version = f"{major}.{minor}.{revision}-"
        return new_version
    else:
        messagebox.showerror("Error", "Failed to retrieve the max version")
        return None
    
def determine_application_id(patch_letter):
    if patch_letter == 'V':
        return 'BT'
    elif patch_letter == 'S':
        return 'CORE_SVN'
    else:
        return 'CORE'