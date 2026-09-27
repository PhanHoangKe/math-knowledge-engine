"""Standalone ctypes counterpart to the S4-B2/P0-R1 native launcher."""

from __future__ import annotations

import ctypes
import json
import os
import platform
import sys
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Dict, Optional


if sys.platform != "win32":
    raise SystemExit("Windows only")


CREATE_SUSPENDED = 0x00000004
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002
PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
ERROR_INSUFFICIENT_BUFFER = 122
DUPLICATE_SAME_ACCESS = 0x00000002
TOKEN_QUERY = 0x0008
TokenElevation = 20
TokenIsAppContainer = 29
TokenAppContainerSid = 31


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
        ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [
        ("StartupInfo", STARTUPINFOW),
        ("lpAttributeList", ctypes.c_void_p),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Sid", ctypes.c_void_p),
        ("Attributes", wintypes.DWORD),
    ]


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
    ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION),
]
kernel32.CreateProcessW.restype = wintypes.BOOL
kernel32.CreateEventW.argtypes = [
    ctypes.POINTER(SECURITY_ATTRIBUTES), wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR
]
kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.GetHandleInformation.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.GetHandleInformation.restype = wintypes.BOOL
kernel32.DuplicateHandle.argtypes = [
    wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE,
    ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD,
]
kernel32.DuplicateHandle.restype = wintypes.BOOL
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.IsProcessInJob.argtypes = [
    wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)
]
kernel32.IsProcessInJob.restype = wintypes.BOOL
kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

advapi32.OpenProcessToken.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)
]
advapi32.OpenProcessToken.restype = wintypes.BOOL
advapi32.GetTokenInformation.argtypes = [
    wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
advapi32.GetTokenInformation.restype = wintypes.BOOL
advapi32.IsValidSid.argtypes = [ctypes.c_void_p]
advapi32.IsValidSid.restype = wintypes.BOOL
advapi32.ConvertSidToStringSidW.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)
]
advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
advapi32.FreeSid.argtypes = [ctypes.c_void_p]

userenv.CreateAppContainerProfile.argtypes = [
    wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
    ctypes.POINTER(SID_AND_ATTRIBUTES), wintypes.DWORD,
    ctypes.POINTER(ctypes.c_void_p),
]
userenv.CreateAppContainerProfile.restype = ctypes.c_long
userenv.DeleteAppContainerProfile.argtypes = [wintypes.LPCWSTR]
userenv.DeleteAppContainerProfile.restype = ctypes.c_long

shell32.IsUserAnAdmin.restype = wintypes.BOOL


def _u32(value: int) -> int:
    return ctypes.c_uint32(value).value


def _handle_value(handle: Any) -> int:
    if isinstance(handle, ctypes.c_void_p):
        return int(handle.value or 0)
    return int(handle or 0)


def _sid_text(sid: ctypes.c_void_p) -> str:
    raw = wintypes.LPWSTR()
    if not sid or not advapi32.ConvertSidToStringSidW(sid, ctypes.byref(raw)):
        return ""
    try:
        return raw.value
    finally:
        kernel32.LocalFree(raw)


