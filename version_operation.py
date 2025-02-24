import oracledb
import tkinter as tk
from tkinter import messagebox

def get_max_version(module):
    oracledb.init_oracle_client(lib_dir=r"D:\app\product\instantclient_12_1")
    conn = oracledb.connect(user='DEV_TOOL', password='DEV_TOOL', dsn='PROD_CYFRAME')
    cursor = conn.cursor()
    
    # First query to get MAJOR and MINOR
    cursor.execute("SELECT MAJOR, MINOR FROM CURRENT_VERSION WHERE APPLICATION_ID='CORE'")
    result = cursor.fetchone()
    
    if result:
        nMajor, nMinor = result
    else:
        nMajor, nMinor = 0, 0  # Default values if no result found
    
    sql = """
        SELECT NVL(MAX(REVISION), 0) AS REVISION, NVL(MAX(MAJOR), :nMajor) AS MAJOR, NVL(MAX(MINOR), :nMinor) AS MINOR 
        FROM PATCH_HEADER 
        WHERE DELETED_YN = 'N' AND TEMP_YN = 'N' 
        AND MAJOR = :nMajor AND MINOR = :nMinor
    """

    if module == "V":
        sql += "AND APPLICATION_ID = 'BT'"
    else:
        sql += "AND APPLICATION_ID = 'CORE'"

    cursor.execute(sql, {"nMajor": nMajor, "nMinor": nMinor})
    
    result = cursor.fetchone()
    conn.close()
    return result

def next_version(module):
    max_version = get_max_version(module)
    if max_version:
        revision, major, minor = max_version
        revision += 1
        new_version = f"{major}.{minor}.{revision}-"
        return new_version
    else:
        messagebox.showerror("Error", "Failed to retrieve the max version")
        return None