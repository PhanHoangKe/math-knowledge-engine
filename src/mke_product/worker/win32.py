"""Win32 ctypes interfaces and safe abstractions for Job Objects and process containment."""

import sys
from typing import Any, List, Optional, Tuple

if sys.platform != "win32":
    raise ImportError("mke_product.worker.win32 is only supported on Windows operating systems.")

import ctypes
from ctypes import wintypes

from .constants import (
    ERROR_BROKEN_PIPE,
    ERROR_COMMITMENT_LIMIT,
    ERROR_INSUFFICIENT_BUFFER,
    ERROR_NOT_ENOUGH_QUOTA,
    HANDLE_FLAG_INHERIT,
    JOB_OBJECT_LIMIT_JOB_MEMORY,
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    JOB_OBJECT_LIMIT_PROCESS_MEMORY,
    JOB_MEMORY_LIMIT_BYTES,
    JobObjectBasicProcessIdList,
    JobObjectExtendedLimitInformation,
    PROCESS_MEMORY_LIMIT_BYTES,
    PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
    STARTF_USESTDHANDLES,
    WAIT_OBJECT_0,
    WAIT_TIMEOUT,
)

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# ---------------------------------------------------------------------------
# CTypes Structures
# ---------------------------------------------------------------------------
class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryLimit", ctypes.c_size_t),
        ("PeakJobMemoryLimit", ctypes.c_size_t),
    ]


class JOBOBJECT_BASIC_PROCESS_ID_LIST(ctypes.Structure):
    _fields_ = [
        ("NumberOfAssignedProcesses", wintypes.DWORD),
        ("NumberOfProcessIdsInList", wintypes.DWORD),
        ("ProcessIdList", ctypes.c_size_t * 64),
    ]


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


# ---------------------------------------------------------------------------
# Kernel32 Function Signatures
# ---------------------------------------------------------------------------
kernel32.GetCurrentProcess.restype = wintypes.HANDLE

kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
kernel32.CreateJobObjectW.restype = wintypes.HANDLE

kernel32.SetInformationJobObject.argtypes = [
    wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD
]
kernel32.SetInformationJobObject.restype = wintypes.BOOL

kernel32.QueryInformationJobObject.argtypes = [
    wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)
]
kernel32.QueryInformationJobObject.restype = wintypes.BOOL

kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
kernel32.AssignProcessToJobObject.restype = wintypes.BOOL

kernel32.IsProcessInJob.argtypes = [
    wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)
]
kernel32.IsProcessInJob.restype = wintypes.BOOL

kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
    wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
    ctypes.c_void_p, ctypes.POINTER(PROCESS_INFORMATION)
]
kernel32.CreateProcessW.restype = wintypes.BOOL

kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
kernel32.ResumeThread.restype = wintypes.DWORD

kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel32.TerminateProcess.restype = wintypes.BOOL

kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.GetExitCodeProcess.restype = wintypes.BOOL

kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

kernel32.CreatePipe.argtypes = [
    ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE),
    ctypes.POINTER(SECURITY_ATTRIBUTES), wintypes.DWORD
]
kernel32.CreatePipe.restype = wintypes.BOOL

kernel32.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
kernel32.SetHandleInformation.restype = wintypes.BOOL

kernel32.PeekNamedPipe.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD)
]
kernel32.PeekNamedPipe.restype = wintypes.BOOL

kernel32.ReadFile.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
]
kernel32.ReadFile.restype = wintypes.BOOL

kernel32.WriteFile.argtypes = [
    wintypes.HANDLE, ctypes.c_char_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
]
kernel32.WriteFile.restype = wintypes.BOOL

kernel32.InitializeProcThreadAttributeList.argtypes = [
    ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)
]
kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL

kernel32.UpdateProcThreadAttribute.argtypes = [
    ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t, ctypes.c_void_p,
    ctypes.c_size_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)
]
kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL

kernel32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]


# ---------------------------------------------------------------------------
# Safe Abstractions & Helper Functions
# ---------------------------------------------------------------------------

