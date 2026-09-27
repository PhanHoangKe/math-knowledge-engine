"""Windows Job Object worker controller and process containment manager."""

import json
import os
import re
import struct
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

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
    DUPLICATE_SAME_ACCESS,
    ERROR_BROKEN_PIPE,
    ERROR_COMMITMENT_LIMIT,
    ERROR_NOT_ENOUGH_QUOTA,
    ERROR_OPERATION_ABORTED,
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


ALLOWED_OPERATIONS = {"SOLVE", "CHECK_CANDIDATE"}


def _normalize_operation(op: Any) -> str:
    """Normalize operation to documented identifiers, preventing reflection of oversized/untrusted strings."""
    if isinstance(op, str) and op in ALLOWED_OPERATIONS:
        return op
    return "UNKNOWN"


def _build_controller_error(
    status: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    operation: Optional[str] = None,
) -> Dict[str, Any]:
    """Construct structured fail-closed error envelope matching S4 protocol taxonomy and IPC response limits."""
    norm_op = _normalize_operation(operation)
    outcome = "RESOURCE_EXHAUSTED" if status in (WORKER_RESOURCE_EXHAUSTED, WORKER_TIMEOUT) else "PROTOCOL_ERROR"
    sanitized_msg = _sanitize_error_text(message)

    envelope = {
        "schema_version": SCHEMA_VERSION,
        "operation": norm_op,
        "outcome": outcome,
        "status": status,
        "definedness": None,
        "is_provisional_evidence": False,
        "error": {
            "code": status,
            "message": sanitized_msg[:1024],
            "details": details or {},
        },
    }

    # Strict enforcement of IPC_MAX_RESPONSE_BYTES ceiling
    try:
        raw_json = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
        if len(raw_json) > IPC_MAX_RESPONSE_BYTES:
            return {
                "schema_version": SCHEMA_VERSION,
                "operation": norm_op,
                "outcome": outcome,
                "status": status,
                "definedness": None,
                "is_provisional_evidence": False,
                "error": {
                    "code": status,
                    "message": "Error response truncated to satisfy protocol response limit.",
                    "details": {"max_response_bytes": IPC_MAX_RESPONSE_BYTES},
                },
            }
    except Exception:
        # Guaranteed deterministic minimal fallback if serialization fails
        return {
            "schema_version": SCHEMA_VERSION,
            "operation": norm_op,
            "outcome": outcome,
            "status": status,
            "definedness": None,
            "is_provisional_evidence": False,
            "error": {
                "code": status,
                "message": "Error serialization failed.",
                "details": {"reason": "serialization_failure"},
            },
        }

    return envelope


# ---------------------------------------------------------------------------
# Safe Handle Ownership & Quarantine
# ---------------------------------------------------------------------------

class SafePipeHandle:
    """Thread-safe, atomic single-ownership wrapper around a Win32 pipe HANDLE.

    Guarantees:
    - Exactly-once Win32 CloseHandle execution.
    - Quarantined handles are protected from premature caller closing.
    - Idempotent close() calls across thread callbacks and controller settlement.
    """

    def __init__(self, handle: wintypes.HANDLE) -> None:
        self._handle = handle
        self._raw_val = int(handle.value) if handle and handle.value else 0
        self._lock = threading.Lock()
        self._closed = False
        self._quarantined = False

    @property
    def handle(self) -> wintypes.HANDLE:
        with self._lock:
            return self._handle

    @property
    def raw_val(self) -> int:
        return self._raw_val

    def is_quarantined(self) -> bool:
        with self._lock:
            return self._quarantined

    def is_closed(self) -> bool:
        with self._lock:
            return self._closed

    def quarantine(self) -> None:
        with self._lock:
            self._quarantined = True

    def close(self) -> bool:
        """Atomically close the underlying handle if not already closed."""
        with self._lock:
            if self._closed or not self._handle or not self._handle.value:
                return False
            h = self._handle
            self._handle = wintypes.HANDLE(0)
            self._closed = True
            safe_close_handle(h)
            return True


