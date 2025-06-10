import os
import sys
from typing import Optional, Dict, List, Any
import oracledb
from contextlib import contextmanager
from datetime import datetime
from tkinter import messagebox
from config import log_error, load_config

class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass

@contextmanager
def db_cursor(db_conn):
    """Context manager for database cursors."""
    cursor = db_conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()

class DatabaseConnection:
    """Manages the database connection lifecycle."""
    
    def __init__(self):
        self._conn: Optional[oracledb.Connection] = None
        self._initialize_client()
        
    def _initialize_client(self) -> None:
        """Initialize Oracle client libraries."""
        try:
            base_path = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.abspath(".")
            client_path = os.path.join(base_path, "instantclient_12_1")
            oracledb.init_oracle_client(lib_dir=client_path)
        except Exception as e:
            log_error(f"Failed to initialize Oracle client: {e}")
            raise DatabaseError(f"Oracle client initialization failed: {e}")

    @property
    def conn(self) -> oracledb.Connection:
        """Get the current database connection or create a new one."""
        if not self._conn:
            self.connect()
        return self._conn
    
    def connect(self) -> None:
        """Establish database connection using configuration."""
        config = load_config()
        try:
            self._conn = oracledb.connect(
                user='DEV_TOOL',
                password='DEV_TOOL',
                dsn=config.get("dsn_name", "CYFRAMEPROD")
            )
        except oracledb.Error as e:
            error_msg = f"Database connection failed: {e}"
            log_error(error_msg)
            messagebox.showerror("Database Error", error_msg)
            raise DatabaseError(error_msg)

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            try:
                self._conn.close()
            finally:
                self._conn = None