def safe_close_handle(handle: Optional[wintypes.HANDLE]) -> None:
    """Safely close a Windows handle if valid."""
    if handle and handle != wintypes.HANDLE(0).value and handle != wintypes.HANDLE(-1).value:
        try:
            kernel32.CloseHandle(handle)
        except Exception:
            pass


def is_current_process_in_job() -> Tuple[bool, int]:
    """Check if the current process is running inside any Windows Job Object."""
    in_job = wintypes.BOOL()
    res = kernel32.IsProcessInJob(kernel32.GetCurrentProcess(), None, ctypes.byref(in_job))
    err = ctypes.get_last_error()
    if not res:
        return False, err
    return bool(in_job.value), 0


def create_configured_job_object(
    process_memory_limit: int = PROCESS_MEMORY_LIMIT_BYTES,
    job_memory_limit: int = JOB_MEMORY_LIMIT_BYTES,
) -> Tuple[Optional[wintypes.HANDLE], int]:
    """Create a Windows Job Object configured with S4-B1 resource limits.

    Enforces:
    - JOB_OBJECT_LIMIT_PROCESS_MEMORY (default 256 MiB)
    - JOB_OBJECT_LIMIT_JOB_MEMORY (default 512 MiB)
    - JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    - Strictly does NOT enable breakaway flags.
    """
    h_job = kernel32.CreateJobObjectW(None, None)
    if not h_job:
        return None, ctypes.get_last_error()

    limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    limits.BasicLimitInformation.LimitFlags = (
        JOB_OBJECT_LIMIT_PROCESS_MEMORY |
        JOB_OBJECT_LIMIT_JOB_MEMORY |
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    )
    limits.ProcessMemoryLimit = process_memory_limit
    limits.JobMemoryLimit = job_memory_limit

    res = kernel32.SetInformationJobObject(
        h_job,
        JobObjectExtendedLimitInformation,
        ctypes.byref(limits),
        ctypes.sizeof(limits),
    )
    if not res:
        err = ctypes.get_last_error()
        safe_close_handle(h_job)
        return None, err

    return h_job, 0


def assign_and_verify_process_in_job(h_job: wintypes.HANDLE, h_process: wintypes.HANDLE) -> Tuple[bool, int]:
    """Assign process to Job Object and verify assignment before resuming execution."""
    res = kernel32.AssignProcessToJobObject(h_job, h_process)
    if not res:
        return False, ctypes.get_last_error()

    in_job = wintypes.BOOL()
    verify_res = kernel32.IsProcessInJob(h_process, h_job, ctypes.byref(in_job))
    if not verify_res or not in_job.value:
        err = ctypes.get_last_error() if not verify_res else 0
        return False, err

    return True, 0


def query_job_pids(h_job: wintypes.HANDLE) -> Tuple[List[int], int]:
    """Query list of process IDs currently assigned to the Job Object."""
    pids_struct = JOBOBJECT_BASIC_PROCESS_ID_LIST()
    ret_len = wintypes.DWORD()
    res = kernel32.QueryInformationJobObject(
        h_job,
        JobObjectBasicProcessIdList,
        ctypes.byref(pids_struct),
        ctypes.sizeof(pids_struct),
        ctypes.byref(ret_len),
    )
    if not res:
        return [], ctypes.get_last_error()

    count = min(pids_struct.NumberOfProcessIdsInList, 64)
    return [int(pids_struct.ProcessIdList[i]) for i in range(count)], 0


def query_job_peak_memory(h_job: wintypes.HANDLE) -> Tuple[int, int, int]:
    """Query PeakProcessMemoryLimit and PeakJobMemoryLimit for Job Object.

    Returns:
        (peak_process_bytes, peak_job_bytes, win32_error)
    """
    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    ret_len = wintypes.DWORD()
    res = kernel32.QueryInformationJobObject(
        h_job,
        JobObjectExtendedLimitInformation,
        ctypes.byref(info),
        ctypes.sizeof(info),
        ctypes.byref(ret_len),
    )
    if not res:
        return 0, 0, ctypes.get_last_error()
    return int(info.PeakProcessMemoryLimit), int(info.PeakJobMemoryLimit), 0
