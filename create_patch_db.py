import oracledb
import version_operation as vo

def create_patch_header(patch_letter:str , patch_version:str, patch_desc: str, username: str, personal: bool) -> int:
    oracledb.init_oracle_client(lib_dir=r"D:\app\product\instantclient_12_1")
        
    # Connect to the database
    conn = oracledb.connect(user='DEV_TOOL', password='DEV_TOOL', dsn='PROD_CYFRAME')
    cursor = conn.cursor()

    # Obtenir le dernier ID
    cursor.execute("SELECT MAX(PATCH_ID) FROM PATCH_HEADER")
    max_id = cursor.fetchone()[0]
    patch_id = 1 if max_id is None else max_id + 1
    
    application_id = vo.determine_application_id(patch_letter)

    cursor.execute(
        """
        INSERT INTO PATCH_HEADER (PATCH_ID, NAME, COMMENTS, TEMP_YN, USER_ID, APPLICATION_ID, MAJOR, MINOR, REVISION)
        VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9)
        """,
        (patch_id, patch_letter + patch_version, patch_desc, 'Y' if personal else 'N', username, application_id, vo.major, vo.minor, vo.revision)
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    return patch_id
