import os
from dotenv import load_dotenv
from tkinter import messagebox

# Load the .env file

def get_env_var(var_name):
    load_dotenv()
    if var_name not in os.environ:
        return None
    return os.getenv(var_name)  # Return the value of the environment variable

def set_env_var(var_name, value):
    load_dotenv()
    env_vars = {}
    if os.path.exists(".env"):
        with open(".env", "r") as env_file:
            for line in env_file:
                if line.strip() and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    env_vars[key] = val.strip("'")
    env_vars[var_name] = value
    with open(".env", "w") as env_file:
        for key, val in env_vars.items():
            env_file.write(f"{key}='{val}'\n")

def verify_env():
    env_vars = ["INSTANT_CLIENT"]
    missing_vars = []
    for var in env_vars:
        if not get_env_var(var):
            missing_vars.append(var)
    if missing_vars:
        messagebox.showerror("Error", f"Set the following environment variables in .env: {', '.join(missing_vars)}")
        exit(1)
        return False