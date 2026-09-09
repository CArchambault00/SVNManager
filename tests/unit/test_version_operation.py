"""Unit tests for version_operation."""

from unittest.mock import MagicMock, patch

import pytest

from version_operation import VersionInfo, next_version, parse_version, set_current_version


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1.0.0953-W0", (1, 0, 953)),
        ("S1.0.0953-W0", (1, 0, 953)),
        ("1.0.0953-", (1, 0, 953)),
        ("2.3.0001-S0", (2, 3, 1)),
        ("", None),
        ("not-a-version", None),
        ("1.2", None),
    ],
)
def test_parse_version(raw, expected):
    result = parse_version(raw)
    if expected is None:
        assert result is None
    else:
        assert result is not None
        assert (result.major, result.minor, result.revision) == expected


def test_parse_version_none():
    assert parse_version(None) is None  # type: ignore[arg-type]


def test_version_info_str_zero_pads_revision():
    assert str(VersionInfo(1, 2, 3)) == "1.2.0003-"


def test_set_current_version_updates_globals():
    import version_operation as vo

    set_current_version(VersionInfo(9, 8, 7))
    assert vo.major == 9
    assert vo.minor == 8
    assert vo.revision == 7
    assert str(vo.current_version) == "9.8.0007-"


def test_next_version_with_mock_db(mock_messagebox):
    fake = MagicMock()
    fake.get_max_version.return_value = [{"MAJOR": 1, "MINOR": 0, "REVISION": 50}]

    with patch("version_operation.dbClass", return_value=fake):
        result = next_version("CORE")

    assert result == "1.0.0051-"


def test_next_version_returns_none_when_db_empty(mock_messagebox):
    fake = MagicMock()
    fake.get_max_version.return_value = []

    with patch("version_operation.dbClass", return_value=fake):
        assert next_version("CORE") is None
    mock_messagebox.showerror.assert_called()
