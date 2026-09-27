"""Windows Job Object worker controller and process containment manager."""

import json
import os
import re
import struct
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

if sys.platform != "win32":
    raise ImportError("WorkerController is only supported on Windows operating systems.")

import ctypes
from ctypes import wintypes

from mke_product.protocol.errors import (
    ProtocolError,
    ProtocolInvalidTypeError,
    ProtocolJsonDecodeError,
    ProtocolPayloadTooLargeError,
    ProtocolStructureError,
)
from mke_product.protocol.schema import SCHEMA_VERSION
from mke_product.protocol.validator import _measure_dict_bytes

from .constants import (
    CREATE_SUSPENDED,
    DEFAULT_WORKER_TIMEOUT_SEC,
    ERROR_BROKEN_PIPE,
    ERROR_COMMITMENT_LIMIT,
    ERROR_NOT_ENOUGH_QUOTA,
    EXTENDED_STARTUPINFO_PRESENT,
    HANDLE_FLAG_INHERIT,
    IPC_HEADER_SIZE,
    IPC_MAX_REQUEST_BYTES,
    IPC_MAX_RESPONSE_BYTES,
    JOB_MEMORY_LIMIT_BYTES,
    PROCESS_MEMORY_LIMIT_BYTES,
    PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
    STARTF_USESTDHANDLES,
    STATUS_COMMITMENT_LIMIT,
    WAIT_OBJECT_0,
    WAIT_TIMEOUT,
    WORKER_ASSIGNMENT_FAILURE,
    WORKER_EXIT_FAILURE,
    WORKER_PROTOCOL_FAILURE,
    WORKER_RESOURCE_EXHAUSTED,
    WORKER_STARTUP_FAILURE,
    WORKER_TIMEOUT,
)
from .win32 import (
    PROCESS_INFORMATION,
    SECURITY_ATTRIBUTES,
    STARTUPINFOEXW,
    assign_and_verify_process_in_job,
    create_configured_job_object,
    kernel32,
    query_job_peak_memory,
    safe_close_handle,
)


def _sanitize_error_text(text: str) -> str:
    """Sanitize internal filesystem paths and sensitive identifiers from error output."""
    if not text:
        return ""
    # Redact Windows paths (e.g. C:\... or D:\...)
    sanitized = re.sub(r"[a-zA-Z]:\\[^\s\"';,]+", "[REDACTED_PATH]", text)
    # Redact Unix style paths
    sanitized = re.sub(r"/(?:[a-zA-Z0-9_\.\-]+/)+[a-zA-Z0-9_\.\-]+", "[REDACTED_PATH]", sanitized)
    return sanitized.strip()


def _build_controller_error(
    status: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    operation: str = "UNKNOWN",
) -> Dict[str, Any]:
    """Construct structured fail-closed error envelope matching S4 protocol taxonomy."""
    outcome = "RESOURCE_EXHAUSTED" if status in (WORKER_RESOURCE_EXHAUSTED, WORKER_TIMEOUT) else "PROTOCOL_ERROR"
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": operation,
        "outcome": outcome,
        "status": status,
        "definedness": None,
        "is_provisional_evidence": False,
        "error": {
            "code": status,
            "message": _sanitize_error_text(message),
            "details": details or {},
        },
    }


