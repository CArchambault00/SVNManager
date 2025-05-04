from tkinter import messagebox
from db_handler import dbClass

revision, major, minor = 0, 0, 0

def next_version(application_id):
    db = dbClass()

    global revision, major, minor
    max_version = db.get_max_version(application_id)
    if max_version:
        revision = max_version[0]["REVISION"]
        # fill revision with 0 up to 4 digits
        major = max_version[0]["MAJOR"]
        minor = max_version[0]["MINOR"]
        revision += 1
        revision = str(revision).zfill(4)
        new_version = f"{major}.{minor}.{revision}-"
        return new_version
    else:
        messagebox.showerror("Error", "Failed to retrieve the max version")
        return None