def _token_evidence(process: wintypes.HANDLE) -> Dict[str, Any]:
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(process, TOKEN_QUERY, ctypes.byref(token)):
        return {"query_ok": False, "query_error": ctypes.get_last_error()}
    try:
        returned = wintypes.DWORD()
        is_appcontainer = wintypes.DWORD()
        ctypes.set_last_error(0)
        app_ok = bool(advapi32.GetTokenInformation(
            token, TokenIsAppContainer, ctypes.byref(is_appcontainer),
            ctypes.sizeof(is_appcontainer), ctypes.byref(returned),
        ))
        app_error = 0 if app_ok else ctypes.get_last_error()

        elevation = TOKEN_ELEVATION()
        ctypes.set_last_error(0)
        elevation_ok = bool(advapi32.GetTokenInformation(
            token, TokenElevation, ctypes.byref(elevation), ctypes.sizeof(elevation),
            ctypes.byref(returned),
        ))
        elevation_error = 0 if elevation_ok else ctypes.get_last_error()

        needed = wintypes.DWORD()
        ctypes.set_last_error(0)
        advapi32.GetTokenInformation(
            token, TokenAppContainerSid, None, 0, ctypes.byref(needed)
        )
        sid_probe_error = ctypes.get_last_error()
        sid_ok = False
        sid_value = ""
        sid_error = 0
        if needed.value and sid_probe_error == ERROR_INSUFFICIENT_BUFFER:
            buffer = ctypes.create_string_buffer(needed.value)
            sid_ok = bool(advapi32.GetTokenInformation(
                token, TokenAppContainerSid, buffer, needed.value,
                ctypes.byref(returned),
            ))
            sid_error = 0 if sid_ok else ctypes.get_last_error()
            if sid_ok:
                info = ctypes.cast(
                    buffer, ctypes.POINTER(TOKEN_APPCONTAINER_INFORMATION)
                ).contents
                sid_value = _sid_text(info.TokenAppContainer)
        elif is_appcontainer.value:
            sid_error = sid_probe_error
        return {
            "query_ok": app_ok and elevation_ok and (sid_ok or not is_appcontainer.value),
            "query_error": app_error or elevation_error or sid_error,
            "is_appcontainer": bool(is_appcontainer.value),
            "elevated": bool(elevation.TokenIsElevated),
            "appcontainer_sid": sid_value,
        }
    finally:
        kernel32.CloseHandle(token)


def _child_has_handle(process: wintypes.HANDLE, candidate: wintypes.HANDLE) -> bool:
    duplicate = wintypes.HANDLE()
    ok = bool(kernel32.DuplicateHandle(
        process, candidate, kernel32.GetCurrentProcess(), ctypes.byref(duplicate),
        0, False, DUPLICATE_SAME_ACCESS,
    ))
    if ok:
        kernel32.CloseHandle(duplicate)
    return ok


