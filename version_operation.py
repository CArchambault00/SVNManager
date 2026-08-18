from dataclasses import dataclass
import re
from typing import Optional
from tkinter import messagebox
from db_handler import dbClass

@dataclass
class VersionInfo:
    """Represents version information for patches."""
    major: int = 0
    minor: int = 0
    revision: int = 0

    def __str__(self) -> str:
        """Format version as string like '1.2.0003-'"""
        return f"{self.major}.{self.minor}.{str(self.revision).zfill(4)}-"


# Global version state
current_version = VersionInfo()

# Module level exports for backward compatibility
major = 0
minor = 0
revision = 0


def parse_version(patch_version: str) -> Optional[VersionInfo]:
    """
    Parse a patch version string into VersionInfo.

    Accepts values such as '1.0.0953-W0', 'S1.0.0953-W0', or '1.0.0953-'.
    """
    if not patch_version:
        return None

    version_core = patch_version.split("-")[0]
    version_core = re.sub(r"^[A-Za-z]+", "", version_core)
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_core)
    if not match:
        return None

    return VersionInfo(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def set_current_version(info: VersionInfo) -> None:
    """Keep global version state in sync with the version actually being saved."""
    global major, minor, revision
    current_version.major = info.major
    current_version.minor = info.minor
    current_version.revision = info.revision
    major = info.major
    minor = info.minor
    revision = info.revision


def next_version(application_id: str) -> Optional[str]:
    """
    Calculate the next version number for the given application.

    Args:
        application_id: The application identifier

    Returns:
        Formatted version string or None if retrieval failed
    """
    try:
        db = dbClass()
        max_version = db.get_max_version(application_id)
        if not max_version:
            messagebox.showerror("Error", "Failed to retrieve the max version")
            return None

        set_current_version(VersionInfo(
            max_version[0]["MAJOR"],
            max_version[0]["MINOR"],
            max_version[0]["REVISION"] + 1,
        ))

        return str(current_version)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to calculate next version: {e}")
        return None