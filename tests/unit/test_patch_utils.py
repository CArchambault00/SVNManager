"""Unit tests for patch_utils mapping and file helpers."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from patch_utils import (
    MAIN_SQL_FILENAME,
    _next_main_sql_backup_index,
    backup_existing_main_sql,
    backup_extra_patch_files,
    create_main_sql_file,
    create_readme_file,
    extract_build_number,
    get_managed_dest_paths,
    get_md5_checksum,
    map_db_file_to_patch_dest,
    map_svn_file_to_patch_dest,
    restore_extra_patch_files,
)


def test_get_md5_checksum(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"hello")
    assert get_md5_checksum(str(f)) == "5d41402abc4b2a76b9719d911017c592"


def test_map_svn_file_to_patch_dest_webpage():
    assert map_svn_file_to_patch_dest("webpage/foo/bar.asp") == "Web/foo/bar.asp"


def test_map_svn_file_to_patch_dest_database():
    assert (
        map_svn_file_to_patch_dest("Database/SCHEMA/StoredProcedures/pkg.pks")
        == "DB/SCHEMA/SP/pkg.pks"
    )


def test_map_svn_file_to_patch_dest_unknown():
    assert map_svn_file_to_patch_dest("Other/file.txt") is None


def test_map_svn_file_strips_relative_prefix():
    with patch("patch_utils.get_relative_path", return_value="Projects/SVN"):
        dest = map_svn_file_to_patch_dest(
            "Projects/SVN/webpage/a.asp", svn_path="C:/svn/Projects/SVN"
        )
    assert dest == "Web/a.asp"


def test_map_db_file_to_patch_dest_web():
    dest = map_db_file_to_patch_dest(
        {
            "PATH": "webpage/pages/index.asp",
            "SVN_PATH": "webpage",
            "FOLDER_TYPE": "1",
            "NAME": "index.asp",
        }
    )
    assert dest == "Web/pages/index.asp"


def test_map_db_file_to_patch_dest_db():
    dest = map_db_file_to_patch_dest(
        {
            "PATH": "Database/FOO/StoredProcedures/x.pks",
            "SVN_PATH": "Database",
            "FOLDER_TYPE": "2",
            "NAME": "x.pks",
        }
    )
    assert dest == "DB/FOO/SP/x.pks"


def test_get_managed_dest_paths_mixed():
    paths = get_managed_dest_paths(
        [
            "webpage/a.asp",
            {
                "PATH": "Database/X/StoredProcedures/y.pkb",
                "SVN_PATH": "Database",
                "FOLDER_TYPE": "2",
                "NAME": "y.pkb",
            },
        ]
    )
    assert "Web/a.asp" in paths
    assert "DB/X/SP/y.pkb" in paths


def test_main_sql_backup_index_and_backup(tmp_path):
    folder = tmp_path / "patch"
    folder.mkdir()
    (folder / MAIN_SQL_FILENAME).write_text("old", encoding="utf-8")
    assert _next_main_sql_backup_index(str(folder)) == 1
    backup = backup_existing_main_sql(str(folder))
    assert backup is not None
    assert Path(backup).name == "MainSQL (1).sql"
    assert (folder / "MainSQL (1).sql").read_text(encoding="utf-8") == "old"
    assert _next_main_sql_backup_index(str(folder)) == 2


def test_backup_and_restore_extra_files(tmp_path):
    folder = tmp_path / "patch"
    folder.mkdir()
    (folder / "ReadMe.txt").write_text("gen", encoding="utf-8")
    extra = folder / "manual" / "note.txt"
    extra.parent.mkdir()
    extra.write_text("keep-me", encoding="utf-8")
    managed = {"Web/a.asp"}
    (folder / "Web").mkdir()
    (folder / "Web" / "a.asp").write_text("managed", encoding="utf-8")

    temp = backup_extra_patch_files(str(folder), managed)
    assert temp is not None
    assert (Path(temp) / "manual" / "note.txt").exists()

    # wipe and restore
    for child in folder.iterdir():
        if child.is_file():
            child.unlink()
        else:
            import shutil

            shutil.rmtree(child)
    restore_extra_patch_files(temp, str(folder))
    assert (folder / "manual" / "note.txt").read_text(encoding="utf-8") == "keep-me"


def test_create_readme_with_db_file_dicts(tmp_path, sample_config):
    folder = tmp_path / "out"
    folder.mkdir()
    files = [
        {
            "PATH": "webpage/a.asp",
            "VERSION": "10",
            "FOLDER_TYPE": "1",
            "NAME": "a.asp",
            "SVN_PATH": "webpage",
        },
        {
            "PATH": "Database/SCH/StoredProcedures/b.pks",
            "VERSION": "11",
            "FOLDER_TYPE": "2",
            "NAME": "b.pks",
            "SVN_PATH": "Database",
        },
    ]
    create_readme_file(str(folder), "S1.0.0001-W0", "tester", "2026-01-01", "desc", files)
    content = (folder / "ReadMe.txt").read_text(encoding="utf-8")
    assert "Patch S1.0.0001-W0" in content
    assert "webpage/a.asp (10)" in content
    assert "Database/SCH/StoredProcedures/b.pks (11)" in content


def test_create_main_sql_with_version_info(tmp_path, sample_config):
    folder = tmp_path / "out"
    folder.mkdir()
    files = [
        {
            "PATH": "/SCH/StoredProcedures/pkg.pks",
            "VERSION": "1",
            "FOLDER_TYPE": "2",
            "NAME": "pkg.pks",
            "SVN_PATH": "Database",
        },
        {
            "PATH": "/SCH/StoredProcedures/pkg.pkb",
            "VERSION": "1",
            "FOLDER_TYPE": "2",
            "NAME": "pkg.pkb",
            "SVN_PATH": "Database",
        },
    ]
    create_main_sql_file(
        str(folder), files, version_info=(1, 0, 5), application_id="CORE"
    )
    sql = (folder / "MainSQL.sql").read_text(encoding="utf-8")
    assert "connect SCH/SCH@&&HOST" in sql
    assert '@@"DB/SCH/SP/pkg.pks"' in sql
    assert '@@"DB/SCH/SP/pkg.pkb"' in sql
    assert "SETCURRENTVERSION('CORE',1,0,0005" in sql


def test_extract_build_number(mock_db):
    assert extract_build_number("S2.1.1234") == "'CORE',2,1,1234"
    assert extract_build_number("") == "'ERROR',0,0,0"
    assert extract_build_number("J1.0.0001-W0") == "'JTIME',1,0,0001"
