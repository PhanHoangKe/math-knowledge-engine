"""Minimal destructive-safe Windows AppContainer feasibility probes for S4-B2/P0."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


if sys.platform != "win32":
    raise SystemExit("This probe requires Windows.")


EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_NO_WINDOW = 0x08000000
STARTF_USESTDHANDLES = 0x00000100
PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002
PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
WAIT_OBJECT_0 = 0
ERROR_INSUFFICIENT_BUFFER = 122
HANDLE_FLAG_INHERIT = 0x00000001
STILL_ACTIVE = 259


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", ctypes.c_void_p),
        ("bInheritHandle", wintypes.BOOL),
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [("StartupInfo", STARTUPINFOW), ("lpAttributeList", ctypes.c_void_p)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]


class SECURITY_CAPABILITIES(ctypes.Structure):
    _fields_ = [
        ("AppContainerSid", ctypes.c_void_p),
        ("Capabilities", ctypes.POINTER(SID_AND_ATTRIBUTES)),
        ("CapabilityCount", wintypes.DWORD),
        ("Reserved", wintypes.DWORD),
    ]


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
userenv = ctypes.WinDLL("userenv", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

kernel32.InitializeProcThreadAttributeList.argtypes = [
    ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)
]
kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL
kernel32.UpdateProcThreadAttribute.argtypes = [
    ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t, ctypes.c_void_p,
    ctypes.c_size_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
]
kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL
kernel32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
    wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
    ctypes.c_void_p, ctypes.POINTER(PROCESS_INFORMATION),
]
kernel32.CreateProcessW.restype = wintypes.BOOL
kernel32.CreatePipe.argtypes = [
    ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE),
    ctypes.POINTER(SECURITY_ATTRIBUTES), wintypes.DWORD,
]
kernel32.CreatePipe.restype = wintypes.BOOL
kernel32.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
kernel32.SetHandleInformation.restype = wintypes.BOOL
kernel32.GetHandleInformation.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.GetHandleInformation.restype = wintypes.BOOL
kernel32.CreateEventW.argtypes = [ctypes.POINTER(SECURITY_ATTRIBUTES), wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.GetExitCodeProcess.restype = wintypes.BOOL
kernel32.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
kernel32.ReadFile.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.LocalFree.argtypes = [ctypes.c_void_p]
kernel32.LocalFree.restype = ctypes.c_void_p

userenv.CreateAppContainerProfile.argtypes = [
    wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
    ctypes.POINTER(SID_AND_ATTRIBUTES), wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p),
]
userenv.CreateAppContainerProfile.restype = ctypes.c_long
userenv.DeleteAppContainerProfile.argtypes = [wintypes.LPCWSTR]
userenv.DeleteAppContainerProfile.restype = ctypes.c_long
userenv.DeriveAppContainerSidFromAppContainerName.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
userenv.DeriveAppContainerSidFromAppContainerName.restype = ctypes.c_long
advapi32.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
advapi32.IsValidSid.argtypes = [ctypes.c_void_p]
advapi32.IsValidSid.restype = wintypes.BOOL
advapi32.EqualSid.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
advapi32.EqualSid.restype = wintypes.BOOL
advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
advapi32.OpenProcessToken.restype = wintypes.BOOL
advapi32.GetTokenInformation.argtypes = [
    wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
]
advapi32.GetTokenInformation.restype = wintypes.BOOL
advapi32.FreeSid.argtypes = [ctypes.c_void_p]
advapi32.FreeSid.restype = ctypes.c_void_p
shell32.IsUserAnAdmin.restype = wintypes.BOOL


def _u32(value: int) -> int:
    return ctypes.c_uint32(value).value


def _sid_string(sid: ctypes.c_void_p) -> str:
    text = wintypes.LPWSTR()
    if not advapi32.ConvertSidToStringSidW(sid, ctypes.byref(text)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return text.value
    finally:
        kernel32.LocalFree(text)


def _token_environment() -> Dict[str, Any]:
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        elevation = wintypes.DWORD()
        returned = wintypes.DWORD()
        ok = advapi32.GetTokenInformation(
            token, 20, ctypes.byref(elevation), ctypes.sizeof(elevation), ctypes.byref(returned)
        )
        return {
            "account": subprocess.check_output(["whoami"], text=True).strip(),
            "is_user_an_admin": bool(shell32.IsUserAnAdmin()),
            "token_elevation_query_ok": bool(ok),
            "token_is_elevated": bool(elevation.value) if ok else None,
            "token_elevation_error": 0 if ok else ctypes.get_last_error(),
        }
    finally:
        kernel32.CloseHandle(token)


def _grant_acl(path: Path, sid: str, rights: str, directory: bool) -> Dict[str, Any]:
    ace = f"*{sid}:{'(OI)(CI)' if directory else ''}{rights}"
    cmd = ["icacls.exe", str(path), "/grant:r", ace, "/Q"]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    return {
        "command": subprocess.list2cmdline(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def _stage_python(source: Path, destination: Path) -> Dict[str, Any]:
    destination.mkdir(parents=True)
    copied = []
    for name in ("python.exe", "python3.dll", "python312.dll", "vcruntime140.dll", "vcruntime140_1.dll"):
        src = source / name
        if src.exists():
            shutil.copy2(src, destination / name)
            copied.append(name)
    shutil.copytree(source / "DLLs", destination / "DLLs")
    ignored = shutil.ignore_patterns(
        "site-packages", "__pycache__", "ensurepip", "idlelib", "test", "tests",
        "tkinter", "turtledemo", "venv",
    )
    shutil.copytree(source / "Lib", destination / "Lib", ignore=ignored)
    return {
        "source": str(source),
        "destination": str(destination),
        "copied_root_files": copied,
        "staged_bytes": sum(p.stat().st_size for p in destination.rglob("*") if p.is_file()),
    }


CHILD_PROBE = r'''import ctypes, json, os, socket, sys
from ctypes import wintypes

cfg = json.loads(sys.argv[1])
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
adv = ctypes.WinDLL("advapi32", use_last_error=True)
k32.GetCurrentProcess.restype = wintypes.HANDLE
k32.GetHandleInformation.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
k32.GetHandleInformation.restype = wintypes.BOOL
adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
adv.OpenProcessToken.restype = wintypes.BOOL
adv.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
adv.GetTokenInformation.restype = wintypes.BOOL

result = {"python": sys.version, "executable": sys.executable}
token = wintypes.HANDLE()
if adv.OpenProcessToken(k32.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
    is_ac = wintypes.DWORD()
    ret = wintypes.DWORD()
    ok = adv.GetTokenInformation(token, 29, ctypes.byref(is_ac), ctypes.sizeof(is_ac), ctypes.byref(ret))
    result["token_is_appcontainer"] = bool(is_ac.value) if ok else None
    result["token_query_error"] = 0 if ok else ctypes.get_last_error()
    k32.CloseHandle(token)

flags = wintypes.DWORD()
ctypes.set_last_error(0)
sentinel_ok = bool(k32.GetHandleInformation(wintypes.HANDLE(cfg["sentinel_handle"]), ctypes.byref(flags)))
result["unallowlisted_handle"] = {"valid": sentinel_ok, "error": 0 if sentinel_ok else ctypes.get_last_error()}

try:
    with open(sys.executable, "rb") as stream:
        result["runtime_read"] = {"ok": bool(stream.read(1))}
except OSError as exc:
    result["runtime_read"] = {"ok": False, "winerror": getattr(exc, "winerror", None), "error": str(exc)}

for key in ("allowed_file", "denied_file"):
    try:
        with open(cfg[key], "w", encoding="utf-8") as stream:
            stream.write("appcontainer-probe")
        result[key] = {"ok": True}
    except OSError as exc:
        result[key] = {"ok": False, "winerror": getattr(exc, "winerror", None), "errno": exc.errno, "error": str(exc)}

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    sock.connect(("127.0.0.1", cfg["tcp_port"]))
    sock.sendall(b"tcp")
    result["tcp_loopback"] = {"ok": True}
except OSError as exc:
    result["tcp_loopback"] = {"ok": False, "winerror": getattr(exc, "winerror", None), "errno": exc.errno, "error": str(exc)}
finally:
    try: sock.close()
    except Exception: pass

try:
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sent = udp.sendto(b"udp", ("127.0.0.1", cfg["udp_port"]))
    result["udp_loopback"] = {"ok": True, "bytes": sent}
except OSError as exc:
    result["udp_loopback"] = {"ok": False, "winerror": getattr(exc, "winerror", None), "errno": exc.errno, "error": str(exc)}
finally:
    try: udp.close()
    except Exception: pass

encoded = json.dumps(result, sort_keys=True)
try:
    with open(cfg["result_file"], "w", encoding="utf-8") as stream:
        stream.write(encoded)
except OSError as exc:
    result["result_file_error"] = {"winerror": getattr(exc, "winerror", None), "error": str(exc)}
    encoded = json.dumps(result, sort_keys=True)
print(encoded, flush=True)
'''


def _fixture_servers() -> Tuple[socket.socket, socket.socket, Dict[str, Any]]:
    received: Dict[str, Any] = {"tcp_received": False, "udp_received": False}
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(("127.0.0.1", 0))
    tcp.listen(1)
    tcp.settimeout(5.0)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(("127.0.0.1", 0))
    udp.settimeout(5.0)

    def accept_tcp() -> None:
        try:
            conn, _ = tcp.accept()
            with conn:
                received["tcp_payload"] = conn.recv(16).decode("ascii", "replace")
                received["tcp_received"] = True
        except OSError as exc:
            if getattr(exc, "winerror", None) == 10038:
                received["tcp_fixture_closed_without_connection"] = True
            else:
                received["tcp_fixture_error"] = str(exc)

    def receive_udp() -> None:
        try:
            data, _ = udp.recvfrom(16)
            received["udp_payload"] = data.decode("ascii", "replace")
            received["udp_received"] = True
        except OSError as exc:
            if getattr(exc, "winerror", None) == 10038:
                received["udp_fixture_closed_without_datagram"] = True
            else:
                received["udp_fixture_error"] = str(exc)

    threading.Thread(target=accept_tcp, name="p0-tcp-fixture", daemon=True).start()
    threading.Thread(target=receive_udp, name="p0-udp-fixture", daemon=True).start()
    return tcp, udp, received


def _read_pipe(handle: wintypes.HANDLE) -> bytes:
    chunks = []
    while True:
        buf = ctypes.create_string_buffer(4096)
        read = wintypes.DWORD()
        if not kernel32.ReadFile(handle, buf, len(buf), ctypes.byref(read), None) or read.value == 0:
            break
        chunks.append(buf.raw[:read.value])
    return b"".join(chunks)


def _launch_appcontainer(
    executable: Path,
    child_script: Path,
    sid: ctypes.c_void_p,
    config: Dict[str, Any],
    *,
    include_handle_list: bool,
    argv: Optional[List[str]] = None,
) -> Dict[str, Any]:
    sa = SECURITY_ATTRIBUTES(ctypes.sizeof(SECURITY_ATTRIBUTES), None, True)
    stdout_read, stdout_write = wintypes.HANDLE(), wintypes.HANDLE()
    if include_handle_list:
        if not kernel32.CreatePipe(ctypes.byref(stdout_read), ctypes.byref(stdout_write), ctypes.byref(sa), 0):
            raise ctypes.WinError(ctypes.get_last_error())
        kernel32.SetHandleInformation(stdout_read, HANDLE_FLAG_INHERIT, 0)
    sentinel = kernel32.CreateEventW(ctypes.byref(sa), True, False, None)
    config["sentinel_handle"] = int(sentinel)

    handles = (wintypes.HANDLE * 1)(stdout_write) if include_handle_list else None
    security = SECURITY_CAPABILITIES(sid, None, 0, 0)
    size = ctypes.c_size_t()
    ctypes.set_last_error(0)
    attribute_count = 2 if include_handle_list else 1
    first_init = bool(kernel32.InitializeProcThreadAttributeList(None, attribute_count, 0, ctypes.byref(size)))
    first_error = ctypes.get_last_error()
    attr_buf = ctypes.create_string_buffer(size.value)
    attr_ptr = ctypes.cast(attr_buf, ctypes.c_void_p)
    init_ok = bool(kernel32.InitializeProcThreadAttributeList(attr_ptr, attribute_count, 0, ctypes.byref(size)))
    init_error = 0 if init_ok else ctypes.get_last_error()
    handle_attr_ok: Optional[bool] = None
    handle_attr_error: Optional[int] = None
    if include_handle_list:
        handle_attr_ok = bool(kernel32.UpdateProcThreadAttribute(
            attr_ptr, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
            ctypes.cast(handles, ctypes.c_void_p), ctypes.sizeof(handles), None, None,
        ))
        handle_attr_error = 0 if handle_attr_ok else ctypes.get_last_error()
    security_attr_ok = bool(kernel32.UpdateProcThreadAttribute(
        attr_ptr, 0, PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
        ctypes.byref(security), ctypes.sizeof(security), None, None,
    ))
    security_attr_error = 0 if security_attr_ok else ctypes.get_last_error()

    if argv is None:
        argv = [
            str(executable), "-I", "-S", str(child_script),
            json.dumps(config, separators=(",", ":")),
        ]
    command = subprocess.list2cmdline(argv)
    siex = STARTUPINFOEXW()
    siex.StartupInfo.cb = ctypes.sizeof(siex)
    siex.StartupInfo.dwFlags = STARTF_USESTDHANDLES if include_handle_list else 0
    siex.StartupInfo.hStdInput = wintypes.HANDLE(0)
    siex.StartupInfo.hStdOutput = stdout_write if include_handle_list else wintypes.HANDLE(0)
    siex.StartupInfo.hStdError = stdout_write if include_handle_list else wintypes.HANDLE(0)
    siex.lpAttributeList = attr_ptr
    pi = PROCESS_INFORMATION()
    ctypes.set_last_error(0)
    create_ok = bool(kernel32.CreateProcessW(
        None, ctypes.create_unicode_buffer(command), None, None, include_handle_list,
        EXTENDED_STARTUPINFO_PRESENT, None, str(executable.parent),
        ctypes.byref(siex), ctypes.byref(pi),
    ))
    create_error = 0 if create_ok else ctypes.get_last_error()
    if include_handle_list:
        kernel32.CloseHandle(stdout_write)

    wait_result: Optional[int] = None
    exit_code: Optional[int] = None
    output = b""
    if create_ok:
        kernel32.CloseHandle(pi.hThread)
        wait_result = int(kernel32.WaitForSingleObject(pi.hProcess, 15000))
        code = wintypes.DWORD(STILL_ACTIVE)
        if kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code)):
            exit_code = int(code.value)
        if include_handle_list:
            output = _read_pipe(stdout_read)
        kernel32.CloseHandle(pi.hProcess)
    if include_handle_list:
        kernel32.CloseHandle(stdout_read)
    kernel32.CloseHandle(sentinel)
    kernel32.DeleteProcThreadAttributeList(attr_ptr)

    text = output.decode("utf-8", "replace").strip()
    child_result = None
    if text:
        try:
            child_result = json.loads(text.splitlines()[-1])
        except json.JSONDecodeError:
            pass
    return {
        "attribute_list": {
            "attribute_count": attribute_count,
            "first_call_return": first_init,
            "first_call_error": first_error,
            "expected_first_error": ERROR_INSUFFICIENT_BUFFER,
            "size": size.value,
            "initialize_ok": init_ok,
            "initialize_error": init_error,
            "handle_list_ok": handle_attr_ok,
            "handle_list_error": handle_attr_error,
            "security_capabilities_ok": security_attr_ok,
            "security_capabilities_error": security_attr_error,
        },
        "create_process_ok": create_ok,
        "create_process_error": create_error,
        "wait_result": wait_result,
        "exit_code": exit_code,
        "raw_output": text,
        "child": child_result,
    }


def run_probe(python_source: Path) -> Dict[str, Any]:
    started = time.time()
    name = f"mke.s4b2.p0.{os.getpid()}.{int(started)}"
    result: Dict[str, Any] = {
        "schema": "mke-s4b2-p0-appcontainer-preflight-v1",
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "environment": {
            "platform": platform.platform(),
            "windows_version": platform.version(),
            "python_source": str(python_source),
            **_token_environment(),
        },
        "profile": {"name": name},
    }
    work_root = Path(tempfile.mkdtemp(prefix="mke-s4b2-p0-"))
    runtime = work_root / "runtime"
    allowed = work_root / "assigned-write"
    outside = work_root / "outside" / "denied.txt"
    allowed.mkdir()
    outside.parent.mkdir()
    result["disposable_root"] = str(work_root)
    sid = ctypes.c_void_p()
    derived_sid = ctypes.c_void_p()
    delete_hr: Optional[int] = None
    tcp = udp = None
    try:
        create_hr_signed = userenv.CreateAppContainerProfile(
            name, "MKE S4-B2 P0", "Disposable feasibility profile", None, 0, ctypes.byref(sid)
        )
        create_hr = _u32(create_hr_signed)
        result["profile"]["create_hresult"] = f"0x{create_hr:08X}"
        result["profile"]["create_succeeded"] = create_hr == 0
        if create_hr != 0:
            return result
        sid_text = _sid_string(sid)
        result["profile"]["sid"] = sid_text
        derive_hr_signed = userenv.DeriveAppContainerSidFromAppContainerName(name, ctypes.byref(derived_sid))
        derive_hr = _u32(derive_hr_signed)
        result["profile"]["derive_hresult"] = f"0x{derive_hr:08X}"
        result["profile"]["returned_sid_valid"] = bool(advapi32.IsValidSid(sid))
        result["profile"]["derived_sid_valid"] = bool(derived_sid.value and advapi32.IsValidSid(derived_sid))
        result["profile"]["returned_equals_derived"] = bool(
            derived_sid.value and advapi32.EqualSid(sid, derived_sid)
        )
        launch_sid = derived_sid if derived_sid.value else sid

        result["runtime_stage"] = _stage_python(python_source, runtime)
        child_script = runtime / "probe_child.py"
        child_script.write_text(CHILD_PROBE, encoding="utf-8")
        result["acl"] = {
            "runtime_rx": _grant_acl(runtime, sid_text, "RX", True),
            "assigned_modify": _grant_acl(allowed, sid_text, "M", True),
        }

        native_config = {
            "allowed_file": str(allowed / "native-smoke-allowed.txt"),
            "denied_file": str(outside),
            "result_file": str(allowed / "native-smoke-result.json"),
            "tcp_port": 1,
            "udp_port": 1,
        }
        native_exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "whoami.exe"
        result["native_smoke_launch"] = _launch_appcontainer(
            native_exe, child_script, launch_sid, native_config,
            include_handle_list=False,
            argv=[str(native_exe)],
        )

        tcp, udp, fixture = _fixture_servers()
        security_only_config = {
            "allowed_file": str(allowed / "security-only-allowed.txt"),
            "denied_file": str(outside),
            "result_file": str(allowed / "security-only-result.json"),
            "tcp_port": tcp.getsockname()[1],
            "udp_port": udp.getsockname()[1],
        }
        result["security_only_launch"] = _launch_appcontainer(
            runtime / "python.exe", child_script, launch_sid, security_only_config,
            include_handle_list=False,
        )
        result_file = Path(security_only_config["result_file"])
        if result_file.exists():
            result["security_only_launch"]["child"] = json.loads(result_file.read_text(encoding="utf-8"))
        tcp.close()
        udp.close()

        tcp, udp, fixture = _fixture_servers()
        config = {
            "allowed_file": str(allowed / "allowed.txt"),
            "denied_file": str(outside),
            "result_file": str(allowed / "combined-result.json"),
            "tcp_port": tcp.getsockname()[1],
            "udp_port": udp.getsockname()[1],
        }
        result["launch"] = _launch_appcontainer(
            runtime / "python.exe", child_script, launch_sid, config,
            include_handle_list=True,
        )
        result_file = Path(config["result_file"])
        if result_file.exists() and result["launch"].get("child") is None:
            result["launch"]["child"] = json.loads(result_file.read_text(encoding="utf-8"))
        time.sleep(0.2)
        result["fixtures"] = fixture
        result["filesystem_observation"] = {
            "allowed_file_exists": (allowed / "allowed.txt").exists(),
            "denied_file_exists": outside.exists(),
        }
        return result
    finally:
        if tcp is not None:
            tcp.close()
        if udp is not None:
            udp.close()
        if sid.value:
            advapi32.FreeSid(sid)
        if derived_sid.value:
            advapi32.FreeSid(derived_sid)
        delete_hr_signed = userenv.DeleteAppContainerProfile(name)
        delete_hr = _u32(delete_hr_signed)
        result["profile"]["delete_hresult"] = f"0x{delete_hr:08X}"
        result["profile"]["delete_succeeded"] = delete_hr == 0
        shutil.rmtree(work_root, ignore_errors=True)
        result["disposable_root_removed"] = not work_root.exists()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_probe(args.python_root.resolve())
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    launch = result.get("launch", {})
    return 0 if result["profile"].get("create_succeeded") and launch.get("create_process_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
