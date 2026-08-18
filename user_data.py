import os
import sys
import shutil
from typing import List, Optional

APP_FOLDER_NAME = "SVNManager"
CONFIG_FILENAME = "svn_config.json"
PROFILES_FILENAME = "svn_profiles.json"
ERROR_LOG_FILENAME = "SVNManager_error.log"
SUCCESS_LOG_FILENAME = "SVNManager_success.log"
MARKER_FILENAME = "settings_ready.flag"

_migrated_sources = []
_initialized = False


def get_install_dir() -> str:
    """Folder containing the running exe (frozen) or this source file."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_user_data_dir() -> str:
    """Persistent settings folder: %APPDATA%\\SVNManager."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    path = os.path.join(appdata, APP_FOLDER_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _legacy_search_dirs() -> List[str]:
    dirs = []
    install_dir = get_install_dir()
    parent_dir = os.path.dirname(install_dir)
    for candidate in (install_dir, os.path.abspath("."), parent_dir):
        if candidate and candidate not in dirs:
            dirs.append(candidate)
    return dirs


def _migrate_file(filename: str, dest_dir: str, track: bool = False) -> str:
    dest = os.path.join(dest_dir, filename)
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        return dest

    dest_abs = os.path.abspath(dest)
    for folder in _legacy_search_dirs():
        src = os.path.abspath(os.path.join(folder, filename))
        if src == dest_abs or not os.path.isfile(src) or os.path.getsize(src) == 0:
            continue
        shutil.copy2(src, dest)
        if track:
            _migrated_sources.append(src)
        return dest
    return dest


def ensure_user_data() -> str:
    """Create the AppData folder and copy any leftover next-to-exe settings into it."""
    global _initialized
    dest_dir = get_user_data_dir()
    if _initialized:
        return dest_dir

    _migrate_file(CONFIG_FILENAME, dest_dir, track=True)
    _migrate_file(PROFILES_FILENAME, dest_dir, track=True)
    _migrate_file(ERROR_LOG_FILENAME, dest_dir)
    _migrate_file(SUCCESS_LOG_FILENAME, dest_dir)

    _initialized = True
    return dest_dir


def has_user_settings() -> bool:
    config_path = os.path.join(get_user_data_dir(), CONFIG_FILENAME)
    profiles_path = os.path.join(get_user_data_dir(), PROFILES_FILENAME)
    return (
        os.path.isfile(config_path) and os.path.getsize(config_path) > 0
    ) or (
        os.path.isfile(profiles_path) and os.path.getsize(profiles_path) > 0
    )


def mark_settings_ready() -> None:
    marker = os.path.join(get_user_data_dir(), MARKER_FILENAME)
    with open(marker, "w", encoding="utf-8") as f:
        f.write("1")


def should_prompt_for_legacy_settings() -> bool:
    """Ask once, only in the packaged app, if AppData has no settings yet."""
    if not getattr(sys, "frozen", False):
        return False
    if has_user_settings() or _migrated_sources:
        return False
    marker = os.path.join(get_user_data_dir(), MARKER_FILENAME)
    return not os.path.isfile(marker)


def _find_settings_file(folder: str, filename: str, max_depth: int = 2) -> Optional[str]:
    """Find filename in folder, then in subfolders a couple of levels down."""
    folder = os.path.abspath(folder)
    direct = os.path.join(folder, filename)
    if os.path.isfile(direct) and os.path.getsize(direct) > 0:
        return direct

    for root, dirs, files in os.walk(folder):
        rel = os.path.relpath(root, folder)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth > max_depth:
            dirs[:] = []
            continue
        if filename in files:
            path = os.path.join(root, filename)
            if os.path.isfile(path) and os.path.getsize(path) > 0:
                return path
    return None


def import_from_folder(folder: str) -> List[str]:
    """Copy svn_config.json / svn_profiles.json from an old folder into AppData.

    After this copy, the app only reads and writes the AppData copies.
    The original files can be deleted.
    """
    imported = []
    dest_dir = get_user_data_dir()
    for filename in (CONFIG_FILENAME, PROFILES_FILENAME):
        dest = os.path.join(dest_dir, filename)
        if os.path.isfile(dest) and os.path.getsize(dest) > 0:
            continue
        src = _find_settings_file(folder, filename)
        if not src:
            continue
        if os.path.abspath(src) == os.path.abspath(dest):
            continue
        shutil.copy2(src, dest)
        imported.append(src)
        _migrated_sources.append(src)
    return imported


def get_migration_message() -> Optional[str]:
    """One-time notice after settings were copied out of the old install folder."""
    if not _migrated_sources:
        return None
    data_dir = get_user_data_dir()
    return (
        "Your SVN Manager settings were copied to:\n\n"
        f"{data_dir}\n\n"
        "The app will always use this copy from now on — including after you "
        "delete the original JSON files, reopen the app, or download a new release."
    )


USER_DATA_DIR = ensure_user_data()
CONFIG_FILE = os.path.join(USER_DATA_DIR, CONFIG_FILENAME)
PROFILES_FILE = os.path.join(USER_DATA_DIR, PROFILES_FILENAME)
ERROR_LOG_FILE = os.path.join(USER_DATA_DIR, ERROR_LOG_FILENAME)
SUCCESS_LOG_FILE = os.path.join(USER_DATA_DIR, SUCCESS_LOG_FILENAME)