def _launch(
    name: str,
    executable: str,
    sid: ctypes.c_void_p,
    *,
    use_appcontainer: bool,
    use_handle_list: bool,
    allowed: wintypes.HANDLE,
    decoy: wintypes.HANDLE,
    explicit_application_name: bool = True,
    explicit_current_directory: bool = False,
) -> Dict[str, Any]:
    attribute_count = int(use_appcontainer) + int(use_handle_list)
    extended = bool(attribute_count)
    startup = STARTUPINFOEXW()
    startup.StartupInfo.cb = (
        ctypes.sizeof(STARTUPINFOEXW) if extended else ctypes.sizeof(STARTUPINFOW)
    )
    size = ctypes.c_size_t()
    attr_buffer: Optional[Any] = None
    attr_ptr = ctypes.c_void_p()
    sizing_return = False
    sizing_error = 0
    initialize_return = False
    initialize_error = 0
    security_update_return = False
    security_update_error = 0
    handle_update_return = False
    handle_update_error = 0
    security = SECURITY_CAPABILITIES(sid, None, 0, 0)
    handles = (wintypes.HANDLE * 1)(allowed)

    if extended:
        ctypes.set_last_error(0)
        sizing_return = bool(kernel32.InitializeProcThreadAttributeList(
            None, attribute_count, 0, ctypes.byref(size)
        ))
        sizing_error = ctypes.get_last_error()
        attr_buffer = ctypes.create_string_buffer(size.value)
        attr_ptr = ctypes.cast(attr_buffer, ctypes.c_void_p)
        ctypes.set_last_error(0)
        initialize_return = bool(kernel32.InitializeProcThreadAttributeList(
            attr_ptr, attribute_count, 0, ctypes.byref(size)
        ))
        initialize_error = 0 if initialize_return else ctypes.get_last_error()
        if initialize_return and use_appcontainer:
            ctypes.set_last_error(0)
            security_update_return = bool(kernel32.UpdateProcThreadAttribute(
                attr_ptr, 0, PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
                ctypes.byref(security), ctypes.sizeof(security), None, None,
            ))
            security_update_error = (
                0 if security_update_return else ctypes.get_last_error()
            )
        if initialize_return and use_handle_list:
            ctypes.set_last_error(0)
            handle_update_return = bool(kernel32.UpdateProcThreadAttribute(
                attr_ptr, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
                ctypes.cast(handles, ctypes.c_void_p), ctypes.sizeof(handles),
                None, None,
            ))
            handle_update_error = (
                0 if handle_update_return else ctypes.get_last_error()
            )
        startup.lpAttributeList = attr_ptr

    command = ctypes.create_unicode_buffer(f'"{executable}"')
    process = PROCESS_INFORMATION()
    flags = CREATE_SUSPENDED | (EXTENDED_STARTUPINFO_PRESENT if extended else 0)
    inherit = bool(use_handle_list)
    ctypes.set_last_error(0)
    create_return = bool(kernel32.CreateProcessW(
        executable if explicit_application_name else None,
        command, None, None, inherit, flags, None,
        str(Path(executable).parent) if explicit_current_directory else None,
        ctypes.cast(ctypes.byref(startup), ctypes.POINTER(STARTUPINFOW)),
        ctypes.byref(process),
    ))
    create_error = 0 if create_return else ctypes.get_last_error()
    result: Dict[str, Any] = {
        "type": "experiment",
        "name": name,
        "api": "CreateProcessW",
        "executable": executable,
        "explicit_application_name": explicit_application_name,
        "explicit_current_directory": explicit_current_directory,
        "use_extended": extended,
        "use_appcontainer": use_appcontainer,
        "use_handle_list": use_handle_list,
        "attribute_count": attribute_count,
        "attribute_bytes": size.value,
        "attribute_buffer_address": attr_ptr.value,
        "attribute_buffer_alignment_mod_8": (
            attr_ptr.value % 8 if attr_ptr.value else None
        ),
        "sizing_return": sizing_return,
        "sizing_error": sizing_error,
        "initialize_return": initialize_return,
        "initialize_error": initialize_error,
        "security_update_return": security_update_return,
        "security_update_error": security_update_error,
        "handle_update_return": handle_update_return,
        "handle_update_error": handle_update_error,
        "startup_cb": startup.StartupInfo.cb,
        "inherit_handles": inherit,
        "creation_flags": flags,
        "create_return": create_return,
        "create_error": create_error,
        "pid": process.dwProcessId if create_return else 0,
    }
    if create_return:
        result["token"] = _token_evidence(process.hProcess)
        result["allowed_handle_inherited"] = (
            _child_has_handle(process.hProcess, allowed) if use_handle_list else False
        )
        result["decoy_handle_inherited"] = (
            _child_has_handle(process.hProcess, decoy) if use_handle_list else False
        )
        kernel32.TerminateProcess(process.hProcess, 0)
        kernel32.WaitForSingleObject(process.hProcess, 5000)
        kernel32.CloseHandle(process.hThread)
        kernel32.CloseHandle(process.hProcess)
    if extended:
        kernel32.DeleteProcThreadAttributeList(attr_ptr)
    return result