@dataclass
class QuarantineRecord:
    """Tracks a quarantined pipe handle awaiting worker thread exit."""
    record_id: int
    thread: Optional[threading.Thread]
    handle: SafePipeHandle
    created_at: float
    settled: bool = False
    settled_at: Optional[float] = None


class WorkerController:
    """Manages creation, execution, and containment of disposable sandboxed workers."""

    def __init__(
        self,
        process_memory_limit: int = PROCESS_MEMORY_LIMIT_BYTES,
        job_memory_limit: int = JOB_MEMORY_LIMIT_BYTES,
        timeout_sec: float = DEFAULT_WORKER_TIMEOUT_SEC,
        _worker_cmd: Optional[str] = None,
        _stdin_pipe_buffer_size: int = 0,
    ) -> None:
        self.process_memory_limit = process_memory_limit
        self.job_memory_limit = job_memory_limit
        self.timeout_sec = timeout_sec
        self._stdin_pipe_buffer_size = _stdin_pipe_buffer_size
        self._last_write_info: Optional[Dict[str, Any]] = None
        self._current_writer_thread: Optional[threading.Thread] = None

        # Thread-safe persistent quarantine ledger across requests
        self._quarantine: List[QuarantineRecord] = []
        self._quarantine_counter: int = 0
        self._quarantine_lock: threading.Lock = threading.Lock()

        # Resolve fixed allowlisted entry point and src root
        self._src_dir = str(Path(__file__).resolve().parents[2])
        self._python_exe = sys.executable
        self._worker_cmd = _worker_cmd or f'"{self._python_exe}" -m mke_product.worker.entrypoint'

    def settle_quarantine(self, timeout: float = 0.0) -> int:
        """Reap and safely release quarantined pipe handles whose worker threads have terminated.

        Args:
            timeout: Maximum seconds to wait on each active unsettled thread. Defaults to 0.0 (non-blocking).

        Returns:
            Number of newly settled quarantine records.
        """
        settled_count = 0
        with self._quarantine_lock:
            for rec in self._quarantine:
                if rec.settled:
                    continue
                if rec.thread is not None:
                    if rec.thread.is_alive() and timeout > 0:
                        rec.thread.join(timeout=timeout)
                    if not rec.thread.is_alive():
                        rec.handle.close()
                        rec.settled = True
                        rec.settled_at = time.monotonic()
                        rec.thread = None  # Release Python Thread object to free underlying OS handles
                        settled_count += 1

            # Bounded retention: retain all unsettled records plus up to 64 settled records
            unsettled = [r for r in self._quarantine if not r.settled]
            settled = [r for r in self._quarantine if r.settled]
            if len(settled) > 64:
                settled = settled[-64:]
            self._quarantine = unsettled + settled

        return settled_count

    def get_quarantine_records(self) -> List[Dict[str, Any]]:
        """Return a snapshot list of quarantine records for telemetry and verification."""
        with self._quarantine_lock:
            return [
                {
                    "record_id": r.record_id,
                    "thread_name": r.thread.name if r.thread is not None else "mke-ipc-writer",
                    "thread_alive": r.thread.is_alive() if r.thread is not None else False,
                    "handle_val": r.handle.raw_val,
                    "handle_closed": r.handle.is_closed(),
                    "created_at": r.created_at,
                    "settled": r.settled,
                    "settled_at": r.settled_at,
                }
                for r in self._quarantine
            ]

    def get_active_quarantine_count(self) -> int:
        """Return count of currently unsettled quarantined handles."""
        with self._quarantine_lock:
            return sum(1 for r in self._quarantine if not r.settled)

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
        _inject_duplicate_handle_failure: bool = False,
        _inject_cancel_io_failure: bool = False,
        _inject_writer_join_timeout: bool = False,
        _inject_normal_write_join_timeout: bool = False,
        _worker_cmd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute request inside a disposable sandboxed worker and return the response."""
        effective_timeout = timeout_sec if timeout_sec is not None else self.timeout_sec

        # Reset per-request cancellation and write telemetry before every request
        self._last_write_info = None
        self._current_writer_thread = None

        # Settle any previously completed quarantined handles before beginning new request
        self.settle_quarantine(timeout=0.0)

        # Extract normalized operation for error envelopes to prevent untrusted string reflection
        operation = "UNKNOWN"
        if isinstance(request, dict):
            if "operation" in request:
                operation = _normalize_operation(request["operation"])
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
                raw_payload = json.dumps(request, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            except (TypeError, ValueError, OverflowError) as err:
                return _build_controller_error(
                    "ERR_PROTOCOL_INVALID_TYPE",
                    f"Failed to serialize request dictionary: {err}",
                    operation=operation,
                )
            except UnicodeEncodeError as err:
                return _build_controller_error(
                    "ERR_PROTOCOL_JSON_DECODE",
                    f"Invalid Unicode in request dictionary: {err}",
                    operation=operation,
                )

            if len(raw_payload) > IPC_MAX_REQUEST_BYTES:
                return _build_controller_error(
                    "ERR_PAYLOAD_TOO_LARGE",
                    f"Request serialized payload size ({len(raw_payload)} bytes) exceeds maximum limit of {IPC_MAX_REQUEST_BYTES} bytes.",
                    details={"actual_bytes": len(raw_payload), "max_bytes": IPC_MAX_REQUEST_BYTES},
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
                if isinstance(parsed, dict) and "operation" in parsed:
                    operation = _normalize_operation(parsed["operation"])
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
                if isinstance(parsed, dict) and "operation" in parsed:
                    operation = _normalize_operation(parsed["operation"])
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
        pipe_owner: Optional[SafePipeHandle] = None
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

            raw_stdin_write = wintypes.HANDLE()
            if not kernel32.CreatePipe(ctypes.byref(h_stdin_read), ctypes.byref(raw_stdin_write), ctypes.byref(sa), self._stdin_pipe_buffer_size):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to create stdin pipe (win32 error {err}).",
                    operation=operation,
                )
            pipe_owner = SafePipeHandle(raw_stdin_write)

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
            if not kernel32.SetHandleInformation(pipe_owner.handle, HANDLE_FLAG_INHERIT, 0):
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

            cmd = _worker_cmd or self._worker_cmd
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

            # 7. Establish full-lifecycle deadline before worker IPC
            deadline = time.monotonic() + effective_timeout

            # Write length-prefixed request to stdin pipe within full-lifecycle deadline
            header = struct.pack(">I", len(raw_payload))
            msg = header + raw_payload

            write_res = self._write_exact_bytes_with_timeout(
                pipe_owner,
                msg,
                deadline,
                pi.hProcess,
                h_job,
                operation=operation,
                _inject_duplicate_handle_failure=_inject_duplicate_handle_failure,
                _inject_cancel_io_failure=_inject_cancel_io_failure,
                _inject_writer_join_timeout=_inject_writer_join_timeout,
                _inject_normal_write_join_timeout=_inject_normal_write_join_timeout,
            )
            if isinstance(write_res, dict):
                return write_res

            # Close stdin write handle to signal EOF to worker
            if pipe_owner is not None:
                pipe_owner.close()

            # 8. Bounded read from stdout pipe with same effective deadline
            response_header = self._read_exact_bytes(
                h_stdout_read, pi.hProcess, IPC_HEADER_SIZE, deadline, h_job, h_stderr=h_stderr_read, operation=operation
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
                h_stdout_read, pi.hProcess, resp_length, deadline, h_job, h_stderr=h_stderr_read, operation=operation
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
            h_stdin_read = wintypes.HANDLE()

            # Handle ownership invariant: close pipe_owner ONLY IF not quarantined
            if pipe_owner is not None and not pipe_owner.is_quarantined():
                pipe_owner.close()

            safe_close_handle(h_stdout_read)
            h_stdout_read = wintypes.HANDLE()
            safe_close_handle(h_stdout_write)
            h_stdout_write = wintypes.HANDLE()
            safe_close_handle(h_stderr_read)
            h_stderr_read = wintypes.HANDLE()
            safe_close_handle(h_stderr_write)
            h_stderr_write = wintypes.HANDLE()

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

    def _handle_worker_timeout(
        self,
        h_process: wintypes.HANDLE,
        h_job: Optional[wintypes.HANDLE],
        timeout_phase: str = "UNKNOWN",
        operation: str = "UNKNOWN",
        safe_cleanup: bool = True,
    ) -> Dict[str, Any]:
        """Build structured timeout error after terminating worker."""
        kernel32.TerminateProcess(h_process, 0x00000102)
        peak_proc, peak_job, _ = query_job_peak_memory(h_job) if h_job else (0, 0, 0)
        return _build_controller_error(
            WORKER_TIMEOUT,
            f"Worker execution timed out during {timeout_phase} phase after {self.timeout_sec} seconds.",
            details={
                "timeout_phase": timeout_phase,
                "timeout_sec": self.timeout_sec,
                "peak_process_bytes": peak_proc,
                "peak_job_bytes": peak_job,
                "safe_cleanup": safe_cleanup,
            },
            operation=operation,
        )

    def _write_exact_bytes_with_timeout(
        self,
        pipe_owner: SafePipeHandle,
        data: bytes,
        deadline: float,
        h_process: wintypes.HANDLE,
        h_job: Optional[wintypes.HANDLE],
        operation: str = "UNKNOWN",
        _inject_duplicate_handle_failure: bool = False,
        _inject_cancel_io_failure: bool = False,
        _inject_writer_join_timeout: bool = False,
        _inject_normal_write_join_timeout: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Write exact bytes to pipe within full-lifecycle deadline, handling partial writes and blocking worker."""
        write_error = [None]
        bytes_written_total = [0]
        write_done = threading.Event()
        setup_done = threading.Event()
        write_in_progress = threading.Event()
        dup_success = [False]
        dup_error = [0]
        write_status = ["NOT_STARTED"]
        h_thread_real = wintypes.HANDLE()

        def _writer():
            try:
                if _inject_duplicate_handle_failure:
                    dup_ok = False
                    ctypes.set_last_error(5)  # ERROR_ACCESS_DENIED
                else:
                    cur_proc = kernel32.GetCurrentProcess()
                    cur_th = kernel32.GetCurrentThread()
                    dup_ok = bool(kernel32.DuplicateHandle(
                        cur_proc,
                        cur_th,
                        cur_proc,
                        ctypes.byref(h_thread_real),
                        0,
                        False,
                        DUPLICATE_SAME_ACCESS,
                    ))

                if not dup_ok:
                    dup_error[0] = ctypes.get_last_error()
                    dup_success[0] = False
                    write_status[0] = "DUPLICATE_HANDLE_FAILED"
                    setup_done.set()
                    return

                dup_success[0] = True
                write_status[0] = "ENTERED"
                setup_done.set()

                total = 0
                while total < len(data):
                    chunk = data[total:]
                    written = wintypes.DWORD()
                    write_in_progress.set()
                    ok = kernel32.WriteFile(pipe_owner.handle, chunk, len(chunk), ctypes.byref(written), None)
                    err = ctypes.get_last_error()
                    write_in_progress.clear()
                    if not ok:
                        write_error[0] = err
                        if err == ERROR_OPERATION_ABORTED:
                            write_status[0] = "ABORTED"
                        elif err == ERROR_BROKEN_PIPE:
                            write_status[0] = "BROKEN_PIPE"
                        else:
                            write_status[0] = f"WIN32_ERROR_{err}"
                        return
                    if written.value == 0:
                        write_error[0] = 0
                        write_status[0] = "ZERO_BYTES_WRITTEN"
                        return
                    total += written.value
                    bytes_written_total[0] = total
                write_status[0] = "COMPLETED"
            except Exception as ex:
                write_error[0] = ex
                write_status[0] = f"EXCEPTION_{type(ex).__name__}"
            finally:
                write_in_progress.clear()
                write_done.set()
                if _inject_writer_join_timeout or _inject_normal_write_join_timeout:
                    time.sleep(0.3)
                # Deferred release: if quarantined, safely close handle upon thread termination
                if pipe_owner.is_quarantined():
                    pipe_owner.close()

        writer_thread = threading.Thread(target=_writer, daemon=True, name="mke-ipc-writer")
        self._current_writer_thread = writer_thread
        writer_thread.start()
        setup_done.wait(timeout=1.0)

        # Check DuplicateHandle status before proceeding
        if not dup_success[0]:
            writer_thread.join(timeout=1.0)
            writer_exited = not writer_thread.is_alive()
            self._last_write_info = {
                "duplicate_handle_success": False,
                "duplicate_handle_error": dup_error[0],
                "write_entered": False,
                "write_blocked_at_deadline": False,
                "cancellation_requested": False,
                "cancel_synchronous_io_called": False,
                "cancel_synchronous_io_success": False,
                "cancel_synchronous_io_return": None,
                "cancel_synchronous_io_last_error": None,
                "writer_thread_alive_before_cancel": False,
                "writer_thread_alive_after_join": not writer_exited,
                "write_file_status": write_status[0],
                "writer_exited": writer_exited,
                "all_handles_safely_released": writer_exited,
                "bytes_written": 0,
                "total_bytes": len(data),
            }
            return _build_controller_error(
                WORKER_STARTUP_FAILURE,
                f"Failed to duplicate writer thread handle for safe cancellation (win32 error {dup_error[0]}).",
                details={"win32_error": dup_error[0]},
                operation=operation,
            )

        write_timed_out = False
        abnormal_exit_code = None

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                write_timed_out = True
                break

            if write_done.wait(timeout=min(0.02, remaining)):
                break

            # Check if worker process terminated prematurely while writing
            exit_code = wintypes.DWORD()
            if kernel32.GetExitCodeProcess(h_process, ctypes.byref(exit_code)):
                if exit_code.value != 259:  # STILL_ACTIVE
                    abnormal_exit_code = exit_code.value
                    break

        if write_timed_out:
            write_blocked = write_in_progress.is_set()
            writer_alive_before = writer_thread.is_alive()
            cancel_called = True
            cancel_ret = False
            cancel_err = 0

            if _inject_cancel_io_failure:
                cancel_ret = False
                cancel_err = 1168  # ERROR_NOT_FOUND
            elif h_thread_real.value:
                cancel_ret = bool(kernel32.CancelSynchronousIo(h_thread_real))
                if not cancel_ret:
                    cancel_err = ctypes.get_last_error()

            kernel32.TerminateProcess(h_process, 0x00000102)

            join_timeout = 0.001 if _inject_writer_join_timeout else 2.0
            writer_thread.join(timeout=join_timeout)
            writer_exited = not writer_thread.is_alive()

            quarantined = False
            if not writer_exited:
                pipe_owner.quarantine()
                quarantined = True
                with self._quarantine_lock:
                    self._quarantine_counter += 1
                    rec = QuarantineRecord(
                        record_id=self._quarantine_counter,
                        thread=writer_thread,
                        handle=pipe_owner,
                        created_at=time.monotonic(),
                        settled=False,
                        settled_at=None,
                    )
                    self._quarantine.append(rec)

            self._last_write_info = {
                "duplicate_handle_success": True,
                "duplicate_handle_error": 0,
                "write_entered": True,
                "write_blocked_at_deadline": write_blocked,
                "cancellation_requested": cancel_called,
                "cancel_synchronous_io_called": cancel_called,
                "cancel_synchronous_io_success": cancel_ret,
                "cancel_synchronous_io_return": cancel_ret,
                "cancel_synchronous_io_last_error": cancel_err,
                "writer_thread_alive_before_cancel": writer_alive_before,
                "writer_thread_alive_after_join": not writer_exited,
                "write_file_status": write_status[0],
                "writer_exited": writer_exited,
                "all_handles_safely_released": writer_exited,
                "handle_quarantined": quarantined,
                "bytes_written": bytes_written_total[0],
                "total_bytes": len(data),
            }

            safe_close_handle(h_thread_real)
            h_thread_real = wintypes.HANDLE()

            if not writer_exited:
                # Do NOT claim safe cleanup if writer thread is still running
                return _build_controller_error(
                    WORKER_TIMEOUT,
                    "Worker execution timed out during WRITE phase and writer thread failed to terminate safely within deadline.",
                    details={
                        "timeout_phase": "WRITE",
                        "safe_cleanup": False,
                        "writer_exited": False,
                        "handle_quarantined": True,
                        "cancel_synchronous_io_return": cancel_ret,
                        "cancel_synchronous_io_last_error": cancel_err,
                        "timeout_sec": self.timeout_sec,
                    },
                    operation=operation,
                )

            return self._handle_worker_timeout(
                h_process, h_job, timeout_phase="WRITE", operation=operation, safe_cleanup=True
            )

        if abnormal_exit_code is not None:
            cancel_called = False
            cancel_ret = None
            cancel_err = None
            if h_thread_real.value:
                cancel_called = True
                cancel_ret = bool(kernel32.CancelSynchronousIo(h_thread_real))
                cancel_err = 0 if cancel_ret else ctypes.get_last_error()

            writer_thread.join(timeout=2.0)
            writer_exited = not writer_thread.is_alive()
            safe_close_handle(h_thread_real)
            h_thread_real = wintypes.HANDLE()

            quarantined = False
            if not writer_exited:
                pipe_owner.quarantine()
                quarantined = True
                with self._quarantine_lock:
                    self._quarantine_counter += 1
                    rec = QuarantineRecord(
                        record_id=self._quarantine_counter,
                        thread=writer_thread,
                        handle=pipe_owner,
                        created_at=time.monotonic(),
                        settled=False,
                        settled_at=None,
                    )
                    self._quarantine.append(rec)

            self._last_write_info = {
                "duplicate_handle_success": True,
                "duplicate_handle_error": 0,
                "write_entered": True,
                "write_blocked_at_deadline": False,
                "cancellation_requested": cancel_called,
                "cancel_synchronous_io_called": cancel_called,
                "cancel_synchronous_io_success": bool(cancel_ret),
                "cancel_synchronous_io_return": cancel_ret,
                "cancel_synchronous_io_last_error": cancel_err,
                "writer_thread_alive_before_cancel": False,
                "writer_thread_alive_after_join": not writer_exited,
                "write_file_status": write_status[0],
                "writer_exited": writer_exited,
                "all_handles_safely_released": writer_exited,
                "handle_quarantined": quarantined,
                "bytes_written": bytes_written_total[0],
                "total_bytes": len(data),
            }

            return self._handle_worker_abnormal_exit(
                h_process, h_job, abnormal_exit_code, operation=operation
            )

        join_timeout = 0.001 if _inject_normal_write_join_timeout else 2.0
        writer_thread.join(timeout=join_timeout)
        writer_exited = not writer_thread.is_alive()
        safe_close_handle(h_thread_real)
        h_thread_real = wintypes.HANDLE()

        quarantined = False
        if not writer_exited:
            pipe_owner.quarantine()
            quarantined = True
            with self._quarantine_lock:
                self._quarantine_counter += 1
                rec = QuarantineRecord(
                    record_id=self._quarantine_counter,
                    thread=writer_thread,
                    handle=pipe_owner,
                    created_at=time.monotonic(),
                    settled=False,
                    settled_at=None,
                )
                self._quarantine.append(rec)

        self._last_write_info = {
            "duplicate_handle_success": True,
            "duplicate_handle_error": 0,
            "write_entered": True,
            "write_blocked_at_deadline": False,
            "cancellation_requested": False,
            "cancel_synchronous_io_called": False,
            "cancel_synchronous_io_success": False,
            "cancel_synchronous_io_return": None,
            "cancel_synchronous_io_last_error": None,
            "writer_thread_alive_before_cancel": False,
            "writer_thread_alive_after_join": not writer_exited,
            "write_file_status": write_status[0],
            "writer_exited": writer_exited,
            "all_handles_safely_released": writer_exited,
            "handle_quarantined": quarantined,
            "bytes_written": bytes_written_total[0],
            "total_bytes": len(data),
        }

        if not writer_exited:
            return _build_controller_error(
                WORKER_TIMEOUT,
                "Worker writer thread failed to exit cleanly after write completion.",
                details={
                    "timeout_phase": "WRITE",
                    "safe_cleanup": False,
                    "writer_exited": False,
                    "handle_quarantined": True,
                },
                operation=operation,
            )

        if write_error[0] is not None:
            exit_code = wintypes.DWORD()
            if kernel32.GetExitCodeProcess(h_process, ctypes.byref(exit_code)):
                if exit_code.value != 259:
                    return self._handle_worker_abnormal_exit(
                        h_process, h_job, exit_code.value, operation=operation
                    )
            return _build_controller_error(
                WORKER_PROTOCOL_FAILURE,
                f"Failed to write request to worker pipe (win32 error {write_error[0]}).",
                operation=operation,
            )

        return None

    def _read_exact_bytes(
        self,
        h_pipe: wintypes.HANDLE,
        h_process: wintypes.HANDLE,
        num_bytes: int,
        deadline: float,
        h_job: Optional[wintypes.HANDLE],
        h_stderr: Optional[wintypes.HANDLE] = None,
        operation: str = "UNKNOWN",
    ) -> Union[bytes, Dict[str, Any]]:
        """Read exactly `num_bytes` from `h_pipe` before `deadline`, checking process status."""
        accumulated = bytearray()
        while len(accumulated) < num_bytes:
            now = time.monotonic()
            if now >= deadline:
                return self._handle_worker_timeout(h_process, h_job, timeout_phase="READ", operation=operation)

            avail = wintypes.DWORD(0)
            peek_res = kernel32.PeekNamedPipe(h_pipe, None, 0, None, ctypes.byref(avail), None)
            if not peek_res:
                err = ctypes.get_last_error()
                # Broken pipe means worker process closed pipe (exited or crashed)
                return self._handle_worker_abnormal_exit(h_process, h_job, err, h_stderr=h_stderr, operation=operation)

            if avail.value > 0:
                to_read = min(num_bytes - len(accumulated), avail.value)
                buf = ctypes.create_string_buffer(to_read)
                bytes_read = wintypes.DWORD(0)
                read_res = kernel32.ReadFile(h_pipe, buf, to_read, ctypes.byref(bytes_read), None)
                if not read_res or bytes_read.value == 0:
                    err = ctypes.get_last_error()
                    return self._handle_worker_abnormal_exit(h_process, h_job, err, h_stderr=h_stderr, operation=operation)
                accumulated.extend(buf.raw[: bytes_read.value])
            else:
                # Check if process has terminated while no data is available
                wait_res = kernel32.WaitForSingleObject(h_process, 0)
                if wait_res == WAIT_OBJECT_0:
                    # Process died without writing expected data
                    return self._handle_worker_abnormal_exit(h_process, h_job, 0, h_stderr=h_stderr, operation=operation)
                time.sleep(0.01)

        return bytes(accumulated)

    def _handle_worker_abnormal_exit(
        self,
        h_process: wintypes.HANDLE,
        h_job: Optional[wintypes.HANDLE],
        pipe_error: int,
        h_stderr: Optional[wintypes.HANDLE] = None,
        operation: str = "UNKNOWN",
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
                operation=operation,
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
            operation=operation,
        )


def dispatch_via_worker(
    request: Union[str, bytes, Dict[str, Any]],
    timeout_sec: float = DEFAULT_WORKER_TIMEOUT_SEC,
) -> Dict[str, Any]:
    """Convenience entry point for routing a protocol request through a sandboxed disposable worker."""
    controller = WorkerController(timeout_sec=timeout_sec)
    return controller.execute_request(request)
