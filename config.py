import os
import json
from tkinter import messagebox
import datetime as date

CONFIG_FILE = "svn_config.json"
ERROR_LOG_FILE = "SVNManager_error.log"
SUCCESS_LOG_FILE = "SVNManager_success.log"
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

def _write_log(message: str, log_file: str, include_timestamp: bool = True):
    """Internal function to write to log files with consistent formatting."""
    try:
        with open(log_file, "a", encoding='utf-8') as log:
            if include_timestamp:
                timestamp = date.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log.write(f"[{timestamp}] {message}\n")
            else:
                log.write(f"{message}\n")
            log.write("-" * 80 + "\n")  # Separator line for better readability
    except Exception as e:
        print(f"Failed to write to log file {log_file}: {e}")
    
def log_error(message: str, include_stack: bool = False):
    """
    Log error messages to the error log file.
    Args:
        message: The error message to log
        include_stack: Whether to include stack trace information
    """
    import traceback
    error_msg = message
    if include_stack:
        error_msg += f"\nStack trace:\n{traceback.format_exc()}"
    _write_log(error_msg, ERROR_LOG_FILE)

def log_success(action: str, details: str = None):
    """
    Log successful actions to the success log file.
    Args:
        action: The action that was successful (e.g., "Patch Creation", "File Lock")
        details: Additional details about the success (optional)
    """
    message = f"SUCCESS - {action}"
    if details:
        message += f"\nDetails: {details}"
    _write_log(message, SUCCESS_LOG_FILE)