class dbClass:
    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self):
        instantclient_path = None
        config = load_config()
        try:
             # Detect if running inside compiled .exe
            if getattr(sys, 'frozen', False):
                # Running from PyInstaller bundle
                base_path = sys._MEIPASS
            else:
                # Running from source
                base_path = os.path.dirname(os.path.abspath(__file__))

            instantclient_path = os.path.join(base_path, "instantclient_12_1")
            
            oracledb.init_oracle_client(lib_dir=instantclient_path)
            self.conn = oracledb.connect(user='DEV_TOOL', password='DEV_TOOL', dsn=config.get("dsn_name", "CYFRAMEPROD"))
        except oracledb.Error as e:
            messagebox.showerror("Database Error", f"Failed to connect to the database, Application will not work properly\n{e}")
            log_error(f"Database Error: {e}")
            log_error(f"Date: {datetime.now()}")
            log_error(f"Instant Client Path: {instantclient_path}\n")
            log_error(f"TNS_ADMIN: {os.environ['TNS_ADMIN']}\n")
            log_error(f"------------------------------")

        # config = load_config()
        # hostname = config.get("db_host", "db04.intranet.cyframe.com")
        # port = config.get("db_port", "1521")
        # service_name = config.get("db_service", "CYFRAMEPROD")

        # dsn = f"{hostname}:{port}/{service_name}"

        # self.conn = oracledb.connect(
        #     user=config.get("db_user", "DEV_TOOL"),
        #     password=config.get("db_password", "DEV_TOOL"),
        #     dsn=dsn
        # )

    def close(self):
        if self.conn:
            self.conn.close()

    def execute_query(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(sql, params or {})
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        return results

    def execute_non_query(self, sql: str, params: Optional[Dict] = None):
        cursor = self.conn.cursor()
        cursor.execute(sql, params or {})
        cursor.close()

    def get_folder_list(self):
        sql = "SELECT PATH, DESCRIPTION, FOLDER_TYPE, SOFT_PATH, DEFAULT_PREFIX FROM FOLDER ORDER BY FOLDER_TYPE, PATH"
        return self.execute_query(sql)

    def add_folder(self, folder: str, description: str, folder_type: int):
        sql = "INSERT INTO FOLDER (PATH, DESCRIPTION, FOLDER_TYPE) VALUES (:folder, :description, :folder_type)"
        self.execute_non_query(sql, {'folder': folder, 'description': description, 'folder_type': folder_type})

    def rename_folder(self, folder: str, description: str):
        sql = "UPDATE FOLDER SET DESCRIPTION = :description WHERE PATH = :folder"
        self.execute_non_query(sql, {'description': description, 'folder': folder})

    def get_file_list(self, folder: str):
        sql = "SELECT FILE_ID, PATH, NAME, DELETED_YN FROM FILES WHERE PATH = :folder ORDER BY NAME"
        return self.execute_query(sql, {'folder': folder})

    def add_file(self, folder: str, filename: str) -> int:
        sql = "SELECT FILE_ID FROM FILES WHERE PATH = :folder AND NAME = :filename"
        result = self.execute_query(sql, {'folder': folder, 'filename': filename})
        if result:
            return result[0]['FILE_ID']
        else:
            sql = "SELECT MAX(FILE_ID) AS MAX_ID FROM FILES"
            result = self.execute_query(sql)
            file_id = (result[0]['MAX_ID'] or 0) + 1
            sql = "INSERT INTO FILES (FILE_ID, PATH, NAME, DELETED_YN) VALUES (:file_id, :folder, :filename, 'N')"
            self.execute_non_query(sql, {'file_id': file_id, 'folder': folder, 'filename': filename})
            return file_id

    def get_file_patch_list(self, folder: str, name: str):
        sql = """
        SELECT F.FILE_ID, F.PATH, F.NAME, F.DELETED_YN, H.NAME AS PATCH_NAME, D.VERSION
        FROM FILES F, PATCH_DETAIL D, PATCH_HEADER H
        WHERE F.FILE_ID = D.FILE_ID
        AND D.PATCH_ID = H.PATCH_ID
        AND F.PATH = :folder
        AND F.NAME = :name
        AND H.TEMP_YN = 'N'
        AND H.DELETED_YN = 'N'
        ORDER BY D.VERSION DESC
        """
        return self.execute_query(sql, {'folder': folder, 'name': name})

    def get_folder_patch_list(self, folder: str):
        sql = """
        SELECT F.FILE_ID, F.PATH, F.NAME, F.DELETED_YN, H.NAME AS PATCH_NAME, D.VERSION, D.MD5_CHECKSUM
        FROM FILES F, PATCH_DETAIL D, PATCH_HEADER H
        WHERE F.FILE_ID = D.FILE_ID
        AND D.PATCH_ID = H.PATCH_ID
        AND F.PATH = :folder
        AND H.TEMP_YN = 'N'
        AND H.DELETED_YN = 'N'
        ORDER BY D.VERSION DESC
        """
        return self.execute_query(sql, {'folder': folder})

    def create_patch_header(self, patch_prefixe:str , patch_version:str, patch_desc: str, username: str, personal: bool, major:int, minor:int, revision:int) -> int:
        sql = "SELECT MAX(PATCH_ID) AS MAX_ID FROM PATCH_HEADER"
        result = self.execute_query(sql)
        patch_id = (result[0]['MAX_ID'] or 0) + 1
        sql = """
        INSERT INTO PATCH_HEADER (PATCH_ID, NAME, COMMENTS, TEMP_YN, USER_ID, APPLICATION_ID, MAJOR, MINOR, REVISION)
        VALUES (:patch_id, :patch_name, :comments, :temp_yn, :user_id, :application_id, :major, :minor, :revision)
        """
        self.execute_non_query(sql, {
            'patch_id': patch_id,
            'patch_name': patch_prefixe + patch_version,
            'comments': patch_desc,
            'temp_yn': 'Y' if personal else 'N',
            'user_id': username,
            'application_id': self.get_application_id(patch_prefixe),
            'major': major,
            'minor': minor,
            'revision': revision
        })
        return patch_id
    

    def update_patch_header(self, patch_id: int, patch_version_prefixe: str, patch_version: str,comments: str) -> int:
        sql = """
        UPDATE PATCH_HEADER SET NAME = :patch_name, COMMENTS = :comments, CREATION_DATE = SYSDATE
        WHERE PATCH_ID = :patch_id
        """
        self.execute_non_query(sql, {'patch_name': patch_version_prefixe + patch_version, 'comments': comments, 'patch_id': patch_id})
        # sql = "DELETE FROM PATCH_DETAIL WHERE PATCH_ID = :patch_id"
        # self.execute_non_query(sql, {'patch_id': patch_id})
        return patch_id

    def delete_patch_detail(self, patch_id: int):
        #delete patch detail
        sql = "DELETE FROM PATCH_DETAIL WHERE PATCH_ID = :patch_id"
        self.execute_non_query(sql, {'patch_id': patch_id})

    def update_comment(self, patch_id: int, comments: str):
        sql = "UPDATE PATCH_HEADER SET COMMENTS = :comments WHERE PATCH_ID = :patch_id"
        self.execute_non_query(sql, {'comments': comments, 'patch_id': patch_id})

    def create_patch_detail(self, patch_id: int, folder: str, name: str, version: int):
        file_id = self.add_file(folder, name)
        sql = "INSERT INTO PATCH_DETAIL (PATCH_ID, FILE_ID, VERSION) VALUES (:patch_id, :file_id, :version)"
        self.execute_non_query(sql, {'patch_id': patch_id, 'file_id': file_id, 'version': version})
        return file_id
    
    def get_patch_list(self, temp_yn: bool, application_id: str):
        sql = """
        SELECT H.PATCH_ID, H.NAME, H.COMMENTS, DECODE(D.PATCH_ID, NULL, 0, COUNT(*)) AS PATCH_SIZE, H.USER_ID, H.CREATION_DATE,
        CHECKLIST_COUNT(H.PATCH_ID) AS CHECK_LIST_COUNT
        FROM PATCH_HEADER H, PATCH_DETAIL D
        WHERE H.PATCH_ID = D.PATCH_ID (+)
        AND DELETED_YN = 'N'
        """
        sql += f"AND TEMP_YN = '{'Y' if temp_yn else 'N'}'"
        sql += f"AND APPLICATION_ID = '{self.get_application_id(application_id)}'"

        sql += """
        GROUP BY H.PATCH_ID, D.PATCH_ID, H.NAME, H.COMMENTS, H.USER_ID, H.CREATION_DATE
        ORDER BY PATCH_ID DESC
        """
        return self.execute_query(sql)

    def get_patch_content(self, patch_id: int):
        sql = """
        SELECT DECODE(UPPER(SUBSTR(F.NAME, INSTR(F.NAME, '.', -1) + 1, 100), 'PKS', 0, 'PRC', 1, 'FNC', 2, 'PKB', 3, 4) AS FILE_ORDER,
        D.PATCH_ID, D.FILE_ID, D.VERSION, F.PATH, F.NAME, F.DELETED_YN, H.COMMENTS, H.USER_ID, H.CREATION_DATE, D.MD5_CHECKSUM
        FROM PATCH_DETAIL D, FILES F, PATCH_HEADER H
        WHERE D.FILE_ID = F.FILE_ID
        AND D.PATCH_ID = H.PATCH_ID
        AND D.PATCH_ID = :patch_id
        ORDER BY PATH, FILE_ORDER
        """
        return self.execute_query(sql, {'patch_id': patch_id})

    def get_all_patch_content(self):
        sql = """
        SELECT DECODE(UPPER(SUBSTR(F.NAME, INSTR(F.NAME, '.', -1) + 1, 100), 'PKS', 0, 'PRC', 1, 'FNC', 2, 'PKB', 3, 4) AS FILE_ORDER,
        D.PATCH_ID, D.FILE_ID, D.VERSION, F.PATH, F.NAME, F.DELETED_YN, H.COMMENTS, H.USER_ID, H.CREATION_DATE
        FROM PATCH_DETAIL D, FILES F, PATCH_HEADER H
        WHERE D.FILE_ID = F.FILE_ID
        AND D.PATCH_ID = H.PATCH_ID
        AND MD5_CHECKSUM IS NULL
        AND H.DELETED_YN = 'N'
        AND H.TEMP_YN = 'N'
        ORDER BY H.PATCH_ID DESC, PATH, FILE_ORDER
        """
        return self.execute_query(sql)

    def remove_patch(self, patch_id: int):
        sql = "UPDATE PATCH_HEADER SET DELETED_YN = 'Y' WHERE PATCH_ID = :patch_id"
        self.execute_non_query(sql, {'patch_id': patch_id})

    def rename_patch(self, patch_id: int, new_name: str):
        sql = "UPDATE PATCH_HEADER SET NAME = :new_name WHERE PATCH_ID = :patch_id"
        self.execute_non_query(sql, {'new_name': new_name, 'patch_id': patch_id})

    def get_application_id(self, application_id: str) -> str:
        sql = f"SELECT APPLICATION_ID FROM MODULE WHERE PREFIX = '{application_id}'"
        result = self.execute_query(sql)
        if result:
            return str(result[0]['APPLICATION_ID']).strip()
        else:
            raise ValueError(f"Application ID '{application_id}' not found in the database.")

    def get_max_version(self, application_id: str):
        application_id = self.get_application_id(application_id)
        sql = f"SELECT MAJOR, MINOR FROM CURRENT_VERSION WHERE APPLICATION_ID = '{application_id}'"
        result = self.execute_query(sql)
        major, minor = (result[0]['MAJOR'], result[0]['MINOR']) if result else (1, 0)
        sql = f"""
        SELECT NVL(MAX(REVISION), 0) AS REVISION, NVL(MAX(MAJOR), :major) AS MAJOR, NVL(MAX(MINOR), :minor) AS MINOR
        FROM PATCH_HEADER
        WHERE DELETED_YN = 'N' AND TEMP_YN = 'N'
        AND MAJOR = :major AND MINOR = :minor
        AND APPLICATION_ID = '{application_id}'
        """
        return self.execute_query(sql, {'major': major, 'minor': minor})

    def get_build_list(self, patch_id: int):
        sql = """
        SELECT DISTINCT PATH, NAME, VERSION
        FROM FILES F, PATCH_DETAIL PD
        WHERE F.FILE_ID = PD.FILE_ID
        AND PATCH_ID = (SELECT MAX(PH.PATCH_ID)
                        FROM PATCH_DETAIL PD2, PATCH_HEADER PH
                        WHERE PD2.FILE_ID = PD.FILE_ID
                        AND PD2.PATCH_ID = PH.PATCH_ID
                        AND PH.TEMP_YN = 'N'
                        AND PH.DELETED_YN = 'N'
                        AND PH.PATCH_ID <= :patch_id)
        AND DELETED_YN = 'N'
        UNION
        SELECT PATH, NAME, TO_NUMBER(NULL) AS VERSION
        FROM FILES F
        WHERE NOT EXISTS (SELECT * FROM PATCH_DETAIL PD, PATCH_HEADER PH
                          WHERE F.FILE_ID = PD.FILE_ID
                          AND PD.PATCH_ID = PH.PATCH_ID
                          AND PH.TEMP_YN = 'N'
                          AND PH.DELETED_YN = 'N'
                          AND PH.PATCH_ID <= :patch_id)
        AND DELETED_YN = 'N'
        """
        return self.execute_query(sql, {'patch_id': patch_id})

    def set_md5(self, patch_id: int, file_id: int, checksum: str):
        sql = "UPDATE PATCH_DETAIL SET MD5_CHECKSUM = :checksum WHERE PATCH_ID = :patch_id AND FILE_ID = :file_id"
        self.execute_non_query(sql, {'checksum': checksum, 'patch_id': patch_id, 'file_id': file_id})

    def get_patch_file_list(self, patch_id: int):
        sql = """
        SELECT FOLDER_TYPE, SUBSTR(F.PATH, LENGTH(R.PATH) + 1) AS PATH, F.NAME, D.VERSION, D.PATCH_ID
        FROM PATCH_DETAIL D, FILES F, FOLDER R
        WHERE D.FILE_ID = F.FILE_ID
        AND D.PATCH_ID = :patch_id
        AND SUBSTR(F.PATH, 1, LENGTH(R.PATH)) = R.PATH
        ORDER BY R.FOLDER_TYPE, F.PATH
        """
        return self.execute_query(sql, {'patch_id': patch_id})

    def get_patch_doc_comment(self, patch_id: int):
        sql = """
        SELECT TRIM(NAME) AS NAME, USER_ID, '""' || REPLACE(COMMENTS, CHR(13) || CHR(10), CHR(10)) || '""' AS COMMENTS, PATCH_ID
        FROM PATCH_HEADER
        WHERE PATCH_ID >= :patch_id
        AND DELETED_YN <> 'Y'
        AND TEMP_YN = 'N'
        ORDER BY PATCH_ID
        """
        return self.execute_query(sql, {'patch_id': patch_id})

    def get_check_list(self, patch_id: int):
        sql = """
        SELECT P.PATCH_ID, P.FILE_ID, P.VERSION, F.CHECKLIST_ID, F.CREATION_DATE, D.ITEM_VALUE, FL.NAME AS FILENAME
        FROM PATCH_CHECKLIST F, PATCH_CHECKLIST_DETAIL D, PATCH_DETAIL P, FILES FL
        WHERE P.PATCH_ID = :patch_id
        AND P.PATCH_ID = F.PATCH_ID (+)
        AND P.FILE_ID = F.FILE_ID (+)
        AND P.VERSION = F.VERSION (+)
        AND F.CHECKLIST_ID = D.CHECKLIST_ID (+)
        AND P.FILE_ID = FL.FILE_ID
        """
        return self.execute_query(sql, {'patch_id': patch_id})

    def get_check_item(self):
        sql = "SELECT ITEM_ID, DISPLAY_ORDER, FILE_TYPE, ITEM_DESC, CONTENT_TYPE FROM CHECKLIST"
        return self.execute_query(sql)

    def get_prefix_list(self):
        sql = "SELECT PREFIX FROM MODULE"
        list = self.execute_query(sql)
        return [item['PREFIX'] for item in list]

    def __del__(self):
        self.close()