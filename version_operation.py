from dataclasses import dataclass
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
        print(f"Max version retrieved: {max_version}")
        if not max_version:
            messagebox.showerror("Error", "Failed to retrieve the max version")
            return None

        # Update global version state
        current_version.major = max_version[0]["MAJOR"]
        current_version.minor = max_version[0]["MINOR"]
        current_version.revision = max_version[0]["REVISION"] + 1

        # Update module level exports
        global major, minor, revision
        major = current_version.major
        minor = current_version.minor
        revision = current_version.revision

        return str(current_version)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to calculate next version: {e}")
        return None