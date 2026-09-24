"""Unit tests for db_handler connection behavior."""

from unittest.mock import MagicMock, patch

import pytest


def test_connect_prefers_thick_when_instant_client_present(
    tmp_appdata, sample_config, mock_messagebox, monkeypatch
):
    import db_handler as dbh

    fake_conn = MagicMock()
    init = MagicMock()
    connect = MagicMock(return_value=fake_conn)

    monkeypatch.setattr(dbh, "_find_instant_client", MagicMock(return_value="C:/ic/instantclient_12_1"))
    monkeypatch.setattr(dbh.oracledb, "init_oracle_client", init)
    monkeypatch.setattr(dbh.oracledb, "connect", connect)

    db = dbh.dbClass()

    assert db.conn is fake_conn
    init.assert_called_once_with(lib_dir="C:/ic/instantclient_12_1")
    connect.assert_called_once()


def test_connect_falls_back_to_thin_without_client(
    tmp_appdata, sample_config, mock_messagebox, monkeypatch
):
    import db_handler as dbh

    fake_conn = MagicMock()
    init = MagicMock()
    connect = MagicMock(return_value=fake_conn)

    monkeypatch.setattr(dbh, "_find_instant_client", MagicMock(return_value=None))
    monkeypatch.setattr(dbh.oracledb, "init_oracle_client", init)
    monkeypatch.setattr(dbh.oracledb, "connect", connect)

    db = dbh.dbClass()

    assert db.conn is fake_conn
    init.assert_not_called()
    connect.assert_called_once()


def test_connect_failure_leaves_conn_none(tmp_appdata, sample_config, mock_messagebox, monkeypatch):
    import db_handler as dbh

    monkeypatch.setattr(dbh, "_find_instant_client", MagicMock(return_value=None))
    monkeypatch.setattr(
        dbh.oracledb,
        "connect",
        MagicMock(side_effect=dbh.oracledb.Error("boom")),
    )

    db = dbh.dbClass()
    assert db.conn is None
    mock_messagebox.showerror.assert_called()


def test_execute_query_requires_connection(tmp_appdata, sample_config, mock_messagebox, monkeypatch):
    import db_handler as dbh

    monkeypatch.setattr(dbh, "_find_instant_client", MagicMock(return_value=None))
    monkeypatch.setattr(
        dbh.oracledb,
        "connect",
        MagicMock(side_effect=dbh.oracledb.Error("boom")),
    )

    db = dbh.dbClass()
    with pytest.raises(dbh.DatabaseError, match="Not connected"):
        db.execute_query("SELECT 1 FROM DUAL")


def test_instant_client_12_included_for_oracledb_2(monkeypatch):
    import db_handler as dbh

    monkeypatch.setattr(dbh.oracledb, "__version__", "2.5.1")
    folders = dbh._instant_client_folders()
    assert "instantclient_12_1" in folders


def test_instant_client_12_excluded_for_oracledb_4(monkeypatch):
    import db_handler as dbh

    monkeypatch.setattr(dbh.oracledb, "__version__", "4.0.2")
    folders = dbh._instant_client_folders()
    assert "instantclient_12_1" not in folders
