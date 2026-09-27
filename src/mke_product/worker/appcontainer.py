"""AppContainer profile, staging, and pre-resume token verification.

The manager deliberately grants the worker SID read/execute access only to a
small staged Python runtime and the MKE Python sources.  Profile deletion is
lease-gated so it cannot race a live or termination-uncertain worker.
"""

from __future__ import annotations

import atexit
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from ctypes import wintypes
from pathlib import Path
from typing import Any, Dict, Optional

if sys.platform != "win32":
    raise ImportError("AppContainer worker support requires Windows.")

from .constants import (
    ERROR_INSUFFICIENT_BUFFER,
    TOKEN_QUERY,
    TokenAppContainerSid,
    TokenElevation,
    TokenIsAppContainer,
)


class SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]


class SECURITY_CAPABILITIES(ctypes.Structure):
    _fields_ = [
        ("AppContainerSid", ctypes.c_void_p),
        ("Capabilities", ctypes.POINTER(SID_AND_ATTRIBUTES)),
        ("CapabilityCount", wintypes.DWORD),
        ("Reserved", wintypes.DWORD),
    ]


class TOKEN_ELEVATION(ctypes.Structure):
    _fields_ = [("TokenIsElevated", wintypes.DWORD)]


class TOKEN_APPCONTAINER_INFORMATION(ctypes.Structure):
    _fields_ = [("TokenAppContainer", ctypes.c_void_p)]


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
userenv = ctypes.WinDLL("userenv", use_last_error=True)

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.LocalFree.argtypes = [ctypes.c_void_p]
kernel32.LocalFree.restype = ctypes.c_void_p
advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
advapi32.OpenProcessToken.restype = wintypes.BOOL
advapi32.GetTokenInformation.argtypes = [
    wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
advapi32.GetTokenInformation.restype = wintypes.BOOL
advapi32.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
advapi32.EqualSid.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
advapi32.EqualSid.restype = wintypes.BOOL
advapi32.IsValidSid.argtypes = [ctypes.c_void_p]
advapi32.IsValidSid.restype = wintypes.BOOL
advapi32.FreeSid.argtypes = [ctypes.c_void_p]
advapi32.FreeSid.restype = ctypes.c_void_p
userenv.CreateAppContainerProfile.argtypes = [
    wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
    ctypes.POINTER(SID_AND_ATTRIBUTES), wintypes.DWORD,
    ctypes.POINTER(ctypes.c_void_p),
]
userenv.CreateAppContainerProfile.restype = ctypes.c_long
userenv.DeleteAppContainerProfile.argtypes = [wintypes.LPCWSTR]
userenv.DeleteAppContainerProfile.restype = ctypes.c_long


def _u32(value: int) -> int:
    return ctypes.c_uint32(value).value


def _sid_text(sid: ctypes.c_void_p) -> str:
    raw = wintypes.LPWSTR()
    if not sid or not advapi32.ConvertSidToStringSidW(sid, ctypes.byref(raw)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return raw.value
    finally:
        kernel32.LocalFree(raw)


def verify_appcontainer_process_token(
    process: wintypes.HANDLE,
    expected_sid: ctypes.c_void_p,
    *,
    inject_token_mismatch: bool = False,
    inject_sid_mismatch: bool = False,
) -> Dict[str, Any]:
    """Return native token evidence used as a mandatory pre-resume gate."""
    evidence: Dict[str, Any] = {
        "query_ok": False,
        "is_appcontainer": False,
        "sid_matches_profile": False,
        "elevated": None,
        "verified_before_resume": True,
    }
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(process, TOKEN_QUERY, ctypes.byref(token)):
        evidence["query_error"] = ctypes.get_last_error()
        return evidence
    try:
        returned = wintypes.DWORD()
        is_ac = wintypes.DWORD()
        app_ok = bool(advapi32.GetTokenInformation(
            token, TokenIsAppContainer, ctypes.byref(is_ac), ctypes.sizeof(is_ac), ctypes.byref(returned)
        ))
        app_error = 0 if app_ok else ctypes.get_last_error()

        elevation = TOKEN_ELEVATION()
        elevation_ok = bool(advapi32.GetTokenInformation(
            token, TokenElevation, ctypes.byref(elevation), ctypes.sizeof(elevation), ctypes.byref(returned)
        ))
        elevation_error = 0 if elevation_ok else ctypes.get_last_error()

        needed = wintypes.DWORD()
        ctypes.set_last_error(0)
        advapi32.GetTokenInformation(token, TokenAppContainerSid, None, 0, ctypes.byref(needed))
        probe_error = ctypes.get_last_error()
        sid_ok = False
        sid_matches = False
        actual_sid_text = ""
        sid_error = probe_error
        if needed.value and probe_error == ERROR_INSUFFICIENT_BUFFER:
            buffer = ctypes.create_string_buffer(needed.value)
            sid_ok = bool(advapi32.GetTokenInformation(
                token, TokenAppContainerSid, buffer, needed.value, ctypes.byref(returned)
            ))
            sid_error = 0 if sid_ok else ctypes.get_last_error()
            if sid_ok:
                info = ctypes.cast(buffer, ctypes.POINTER(TOKEN_APPCONTAINER_INFORMATION)).contents
                actual_sid_text = _sid_text(info.TokenAppContainer)
                sid_matches = bool(advapi32.EqualSid(info.TokenAppContainer, expected_sid))

        is_appcontainer = bool(is_ac.value) and not inject_token_mismatch
        sid_matches = sid_matches and not inject_sid_mismatch
        elevated = bool(elevation.TokenIsElevated) if elevation_ok else None
        evidence.update({
            "query_ok": bool(app_ok and elevation_ok and sid_ok),
            "query_error": app_error or elevation_error or sid_error,
            "is_appcontainer": is_appcontainer,
            "appcontainer_sid": actual_sid_text,
            "sid_matches_profile": sid_matches,
            "elevated": elevated,
        })
        evidence["accepted"] = bool(
            evidence["query_ok"] and is_appcontainer and sid_matches and elevated is False
        )
        return evidence
    finally:
        kernel32.CloseHandle(token)


class AppContainerLease:
    def __init__(self, manager: "AppContainerManager") -> None:
        self._manager = manager
        self._released = False

    def release(self) -> None:
        if not self._released:
            self._released = True
            self._manager._release()


class AppContainerManager:
    """Lazily creates one process-local profile and immutable staged worker."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.profile_name = f"mke.product.worker.p1.{os.getpid()}.{uuid.uuid4().hex[:12]}"
        self.sid = ctypes.c_void_p()
        self.sid_string = ""
        self.stage_root: Optional[Path] = None
        self.python_exe: Optional[Path] = None
        self.bootstrap: Optional[Path] = None
        self._prepared = False
        self._active_children = 0
        self._last_cleanup: Dict[str, Any] = {"state": "NOT_ATTEMPTED"}

    @property
    def active_children(self) -> int:
        with self._lock:
            return self._active_children

    def prepare(self) -> None:
        with self._lock:
            if self._prepared:
                return
            hr = userenv.CreateAppContainerProfile(
                self.profile_name, "MKE P1 disposable worker", "MKE P1 disposable worker",
                None, 0, ctypes.byref(self.sid),
            )
            if hr != 0:
                raise OSError(_u32(hr), "CreateAppContainerProfile failed")
            try:
                if not self.sid or not advapi32.IsValidSid(self.sid):
                    raise OSError("CreateAppContainerProfile returned an invalid SID")
                self.sid_string = _sid_text(self.sid)
                root = Path(tempfile.mkdtemp(prefix="mke-s4b2-p1-"))
                self.stage_root = root
                runtime = root / "runtime"
                source = root / "src"
                runtime.mkdir()
                source.mkdir()
                self._stage_runtime(Path(sys.executable).resolve().parent, runtime)
                source_package = Path(__file__).resolve().parents[1]
                for item in source_package.rglob("*.py"):
                    relative = item.relative_to(source_package.parent)
                    target = source / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)
                bootstrap = root / "worker_bootstrap.py"
                bootstrap.write_text(
                    "import sys\n"
                    f"sys.path.insert(0, {str(source)!r})\n"
                    "from mke_product.worker.entrypoint import run_worker\n"
                    "raise SystemExit(run_worker())\n",
                    encoding="utf-8",
                )
                self._grant_read_execute(root)
                self.python_exe = runtime / Path(sys.executable).name
                self.bootstrap = bootstrap
                self._prepared = True
            except Exception:
                self._cleanup_created_state()
                raise

    def _stage_runtime(self, source: Path, destination: Path) -> None:
        for item in source.iterdir():
            if item.is_file() and (
                item.name.lower() == Path(sys.executable).name.lower()
                or item.name.lower().startswith("python") and item.suffix.lower() == ".dll"
                or item.name.lower().startswith("vcruntime") and item.suffix.lower() == ".dll"
            ):
                shutil.copy2(item, destination / item.name)
        shutil.copytree(source / "DLLs", destination / "DLLs")
        ignored = shutil.ignore_patterns(
            "site-packages", "__pycache__", "ensurepip", "idlelib", "test", "tests",
            "tkinter", "turtledemo", "venv",
        )
        shutil.copytree(source / "Lib", destination / "Lib", ignore=ignored)

    def _grant_read_execute(self, path: Path) -> None:
        ace = f"*{self.sid_string}:(OI)(CI)RX"
        proc = subprocess.run(
            ["icacls.exe", str(path), "/grant:r", ace, "/T", "/C", "/Q"],
            text=True, capture_output=True,
        )
        if proc.returncode != 0:
            raise OSError(f"icacls failed ({proc.returncode}): {proc.stderr.strip()}")

    def acquire(self) -> AppContainerLease:
        self.prepare()
        with self._lock:
            self._active_children += 1
        return AppContainerLease(self)

    def _release(self) -> None:
        with self._lock:
            if self._active_children <= 0:
                raise RuntimeError("AppContainer lease underflow")
            self._active_children -= 1

    def security_capabilities(self) -> SECURITY_CAPABILITIES:
        self.prepare()
        return SECURITY_CAPABILITIES(self.sid, None, 0, 0)

    def default_command(self) -> str:
        self.prepare()
        return subprocess.list2cmdline([str(self.python_exe), "-I", "-S", "-B", str(self.bootstrap)])

    def rewrite_python_command(self, command: str) -> str:
        self.prepare()
        old = f'"{sys.executable}"'
        if command.lower().startswith(old.lower()):
            return f'"{self.python_exe}" -I -S -B' + command[len(old):]
        if command.lower().startswith(sys.executable.lower()):
            return f'"{self.python_exe}" -I -S -B' + command[len(sys.executable):]
        raise ValueError("Custom worker command must use the allowlisted current Python executable")

    def environment_block(self) -> Any:
        """Build a minimal deterministic Unicode environment for the worker."""
        self.prepare()
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        values = {
            "PATH": str(self.python_exe.parent),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "SystemRoot": system_root,
            "WINDIR": system_root,
        }
        # Windows profile/AppContainer initialization consumes these standard
        # locations.  Copy only this explicit allowlist; the AppContainer DACL
        # still prevents access to the caller's profile and temp directories.
        for key in (
            "ALLUSERSPROFILE", "APPDATA", "COMSPEC", "HOMEDRIVE", "HOMEPATH",
            "LOCALAPPDATA", "PROGRAMDATA", "TEMP", "TMP", "USERPROFILE",
        ):
            value = os.environ.get(key)
            if value:
                values[key] = value
        serialized = "\0".join(f"{key}={values[key]}" for key in sorted(values, key=str.upper)) + "\0\0"
        return ctypes.create_unicode_buffer(serialized)

    def cleanup(self) -> Dict[str, Any]:
        with self._lock:
            if self._active_children:
                self._last_cleanup = {
                    "state": "REFUSED_ACTIVE_CHILDREN",
                    "active_children": self._active_children,
                    "profile_name": self.profile_name,
                }
                return dict(self._last_cleanup)
            self._cleanup_created_state()
            return dict(self._last_cleanup)

    def _cleanup_created_state(self) -> None:
        stage_removed = True
        if self.stage_root is not None:
            try:
                shutil.rmtree(self.stage_root)
            except OSError:
                stage_removed = False
        delete_hr = 0
        if self.sid:
            delete_hr = userenv.DeleteAppContainerProfile(self.profile_name)
            advapi32.FreeSid(self.sid)
        self.sid = ctypes.c_void_p()
        self.sid_string = ""
        self.stage_root = None
        self.python_exe = None
        self.bootstrap = None
        self._prepared = False
        self._last_cleanup = {
            "state": "CLEANED" if stage_removed and delete_hr == 0 else "CLEANUP_FAILED",
            "stage_removed": stage_removed,
            "delete_hresult": _u32(delete_hr),
            "active_children": self._active_children,
            "profile_name": self.profile_name,
        }


_manager = AppContainerManager()


def get_appcontainer_manager() -> AppContainerManager:
    return _manager


def cleanup_appcontainer_runtime() -> Dict[str, Any]:
    return _manager.cleanup()


atexit.register(cleanup_appcontainer_runtime)
