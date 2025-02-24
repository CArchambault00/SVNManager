# patches_operation.py
import oracledb

class Patch:
    def __init__(self, patch_id, name, comments, patch_size, user_id, creation_date, check_list_count):
        self.patch_id = patch_id
        self.name = name
        self.comments = comments
        self.patch_size = patch_size
        self.user_id = user_id
        self.creation_date = creation_date
        self.check_list_count = check_list_count

def get_all_patches(temp_yn: bool, module: str, username: str = None):
    """
    Fetch all patches from the database.
    Returns a list of tuples containing patch details.
    """
    try:
        oracledb.init_oracle_client(lib_dir=r"D:\app\product\instantclient_12_1")
        
        # Connect to the database
        conn = oracledb.connect(user='DEV_TOOL', password='DEV_TOOL', dsn='PROD_CYFRAME')
        cursor = conn.cursor()
        
        # Base SQL query
        sql = """
            SELECT H.PATCH_ID, H.NAME, H.COMMENTS, 
                DECODE(COUNT(D.PATCH_ID), 0, 0, COUNT(*)) AS PATCH_SIZE, 
                H.USER_ID, H.CREATION_DATE,
                CHECKLIST_COUNT(H.PATCH_ID) AS CHECK_LIST_COUNT 
            FROM PATCH_HEADER H, PATCH_DETAIL D
            WHERE H.PATCH_ID = D.PATCH_ID (+)
            AND H.DELETED_YN = 'N'
           
        """
        if temp_yn:
            sql += "AND H.TEMP_YN = 'Y'"
        else:
            sql += "AND H.TEMP_YN = 'N'"
        
        # Correctly map module to the expected values
        if module == "V": 
            sql += "AND H.APPLICATION_ID = 'BT'"
        else:    
            sql += "AND H.APPLICATION_ID = 'CORE'"
        
        sql += " GROUP BY H.PATCH_ID, H.NAME, H.COMMENTS, H.USER_ID, H.CREATION_DATE ORDER BY H.PATCH_ID DESC"
       
        # Execute the query
        cursor.execute(sql)
        
        # Fetch all results
        patches = cursor.fetchall()
        conn.close()
        
        patch_objects = [Patch(*patch) for patch in patches]
        
        return patch_objects
    except Exception as e:
        print(f"Error fetching patches: {e}")
        return []
    
def refresh_patches_db(treeview, temp, module, username):
    """
    Refresh the patches displayed in the Treeview.
    """
    # Clear existing items
    for item in treeview.get_children():
        treeview.delete(item)
    
    # Fetch patches from the database
    patches = get_all_patches(temp, module, username)
    # Insert patches into the Treeview
    for patch in patches:
        treeview.insert("", "end", values=(
            patch.name, 
            patch.comments, 
            patch.patch_size, 
            patch.user_id, 
            patch.creation_date, 
            patch.check_list_count
        ))