class WorkerController:
    """Manages creation, execution, and containment of disposable sandboxed workers."""

    def __init__(
        self,
        process_memory_limit: int = PROCESS_MEMORY_LIMIT_BYTES,
        job_memory_limit: int = JOB_MEMORY_LIMIT_BYTES,
        timeout_sec: float = DEFAULT_WORKER_TIMEOUT_SEC,
        _worker_cmd: Optional[str] = None,
    ) -> None:
        self.process_memory_limit = process_memory_limit
        self.job_memory_limit = job_memory_limit
        self.timeout_sec = timeout_sec

        # Resolve fixed allowlisted entry point and src root
        self._src_dir = str(Path(__file__).resolve().parents[2])
        self._python_exe = sys.executable
        self._worker_cmd = _worker_cmd or f'"{self._python_exe}" -m mke_product.worker.entrypoint'

    def execute_request(
        self,
        request: Union[str, bytes, Dict[str, Any]],
        timeout_sec: Optional[float] = None,
        # Failure injection points for security testing
        _inject_job_creation_failure: bool = False,
        _inject_job_config_failure: bool = False,
        _inject_process_creation_failure: bool = False,
        _inject_assignment_failure: bool = False,
        _inject_resume_failure: bool = False,
    ) -> Dict[str, Any]:
        """Execute request inside a disposable sandboxed worker and return the response."""
        effective_timeout = timeout_sec if timeout_sec is not None else self.timeout_sec

        # Extract operation if available for error envelopes
        operation = "UNKNOWN"
        if isinstance(request, dict):
            if "operation" in request and isinstance(request["operation"], str):
                operation = request["operation"]
            # Bounded pre-validation before any serialization to prevent denial of service in controller
            try:
                _measure_dict_bytes(request, max_bytes=IPC_MAX_REQUEST_BYTES)
            except ProtocolPayloadTooLargeError as err:
                return _build_controller_error(
                    "ERR_PAYLOAD_TOO_LARGE",
                    f"Request payload size exceeds maximum limit of {IPC_MAX_REQUEST_BYTES} bytes: {err}",
                    details={"max_bytes": IPC_MAX_REQUEST_BYTES},
                    operation=operation,
                )
            except ProtocolInvalidTypeError as err:
                return _build_controller_error(
                    "ERR_PROTOCOL_INVALID_TYPE",
                    f"Invalid request type: {err}",
                    operation=operation,
                )
            except ProtocolStructureError as err:
                return _build_controller_error(
                    "ERR_PROTOCOL_MALFORMED_STRUCTURE",
                    f"Malformed request structure: {err}",
                    operation=operation,
                )
            except ProtocolJsonDecodeError as err:
                return _build_controller_error(
                    "ERR_PROTOCOL_JSON_DECODE",
                    f"Invalid Unicode in request dictionary: {err}",
                    operation=operation,
                )
            except Exception as err:
                return _build_controller_error(
                    WORKER_PROTOCOL_FAILURE,
                    f"Failed to validate request dictionary: {type(err).__name__}",
                    operation=operation,
                )

            try:
                raw_payload = json.dumps(request, separators=(",", ":")).encode("utf-8")
            except (TypeError, ValueError, OverflowError) as err:
                return _build_controller_error(
                    "ERR_PROTOCOL_INVALID_TYPE",
                    f"Failed to serialize request dictionary: {err}",
                    operation=operation,
                )

        elif isinstance(request, str):
            try:
                raw_payload = request.encode("utf-8")
            except UnicodeEncodeError as err:
                return _build_controller_error(
                    "ERR_PROTOCOL_JSON_DECODE",
                    f"Payload string contains unencodable Unicode surrogates: {err}",
                    operation=operation,
                )
            if len(raw_payload) > IPC_MAX_REQUEST_BYTES:
                return _build_controller_error(
                    "ERR_PAYLOAD_TOO_LARGE",
                    f"Request payload size ({len(raw_payload)} bytes) exceeds maximum limit of {IPC_MAX_REQUEST_BYTES} bytes.",
                    details={"actual_bytes": len(raw_payload), "max_bytes": IPC_MAX_REQUEST_BYTES},
                    operation=operation,
                )
            try:
                parsed = json.loads(request)
                if isinstance(parsed, dict) and "operation" in parsed and isinstance(parsed["operation"], str):
                    operation = parsed["operation"]
            except Exception:
                pass

        elif isinstance(request, (bytes, bytearray)):
            raw_payload = bytes(request)
            if len(raw_payload) > IPC_MAX_REQUEST_BYTES:
                return _build_controller_error(
                    "ERR_PAYLOAD_TOO_LARGE",
                    f"Request payload size ({len(raw_payload)} bytes) exceeds maximum limit of {IPC_MAX_REQUEST_BYTES} bytes.",
                    details={"actual_bytes": len(raw_payload), "max_bytes": IPC_MAX_REQUEST_BYTES},
                    operation=operation,
                )
            try:
                parsed = json.loads(raw_payload.decode("utf-8"))
                if isinstance(parsed, dict) and "operation" in parsed and isinstance(parsed["operation"], str):
                    operation = parsed["operation"]
            except Exception:
                pass

        else:
            return _build_controller_error(
                "ERR_PROTOCOL_INVALID_TYPE",
                f"Unsupported request type: {type(request).__name__}.",
                operation=operation,
            )

        # Track handles for guaranteed cleanup in finally block
        h_job: Optional[wintypes.HANDLE] = None
        h_stdin_read = wintypes.HANDLE()
        h_stdin_write = wintypes.HANDLE()
        h_stdout_read = wintypes.HANDLE()
        h_stdout_write = wintypes.HANDLE()
        h_stderr_read = wintypes.HANDLE()
        h_stderr_write = wintypes.HANDLE()
        pi = PROCESS_INFORMATION()
        attr_buf: Optional[Any] = None

        try:
            # 1. Create and configure Windows Job Object
            if _inject_job_creation_failure:
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    "Injected failure during Job Object creation.",
                    operation=operation,
                )

            h_job, job_err = create_configured_job_object(
                process_memory_limit=self.process_memory_limit,
                job_memory_limit=self.job_memory_limit,
            )
            if not h_job or _inject_job_config_failure:
                safe_close_handle(h_job)
                h_job = None
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to create or configure Job Object (win32 error {job_err}).",
                    details={"win32_error": job_err},
                    operation=operation,
                )

            # 2. Create anonymous pipes with explicit handle inheritance
            sa = SECURITY_ATTRIBUTES()
            sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
            sa.bInheritHandle = True

            if not kernel32.CreatePipe(ctypes.byref(h_stdin_read), ctypes.byref(h_stdin_write), ctypes.byref(sa), 0):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to create stdin pipe (win32 error {err}).",
                    operation=operation,
                )

            if not kernel32.CreatePipe(ctypes.byref(h_stdout_read), ctypes.byref(h_stdout_write), ctypes.byref(sa), 0):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to create stdout pipe (win32 error {err}).",
                    operation=operation,
                )

            if not kernel32.CreatePipe(ctypes.byref(h_stderr_read), ctypes.byref(h_stderr_write), ctypes.byref(sa), 0):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to create stderr pipe (win32 error {err}).",
                    operation=operation,
                )

            # Ensure controller pipe ends are strictly NOT inheritable
            if not kernel32.SetHandleInformation(h_stdin_write, HANDLE_FLAG_INHERIT, 0):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to set handle information on stdin pipe (win32 error {err}).",
                    operation=operation,
                )

            if not kernel32.SetHandleInformation(h_stdout_read, HANDLE_FLAG_INHERIT, 0):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to set handle information on stdout pipe (win32 error {err}).",
                    operation=operation,
                )

            if not kernel32.SetHandleInformation(h_stderr_read, HANDLE_FLAG_INHERIT, 0):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to set handle information on stderr pipe (win32 error {err}).",
                    operation=operation,
                )

            # 3. Configure PROC_THREAD_ATTRIBUTE_HANDLE_LIST (inheriting ONLY worker pipe ends)
            attr_size = ctypes.c_size_t(0)
            kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(attr_size))
            attr_buf = ctypes.create_string_buffer(attr_size.value)
            if not kernel32.InitializeProcThreadAttributeList(attr_buf, 1, 0, ctypes.byref(attr_size)):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to initialize thread attribute list (win32 error {err}).",
                    operation=operation,
                )

            inherited_handles = (wintypes.HANDLE * 3)(h_stdin_read, h_stdout_write, h_stderr_write)
            if not kernel32.UpdateProcThreadAttribute(
                attr_buf, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
                ctypes.byref(inherited_handles), ctypes.sizeof(inherited_handles), None, None
            ):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to update proc thread attribute handle list (win32 error {err}).",
                    operation=operation,
                )

            # 4. Prepare STARTUPINFOEXW and CreateProcessW with CREATE_SUSPENDED
            siex = STARTUPINFOEXW()
            siex.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
            siex.StartupInfo.dwFlags = STARTF_USESTDHANDLES
            siex.StartupInfo.hStdInput = h_stdin_read
            siex.StartupInfo.hStdOutput = h_stdout_write
            siex.StartupInfo.hStdError = h_stderr_write
            siex.lpAttributeList = ctypes.cast(attr_buf, ctypes.c_void_p)

            cmd = self._worker_cmd
            creation_flags = EXTENDED_STARTUPINFO_PRESENT | CREATE_SUSPENDED

            if _inject_process_creation_failure:
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    "Injected failure during worker process creation.",
                    operation=operation,
                )

            cp_res = kernel32.CreateProcessW(
                None,
                ctypes.create_unicode_buffer(cmd),
                None,
                None,
                True,  # bInheritHandles
                creation_flags,
                None,
                self._src_dir,
                ctypes.byref(siex),
                ctypes.byref(pi),
            )
            if not cp_res:
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"CreateProcessW failed for worker (win32 error {err}).",
                    details={"win32_error": err},
                    operation=operation,
                )

            # Close worker ends of pipes in controller immediately after creation
            safe_close_handle(h_stdin_read)
            h_stdin_read = wintypes.HANDLE()
            safe_close_handle(h_stdout_write)
            h_stdout_write = wintypes.HANDLE()
            safe_close_handle(h_stderr_write)
            h_stderr_write = wintypes.HANDLE()

            # 5. Assign process to Job Object and verify assignment BEFORE resuming thread
            if _inject_assignment_failure:
                # Terminate suspended process immediately and fail closed
                kernel32.TerminateProcess(pi.hProcess, 1)
                return _build_controller_error(
                    WORKER_ASSIGNMENT_FAILURE,
                    "Injected failure during Job Object assignment.",
                    operation=operation,
                )

            assign_ok, assign_err = assign_and_verify_process_in_job(h_job, pi.hProcess)
            if not assign_ok:
                # Terminate suspended process immediately and fail closed
                kernel32.TerminateProcess(pi.hProcess, 1)
                return _build_controller_error(
                    WORKER_ASSIGNMENT_FAILURE,
                    f"Failed to assign or verify worker process in Job Object (win32 error {assign_err}).",
                    details={"win32_error": assign_err},
                    operation=operation,
                )

            # 6. Resume primary thread
            if _inject_resume_failure:
                kernel32.TerminateProcess(pi.hProcess, 1)
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    "Injected failure during thread resumption.",
                    operation=operation,
                )

            suspend_count = kernel32.ResumeThread(pi.hThread)
            if suspend_count == 0xFFFFFFFF:
                err = ctypes.get_last_error()
                kernel32.TerminateProcess(pi.hProcess, 1)
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"ResumeThread failed for worker (win32 error {err}).",
                    operation=operation,
                )

            # 7. Write length-prefixed request to stdin pipe
            header = struct.pack(">I", len(raw_payload))
            bytes_written = wintypes.DWORD()
            msg = header + raw_payload

            if not kernel32.WriteFile(h_stdin_write, msg, len(msg), ctypes.byref(bytes_written), None):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_PROTOCOL_FAILURE,
                    f"Failed to write request to worker pipe (win32 error {err}).",
                    operation=operation,
                )

            # Close stdin write handle to signal EOF to worker
            safe_close_handle(h_stdin_write)
            h_stdin_write = wintypes.HANDLE()

            # 8. Bounded read from stdout pipe with deterministic timeout
            deadline = time.monotonic() + effective_timeout
            response_header = self._read_exact_bytes(
                h_stdout_read, pi.hProcess, IPC_HEADER_SIZE, deadline, h_job, h_stderr=h_stderr_read
            )

            if isinstance(response_header, dict):
                # Error envelope returned from read
                return response_header

            (resp_length,) = struct.unpack(">I", response_header)
            if resp_length > IPC_MAX_RESPONSE_BYTES:
                return _build_controller_error(
                    "ERR_RESPONSE_LIMIT_EXCEEDED",
                    f"Worker response length ({resp_length} bytes) exceeds limit of {IPC_MAX_RESPONSE_BYTES} bytes.",
                    details={"response_bytes": resp_length, "max_bytes": IPC_MAX_RESPONSE_BYTES},
                    operation=operation,
                )

            response_body = self._read_exact_bytes(
                h_stdout_read, pi.hProcess, resp_length, deadline, h_job, h_stderr=h_stderr_read
            )
            if isinstance(response_body, dict):
                return response_body

            # 9. Parse and return worker response
            try:
                result = json.loads(response_body.decode("utf-8"))
                if not isinstance(result, dict):
                    return _build_controller_error(
                        WORKER_PROTOCOL_FAILURE,
                        "Worker response root is not a JSON dictionary.",
                        operation=operation,
                    )
                return result
            except Exception as exc:
                return _build_controller_error(
                    WORKER_PROTOCOL_FAILURE,
                    f"Failed to decode worker JSON response: {exc}.",
                    operation=operation,
                )

        finally:
            # 10. Guaranteed cleanup of all handles and attribute lists
            safe_close_handle(h_stdin_read)
            safe_close_handle(h_stdin_write)
            safe_close_handle(h_stdout_read)
            safe_close_handle(h_stdout_write)
            safe_close_handle(h_stderr_read)
            safe_close_handle(h_stderr_write)

            if pi.hProcess:
                # Ensure worker process terminates
                kernel32.TerminateProcess(pi.hProcess, 0)
                kernel32.WaitForSingleObject(pi.hProcess, 1000)
                safe_close_handle(pi.hProcess)
            safe_close_handle(pi.hThread)

            if attr_buf:
                try:
                    kernel32.DeleteProcThreadAttributeList(attr_buf)
                except Exception:
                    pass

            # Closing Job Object handle triggers KILL_ON_JOB_CLOSE for any remaining child processes
            safe_close_handle(h_job)

    def _read_exact_bytes(
        self,
        h_pipe: wintypes.HANDLE,
        h_process: wintypes.HANDLE,
        num_bytes: int,
        deadline: float,
        h_job: Optional[wintypes.HANDLE],
        h_stderr: Optional[wintypes.HANDLE] = None,
    ) -> Union[bytes, Dict[str, Any]]:
        """Read exactly `num_bytes` from `h_pipe` before `deadline`, checking process status."""
        accumulated = bytearray()
        while len(accumulated) < num_bytes:
            now = time.monotonic()
            if now >= deadline:
                kernel32.TerminateProcess(h_process, 1)
                return _build_controller_error(
                    WORKER_TIMEOUT,
                    f"Worker execution timed out after {self.timeout_sec} seconds.",
                )

            avail = wintypes.DWORD(0)
            peek_res = kernel32.PeekNamedPipe(h_pipe, None, 0, None, ctypes.byref(avail), None)
            if not peek_res:
                err = ctypes.get_last_error()
                # Broken pipe means worker process closed pipe (exited or crashed)
                return self._handle_worker_abnormal_exit(h_process, h_job, err, h_stderr=h_stderr)

            if avail.value > 0:
                to_read = min(num_bytes - len(accumulated), avail.value)
                buf = ctypes.create_string_buffer(to_read)
                bytes_read = wintypes.DWORD(0)
                read_res = kernel32.ReadFile(h_pipe, buf, to_read, ctypes.byref(bytes_read), None)
                if not read_res or bytes_read.value == 0:
                    err = ctypes.get_last_error()
                    return self._handle_worker_abnormal_exit(h_process, h_job, err, h_stderr=h_stderr)
                accumulated.extend(buf.raw[: bytes_read.value])
            else:
                # Check if process has terminated while no data is available
                wait_res = kernel32.WaitForSingleObject(h_process, 0)
                if wait_res == WAIT_OBJECT_0:
                    # Process died without writing expected data
                    return self._handle_worker_abnormal_exit(h_process, h_job, 0, h_stderr=h_stderr)
                time.sleep(0.01)

        return bytes(accumulated)

    def _handle_worker_abnormal_exit(
        self,
        h_process: wintypes.HANDLE,
        h_job: Optional[wintypes.HANDLE],
        pipe_error: int,
        h_stderr: Optional[wintypes.HANDLE] = None,
    ) -> Dict[str, Any]:
        """Diagnose worker failure upon pipe disconnect without fallback math execution."""
        exit_code = wintypes.DWORD()
        exit_ok = kernel32.GetExitCodeProcess(h_process, ctypes.byref(exit_code))
        code = exit_code.value if exit_ok else -1

        peak_proc, peak_job, _ = query_job_peak_memory(h_job) if h_job else (0, 0, 0)

        stderr_msg = ""
        if h_stderr:
            err_avail = wintypes.DWORD(0)
            if kernel32.PeekNamedPipe(h_stderr, None, 0, None, ctypes.byref(err_avail), None) and err_avail.value > 0:
                err_buf = ctypes.create_string_buffer(min(err_avail.value, 4096))
                err_read = wintypes.DWORD(0)
                if kernel32.ReadFile(h_stderr, err_buf, len(err_buf), ctypes.byref(err_read), None):
                    raw_stderr = err_buf.raw[: err_read.value].decode("utf-8", errors="replace").strip()
                    stderr_msg = _sanitize_error_text(raw_stderr)

        # Distinguish resource exhaustion from abnormal exit
        # Explicit test code 42 (MemoryError), NTSTATUS/Win32 commitment errors, or peak memory at/above quota
        is_memory_exhaustion = (
            code in (42, STATUS_COMMITMENT_LIMIT, ERROR_COMMITMENT_LIMIT, ERROR_NOT_ENOUGH_QUOTA)
            or (peak_proc > 0 and peak_proc >= self.process_memory_limit)
            or (peak_job > 0 and peak_job >= self.job_memory_limit)
        )

        if is_memory_exhaustion:
            return _build_controller_error(
                WORKER_RESOURCE_EXHAUSTED,
                f"Worker exceeded memory quota (exit code: {code}, peak memory: {peak_proc} bytes).",
                details={
                    "exit_code": code,
                    "peak_process_bytes": peak_proc,
                    "process_memory_limit": self.process_memory_limit,
                    "peak_job_bytes": peak_job,
                    "job_memory_limit": self.job_memory_limit,
                    "stderr": stderr_msg,
                },
            )

        return _build_controller_error(
            WORKER_EXIT_FAILURE,
            f"Worker terminated unexpectedly with exit code {code} (pipe error: {pipe_error}).",
            details={
                "exit_code": code,
                "pipe_error": pipe_error,
                "peak_process_bytes": peak_proc,
                "stderr": stderr_msg,
            },
        )


def dispatch_via_worker(
    request: Union[str, bytes, Dict[str, Any]],
    timeout_sec: float = DEFAULT_WORKER_TIMEOUT_SEC,
) -> Dict[str, Any]:
    """Convenience entry point for routing a protocol request through a sandboxed disposable worker."""
    controller = WorkerController(timeout_sec=timeout_sec)
    return controller.execute_request(request)
