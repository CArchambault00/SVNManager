# patches_operation.py
from db_handler import dbClass

db = dbClass()

def refresh_patches(treeview, temp, module, username):
    """
    Refresh the patches displayed in the Treeview.
    """
    # Clear existing items
    for item in treeview.get_children():
        treeview.delete(item)
    
    # Fetch patches from the database
    patches = db.get_patch_list(temp, module)
    # Insert patches into the Treeview
    for patch in patches:
        treeview.insert("", "end", values=(
            patch["NAME"], 
            patch["COMMENTS"], 
            patch["PATCH_SIZE"], 
            patch["USER_ID"], 
            patch["CREATION_DATE"], 
            patch["CHECK_LIST_COUNT"]
        ))