def main() -> int:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    executable = str(Path(system_root) / "System32" / "whoami.exe")
    profile_name = f"mke.s4b2.p0r1.ctypes.{os.getpid()}.{time.time_ns()}"
    sid = ctypes.c_void_p()
    create_hr = _u32(userenv.CreateAppContainerProfile(
        profile_name, "MKE S4-B2 P0-R1", "Disposable ctypes diagnosis",
        None, 0, ctypes.byref(sid),
    ))

    inheritable = SECURITY_ATTRIBUTES(
        ctypes.sizeof(SECURITY_ATTRIBUTES), None, True
    )
    allowed = kernel32.CreateEventW(ctypes.byref(inheritable), True, False, None)
    decoy = kernel32.CreateEventW(ctypes.byref(inheritable), True, False, None)
    allowed_flags = wintypes.DWORD()
    decoy_flags = wintypes.DWORD()
    allowed_info = bool(kernel32.GetHandleInformation(
        allowed, ctypes.byref(allowed_flags)
    ))
    decoy_info = bool(kernel32.GetHandleInformation(
        decoy, ctypes.byref(decoy_flags)
    ))
    in_job = wintypes.BOOL()
    job_ok = bool(kernel32.IsProcessInJob(
        kernel32.GetCurrentProcess(), None, ctypes.byref(in_job)
    ))
    job_error = 0 if job_ok else ctypes.get_last_error()

    metadata = {
        "type": "metadata",
        "account": (
            f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}"
        ).strip("\\"),
        "python_version": sys.version,
        "python_architecture": platform.architecture()[0],
        "pointer_size": ctypes.sizeof(ctypes.c_void_p),
        "sizeof_STARTUPINFOW": ctypes.sizeof(STARTUPINFOW),
        "alignof_STARTUPINFOW": ctypes.alignment(STARTUPINFOW),
        "sizeof_STARTUPINFOEXW": ctypes.sizeof(STARTUPINFOEXW),
        "alignof_STARTUPINFOEXW": ctypes.alignment(STARTUPINFOEXW),
        "offsetof_dwXCountChars": STARTUPINFOW.dwXCountChars.offset,
        "offsetof_dwYCountChars": STARTUPINFOW.dwYCountChars.offset,
        "offsetof_dwFillAttribute": STARTUPINFOW.dwFillAttribute.offset,
        "offsetof_lpAttributeList": STARTUPINFOEXW.lpAttributeList.offset,
        "sizeof_SECURITY_CAPABILITIES": ctypes.sizeof(SECURITY_CAPABILITIES),
        "alignof_SECURITY_CAPABILITIES": ctypes.alignment(SECURITY_CAPABILITIES),
        "sizeof_HANDLE": ctypes.sizeof(wintypes.HANDLE),
        "process_in_job_query_ok": job_ok,
        "process_in_job": bool(in_job.value),
        "process_in_job_error": job_error,
        "is_user_an_admin": bool(shell32.IsUserAnAdmin()),
        "parent_token": _token_evidence(kernel32.GetCurrentProcess()),
        "profile_create_hresult": create_hr,
        "profile_sid_valid": bool(sid.value and advapi32.IsValidSid(sid)),
        "profile_sid": _sid_text(sid),
        "allowed_handle_value": _handle_value(allowed),
        "allowed_handle_info_ok": allowed_info,
        "allowed_handle_flags": allowed_flags.value,
        "decoy_handle_value": _handle_value(decoy),
        "decoy_handle_info_ok": decoy_info,
        "decoy_handle_flags": decoy_flags.value,
        "executable": executable,
    }
    print(json.dumps(metadata, sort_keys=True))
    if create_hr != 0 or not sid.value or not allowed or not decoy:
        return 3
    try:
        experiments = [
            _launch("E_A_normal", executable, sid, use_appcontainer=False,
                    use_handle_list=False, allowed=allowed, decoy=decoy),
            _launch("E_B_appcontainer_only", executable, sid, use_appcontainer=True,
                    use_handle_list=False, allowed=allowed, decoy=decoy),
            _launch("E_C_handle_list_only", executable, sid, use_appcontainer=False,
                    use_handle_list=True, allowed=allowed, decoy=decoy),
            _launch("E_D_combined", executable, sid, use_appcontainer=True,
                    use_handle_list=True, allowed=allowed, decoy=decoy),
            _launch("E_B_null_application_name", executable, sid,
                    use_appcontainer=True, use_handle_list=False,
                    allowed=allowed, decoy=decoy,
                    explicit_application_name=False),
            _launch("E_B_explicit_current_directory", executable, sid,
                    use_appcontainer=True, use_handle_list=False,
                    allowed=allowed, decoy=decoy,
                    explicit_current_directory=True),
        ]
        for experiment in experiments:
            print(json.dumps(experiment, sort_keys=True))
    finally:
        kernel32.CloseHandle(allowed)
        kernel32.CloseHandle(decoy)
        advapi32.FreeSid(sid)
        delete_hr = _u32(userenv.DeleteAppContainerProfile(profile_name))
        print(json.dumps({
            "type": "cleanup",
            "profile_delete_hresult": delete_hr,
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
