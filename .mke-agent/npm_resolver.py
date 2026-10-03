"""Consistent npm executable resolver for Windows and POSIX environments."""
from __future__ import annotations

import os
import shutil
from pathlib import Path


class NpmResolverError(RuntimeError):
    """Raised when no valid npm executable can be resolved."""
    pass


def resolve_npm(error_cls: type[Exception] = NpmResolverError) -> str:
    """Resolve the absolute path to the npm executable.

    Uses shutil.which, checks Windows executable extensions (npm.cmd, npm.bat, npm.exe),
    resolves the full executable path, and fails closed with error_cls if no executable is found.
    """
    candidates = ["npm.cmd", "npm.bat", "npm.exe", "npm"] if os.name == "nt" else ["npm", "npm.cmd", "npm.bat"]
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return os.path.abspath(found)
    found = shutil.which("npm")
    if found:
        return os.path.abspath(found)
    raise error_cls("npm is required for frontend build but was not found on PATH.")
