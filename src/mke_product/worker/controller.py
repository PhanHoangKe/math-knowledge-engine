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
    CREATE_UNICODE_ENVIRONMENT,
    DEFAULT_WORKER_TIMEOUT_SEC,
    DUPLICATE_SAME_ACCESS,
    ERROR_BROKEN_PIPE,
    ERROR_COMMITMENT_LIMIT,
    ERROR_INVALID_HANDLE,
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
    PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
    STARTF_USESTDHANDLES,
    STATUS_COMMITMENT_LIMIT,
    STILL_ACTIVE,
    WAIT_OBJECT_0,
    WAIT_FAILED,
    WAIT_TIMEOUT,
    WORKER_ASSIGNMENT_FAILURE,
    WORKER_EXIT_FAILURE,
    WORKER_PROTOCOL_FAILURE,
    WORKER_RESOURCE_EXHAUSTED,
    WORKER_STARTUP_FAILURE,
    WORKER_TIMEOUT,
)
from .appcontainer import (
    AppContainerLease,
    cleanup_appcontainer_runtime,
    get_appcontainer_manager,
    verify_appcontainer_process_token,
)
from .win32 import (
    PROCESS_INFORMATION,
    SECURITY_ATTRIBUTES,
    STARTUPINFOEXW,
    assign_and_verify_process_in_job,
    claim_last_job_object_cleanup_failure,
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


ALLOWED_OPERATIONS = {"SOLVE", "CHECK_CANDIDATE", "SOLVE_QUADRATIC", "SOLVE_QUADRATIC_SURD"}


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
# Safe Handle Ownership & Quarantine (F6 & F7)
# ---------------------------------------------------------------------------

MAX_ACTIVE_QUARANTINE = 32

STATE_OPEN = "OPEN"
STATE_CLOSING = "CLOSING"
STATE_CONFIRMED_CLOSED = "CONFIRMED_CLOSED"
STATE_CLOSE_FAILED = "CLOSE_FAILED"

CLOSE_EVIDENCE_NONE = "NONE"
CLOSE_EVIDENCE_INJECTED_BEFORE_CLOSE = "INJECTED_BEFORE_CLOSE"
CLOSE_EVIDENCE_NATIVE_FAILURE = "NATIVE_CLOSE_FAILURE"
CLOSE_EVIDENCE_INVALID_HANDLE = "INVALID_OR_STALE_HANDLE"
CLOSE_EVIDENCE_CONFIRMED_CLOSED = "CONFIRMED_SUCCESSFUL_CLOSURE"

HANDLE_VALID = "VALID"
HANDLE_INVALID = "INVALID"
HANDLE_VALIDITY_UNKNOWN = "UNKNOWN"


class SafeWin32Handle:
    """Thread-safe, atomic single-ownership wrapper around a Win32 HANDLE with strict state tracking.

    Guarantees:
    - Explicit state transitions: OPEN -> CLOSING -> CONFIRMED_CLOSED or CLOSE_FAILED.
    - Preserves ownership and diagnostic information on failure (raw handle value, error code).
    - Idempotent close() calls across thread callbacks and controller settlement.
    - Never reports successful release unless Win32 CloseHandle is confirmed.
    """

    def __init__(
        self,
        handle: Optional[Union[wintypes.HANDLE, int]] = None,
        _inject_close_failure: bool = False,
    ) -> None:
        if isinstance(handle, int):
            self._handle = wintypes.HANDLE(handle)
            self._raw_val = handle
        elif isinstance(handle, wintypes.HANDLE):
            self._handle = handle
            self._raw_val = int(handle.value) if handle.value is not None else 0
        else:
            self._handle = wintypes.HANDLE(0)
            self._raw_val = 0

        self._lock = threading.Lock()
        self._state: str = STATE_OPEN if self._raw_val else STATE_CONFIRMED_CLOSED
        self._close_success: bool = (self._state == STATE_CONFIRMED_CLOSED)
        self._close_error: int = 0
        self._close_attempts: int = 0
        self._quarantined: bool = False
        self._inject_close_failure: bool = _inject_close_failure
        self._close_evidence: str = CLOSE_EVIDENCE_NONE
        self._native_close_attempted: bool = False
        self._validity_before_close: str = HANDLE_VALIDITY_UNKNOWN
        self._validity_after_close: str = HANDLE_VALIDITY_UNKNOWN
        self._close_blocked_reason: Optional[str] = None

    def set_handle(self, handle: Union[wintypes.HANDLE, int]) -> None:
        with self._lock:
            if isinstance(handle, int):
                self._handle = wintypes.HANDLE(handle)
                self._raw_val = handle
            else:
                self._handle = handle
                self._raw_val = int(handle.value) if handle.value is not None else 0
            self._state = STATE_OPEN if self._raw_val else STATE_CONFIRMED_CLOSED
            self._close_success = (self._state == STATE_CONFIRMED_CLOSED)
            self._close_error = 0
            self._close_evidence = CLOSE_EVIDENCE_NONE
            self._native_close_attempted = False
            self._validity_before_close = HANDLE_VALIDITY_UNKNOWN
            self._validity_after_close = HANDLE_VALIDITY_UNKNOWN
            self._close_blocked_reason = None

    @property
    def handle(self) -> wintypes.HANDLE:
        with self._lock:
            return self._handle

    @property
    def raw_handle(self) -> Optional[wintypes.HANDLE]:
        with self._lock:
            return self._handle if (self._handle and self._handle.value) else None

    @property
    def raw_val(self) -> int:
        return self._raw_val

    def raw_value(self) -> int:
        return self._raw_val

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def close_success(self) -> bool:
        with self._lock:
            return self._state == STATE_CONFIRMED_CLOSED

    @property
    def close_error(self) -> int:
        with self._lock:
            return self._close_error

    @property
    def close_attempts(self) -> int:
        with self._lock:
            return self._close_attempts

    @property
    def close_evidence(self) -> str:
        with self._lock:
            return self._close_evidence

    @property
    def native_close_attempted(self) -> bool:
        with self._lock:
            return self._native_close_attempted

    @property
    def validity_before_close(self) -> str:
        with self._lock:
            return self._validity_before_close

    @property
    def validity_after_close(self) -> str:
        with self._lock:
            return self._validity_after_close

    @property
    def close_blocked_reason(self) -> Optional[str]:
        with self._lock:
            return self._close_blocked_reason

    def block_close(self, reason: str) -> None:
        """Prevent handle release while another native ownership invariant is unresolved."""
        with self._lock:
            self._close_blocked_reason = reason

    def unblock_close(self) -> None:
        with self._lock:
            self._close_blocked_reason = None

    def _query_validity_locked(self) -> Tuple[str, int]:
        flags = wintypes.DWORD()
        ctypes.set_last_error(0)
        if kernel32.GetHandleInformation(self._handle, ctypes.byref(flags)):
            return HANDLE_VALID, 0
        err = ctypes.get_last_error()
        if err == ERROR_INVALID_HANDLE:
            return HANDLE_INVALID, err
        return HANDLE_VALIDITY_UNKNOWN, err

    def is_quarantined(self) -> bool:
        with self._lock:
            return self._quarantined

    def is_open(self) -> bool:
        with self._lock:
            return self._state == STATE_OPEN

    def is_confirmed_closed(self) -> bool:
        with self._lock:
            return self._state == STATE_CONFIRMED_CLOSED

    def is_closed(self) -> bool:
        """Alias for is_confirmed_closed. Strictly False if open, closing, or close failed."""
        with self._lock:
            return self._state == STATE_CONFIRMED_CLOSED

    def is_close_failed(self) -> bool:
        with self._lock:
            return self._state == STATE_CLOSE_FAILED

    def quarantine(self) -> None:
        with self._lock:
            self._quarantined = True

    def close(
        self,
        _inject_failure: Optional[bool] = None,
        *,
        _allow_native_retry: bool = False,
    ) -> bool:
        """Close with explicit Win32 evidence and a conservative recovery policy.

        Pre-call injected failures are retryable because CloseHandle was never invoked.
        A genuine native failure is ambiguous and is never retried implicitly; callers
        must first correct the native condition and explicitly set
        ``_allow_native_retry=True``. Invalid/stale values are retained as diagnostic
        evidence and are not treated as successful closure. A numeric value alone is
        never used as proof of ownership or validity.
        """
        with self._lock:
            if self._state == STATE_CONFIRMED_CLOSED:
                return True
            if not self._handle or not self._handle.value:
                self._state = STATE_CONFIRMED_CLOSED
                self._close_success = True
                self._close_evidence = CLOSE_EVIDENCE_CONFIRMED_CLOSED
                return True

            if self._close_blocked_reason is not None:
                return False

            if (
                self._state == STATE_CLOSE_FAILED
                and self._close_evidence in (CLOSE_EVIDENCE_NATIVE_FAILURE, CLOSE_EVIDENCE_INVALID_HANDLE)
                and not _allow_native_retry
            ):
                return False

            self._close_attempts += 1
            self._state = STATE_CLOSING
            h = self._handle

            inject = self._inject_close_failure if _inject_failure is None else _inject_failure
            if inject:
                validity, _ = self._query_validity_locked()
                self._validity_before_close = validity
                self._validity_after_close = validity
                self._native_close_attempted = False
                self._close_evidence = CLOSE_EVIDENCE_INJECTED_BEFORE_CLOSE
                self._state = STATE_CLOSE_FAILED
                self._close_success = False
                self._close_error = 5  # ERROR_ACCESS_DENIED
                return False

            validity, validity_err = self._query_validity_locked()
            self._validity_before_close = validity
            if validity == HANDLE_INVALID:
                self._native_close_attempted = False
                self._close_evidence = CLOSE_EVIDENCE_INVALID_HANDLE
                self._state = STATE_CLOSE_FAILED
                self._close_success = False
                self._close_error = validity_err
                self._validity_after_close = HANDLE_INVALID
                return False

            self._native_close_attempted = True
            ok, err = safe_close_handle(h)
            if ok:
                after, _ = self._query_validity_locked()
                self._validity_after_close = after
                self._close_evidence = CLOSE_EVIDENCE_CONFIRMED_CLOSED
                self._state = STATE_CONFIRMED_CLOSED
                self._handle = wintypes.HANDLE(0)
                self._close_success = True
                self._close_error = 0
                return True
            else:
                after, _ = self._query_validity_locked()
                self._validity_after_close = after
                self._close_evidence = CLOSE_EVIDENCE_NATIVE_FAILURE
                self._state = STATE_CLOSE_FAILED
                self._close_success = False
                self._close_error = err
                return False

    def recover_native_close(self) -> bool:
        """Explicitly retry after an operator/test has corrected a native close condition.

        This is intentionally separate from ledger reconciliation so a genuine,
        ambiguous CloseHandle failure can never be retried as a side effect of a
        later request.
        """
        return self.close(_inject_failure=False, _allow_native_retry=True)

    def adopt_native_close_failure(
        self,
        error: int,
        *,
        handle_valid_after_failure: Optional[bool] = None,
    ) -> None:
        """Adopt an already-attempted ambiguous native close without retrying it."""
        with self._lock:
            self._close_attempts = max(self._close_attempts, 1)
            self._native_close_attempted = True
            self._close_evidence = CLOSE_EVIDENCE_NATIVE_FAILURE
            self._close_error = error
            self._close_success = False
            self._state = STATE_CLOSE_FAILED
            if handle_valid_after_failure is True:
                self._validity_after_close = HANDLE_VALID
            elif handle_valid_after_failure is False:
                self._validity_after_close = HANDLE_INVALID
            else:
                self._validity_after_close = HANDLE_VALIDITY_UNKNOWN


class SafePipeHandle(SafeWin32Handle):
    """Specialized wrapper for pipe handles."""
    pass


class SafeThreadHandle(SafeWin32Handle):
    """Specialized wrapper for duplicated and primary thread handles."""
    pass


class SafeProcessHandle(SafeWin32Handle):
    """Specialized wrapper for worker process handles."""
    pass


@dataclass
class QuarantineRecord:
    """Tracks quarantined pipe and thread handles awaiting worker thread exit."""
    record_id: int
    thread: Optional[threading.Thread]
    handle: Optional[SafePipeHandle]
    thread_handle: Optional[SafeThreadHandle]
    handle_val: int
    thread_handle_val: int
    handle_closed: bool
    thread_handle_closed: bool
    handle_close_error: int
    thread_handle_close_error: int
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
        self._last_job_owner: Optional[SafeWin32Handle] = None
        self._last_process_owner: Optional[SafeProcessHandle] = None
        self._current_writer_thread: Optional[threading.Thread] = None

        # Reentrancy lock enforcing single-request-at-a-time contract
        self._request_lock: threading.Lock = threading.Lock()

        # Thread-safe persistent quarantine ledger across requests
        self._quarantine: List[QuarantineRecord] = []
        self._quarantine_counter: int = 0
        self._quarantine_lock: threading.Lock = threading.Lock()

        # Thread-safe bounded persistent ledgers for unresolved handles across requests (Task 1 & Task 2)
        self._unresolved_job_handles: List[SafeWin32Handle] = []
        self._unresolved_handles: List[SafeWin32Handle] = []
        self._unresolved_process_termination: Dict[int, Dict[str, Any]] = {}
        self._last_termination_evidence: Optional[Dict[str, Any]] = None
        self._last_appcontainer_evidence: Optional[Dict[str, Any]] = None
        self._deferred_appcontainer_leases: Dict[int, AppContainerLease] = {}

        # Resolve fixed allowlisted entry point and src root
        self._src_dir = str(Path(__file__).resolve().parents[2])
        self._python_exe = sys.executable
        self._custom_worker_cmd = _worker_cmd
        self._worker_cmd = _worker_cmd or f'"{self._python_exe}" -m mke_product.worker.entrypoint'

    def get_last_appcontainer_evidence(self) -> Optional[Dict[str, Any]]:
        """Return the latest native pre-resume AppContainer verification."""
        return dict(self._last_appcontainer_evidence) if self._last_appcontainer_evidence else None

    @staticmethod
    def cleanup_appcontainer_runtime() -> Dict[str, Any]:
        """Delete staged assets/profile only if no child lease remains active."""
        return cleanup_appcontainer_runtime()

    def get_unresolved_job_handles(self) -> List[SafeWin32Handle]:
        """Return list of active unresolved Job Object handle owners."""
        with self._quarantine_lock:
            return [h for h in self._unresolved_job_handles if not h.is_confirmed_closed()]

    def get_unresolved_handles(self) -> List[SafeWin32Handle]:
        """Return list of active unresolved general handle owners."""
        with self._quarantine_lock:
            return [h for h in self._unresolved_handles if not h.is_confirmed_closed()]

    def get_unresolved_count(self) -> int:
        """Return total count of active unresolved handles."""
        with self._quarantine_lock:
            return (
                sum(1 for h in self._unresolved_job_handles if not h.is_confirmed_closed()) +
                sum(1 for h in self._unresolved_handles if not h.is_confirmed_closed())
            )

    def get_last_termination_evidence(self) -> Optional[Dict[str, Any]]:
        """Return a copy of the latest process-termination evidence."""
        return dict(self._last_termination_evidence) if self._last_termination_evidence else None

    def _observe_process_termination(
        self,
        owner: SafeProcessHandle,
        wait_ms: int = 0,
    ) -> Dict[str, Any]:
        """Observe termination without issuing a new termination request."""
        exit_code = wintypes.DWORD()
        ctypes.set_last_error(0)
        exit_ok = bool(kernel32.GetExitCodeProcess(owner.handle, ctypes.byref(exit_code)))
        exit_error = 0 if exit_ok else ctypes.get_last_error()
        ctypes.set_last_error(0)
        wait_result = int(kernel32.WaitForSingleObject(owner.handle, wait_ms))
        wait_error = ctypes.get_last_error() if wait_result == WAIT_FAILED else 0
        confirmed = bool(exit_ok and exit_code.value != STILL_ACTIVE and wait_result == WAIT_OBJECT_0)
        return {
            "state": "ALREADY_TERMINATED" if confirmed else "TERMINATION_UNCERTAIN_OR_FAILED",
            "termination_request_state": "NOT_REQUIRED_ALREADY_TERMINATED" if confirmed else "NOT_REQUESTED",
            "termination_confirmation_state": "CONFIRMED" if confirmed else "UNCERTAIN_OR_FAILED",
            "already_terminated": confirmed,
            "termination_requested": False,
            "termination_request_succeeded": False,
            "termination_confirmed": confirmed,
            "terminate_error": 0,
            "wait_result": wait_result,
            "wait_error": wait_error,
            "exit_code_query_succeeded": exit_ok,
            "exit_code_error": exit_error,
            "exit_code": int(exit_code.value) if exit_ok else None,
        }

    def _terminate_and_confirm_process(
        self,
        owner: SafeProcessHandle,
        *,
        _inject_terminate_process_failure: bool = False,
        _inject_termination_wait_timeout: bool = False,
        _inject_termination_wait_failure: bool = False,
        _inject_exit_code_failure: bool = False,
    ) -> Dict[str, Any]:
        """Request termination when needed and require wait plus exit-code confirmation."""
        initial = self._observe_process_termination(owner, wait_ms=0)
        if initial["termination_confirmed"]:
            self._last_termination_evidence = initial
            return initial

        if _inject_terminate_process_failure:
            terminate_ok = False
            terminate_error = 5
        else:
            ctypes.set_last_error(0)
            terminate_ok = bool(kernel32.TerminateProcess(owner.handle, 0))
            terminate_error = 0 if terminate_ok else ctypes.get_last_error()

        if _inject_termination_wait_failure:
            wait_result = WAIT_FAILED
            wait_error = 6
        elif _inject_termination_wait_timeout:
            wait_result = WAIT_TIMEOUT
            wait_error = 0
        else:
            ctypes.set_last_error(0)
            wait_result = int(kernel32.WaitForSingleObject(owner.handle, 1000))
            wait_error = ctypes.get_last_error() if wait_result == WAIT_FAILED else 0

        exit_code = wintypes.DWORD()
        if _inject_exit_code_failure:
            exit_ok = False
            exit_error = 6
        else:
            ctypes.set_last_error(0)
            exit_ok = bool(kernel32.GetExitCodeProcess(owner.handle, ctypes.byref(exit_code)))
            exit_error = 0 if exit_ok else ctypes.get_last_error()

        confirmed = bool(wait_result == WAIT_OBJECT_0 and exit_ok and exit_code.value != STILL_ACTIVE)
        evidence = {
            "state": "TERMINATION_CONFIRMED" if confirmed else "TERMINATION_UNCERTAIN_OR_FAILED",
            "termination_request_state": "REQUESTED_SUCCESSFULLY" if terminate_ok else "REQUEST_FAILED",
            "termination_confirmation_state": "CONFIRMED" if confirmed else "UNCERTAIN_OR_FAILED",
            "already_terminated": False,
            "termination_requested": True,
            "termination_request_succeeded": terminate_ok,
            "termination_confirmed": confirmed,
            "terminate_error": terminate_error,
            "wait_result": wait_result,
            "wait_error": wait_error,
            "exit_code_query_succeeded": exit_ok,
            "exit_code_error": exit_error,
            "exit_code": int(exit_code.value) if exit_ok else None,
        }
        self._last_termination_evidence = evidence
        return evidence

    def reconcile_unresolved_resources(self) -> int:
        """Reconcile only resources with non-ambiguous recovery evidence.

        Injected pre-call failures may be retried because CloseHandle was not called.
        Genuine native close failures and invalid/stale handles remain owned and
        recorded until an explicit ``recover_native_close`` call. Deferred process
        handles are released only after wait plus exit-code confirmation.

        Returns:
            Count of newly settled handles.
        """
        settled_count = 0
        with self._quarantine_lock:
            # 1. Reconcile unresolved job objects
            remaining_jobs: List[SafeWin32Handle] = []
            for job_owner in self._unresolved_job_handles:
                if job_owner.is_confirmed_closed():
                    settled_count += 1
                    continue
                # Attempt safe close with native API without failure injection
                if job_owner.close(_inject_failure=False):
                    settled_count += 1
                else:
                    remaining_jobs.append(job_owner)
            self._unresolved_job_handles = remaining_jobs

            # 2. Reconcile unresolved general handles
            remaining_handles: List[SafeWin32Handle] = []
            for h_owner in self._unresolved_handles:
                if h_owner.is_confirmed_closed():
                    settled_count += 1
                    self._unresolved_process_termination.pop(id(h_owner), None)
                    continue
                if isinstance(h_owner, SafeProcessHandle) and h_owner.close_blocked_reason:
                    evidence = self._observe_process_termination(h_owner, wait_ms=0)
                    self._last_termination_evidence = evidence
                    self._unresolved_process_termination[id(h_owner)] = evidence
                    if not evidence["termination_confirmed"]:
                        remaining_handles.append(h_owner)
                        continue
                    lease = self._deferred_appcontainer_leases.pop(id(h_owner), None)
                    if lease is not None:
                        lease.release()
                    h_owner.unblock_close()
                if h_owner.close(_inject_failure=False):
                    settled_count += 1
                    self._unresolved_process_termination.pop(id(h_owner), None)
                else:
                    remaining_handles.append(h_owner)
            self._unresolved_handles = remaining_handles

        return settled_count

    def settle_quarantine(self, timeout: float = 0.0) -> int:
        """Reap and safely release quarantined pipe/thread handles whose worker threads have terminated.

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

                thread_finished = (rec.thread is None or not rec.thread.is_alive())
                if thread_finished:
                    pipe_ok = True
                    if rec.handle is not None:
                        rec.handle_val = rec.handle.raw_value()
                        pipe_ok = rec.handle.close()
                        rec.handle_closed = rec.handle.is_confirmed_closed()
                        rec.handle_close_error = rec.handle.close_error
                        if pipe_ok:
                            rec.handle = None  # Release reference only when confirmed closed

                    thread_h_ok = True
                    if rec.thread_handle is not None:
                        rec.thread_handle_val = rec.thread_handle.raw_value()
                        thread_h_ok = rec.thread_handle.close()
                        rec.thread_handle_closed = rec.thread_handle.is_confirmed_closed()
                        rec.thread_handle_close_error = rec.thread_handle.close_error
                        if thread_h_ok:
                            rec.thread_handle = None

                    # A record is ONLY settled when all underlying resources are confirmed closed
                    if pipe_ok and thread_h_ok:
                        rec.settled = True
                        rec.settled_at = time.monotonic()
                        rec.thread = None  # Release Python Thread object to free underlying OS handles
                        settled_count += 1
                    else:
                        rec.settled = False

            # Bounded retention: retain all unsettled records plus up to 64 settled records
            unsettled = [r for r in self._quarantine if not r.settled]
            settled = [r for r in self._quarantine if r.settled]
            if len(settled) > 64:
                settled = settled[-64:]
            self._quarantine = unsettled + settled

            # Clear current writer thread reference if it has completed
            if self._current_writer_thread and not self._current_writer_thread.is_alive():
                self._current_writer_thread = None

        # Also reconcile unresolved handle ledgers
        self.reconcile_unresolved_resources()

        return settled_count

    def get_quarantine_records(self) -> List[Dict[str, Any]]:
        """Return a snapshot list of quarantine records for telemetry and verification."""
        with self._quarantine_lock:
            return [
                {
                    "record_id": r.record_id,
                    "thread_name": r.thread.name if r.thread is not None else "mke-ipc-writer",
                    "thread_alive": r.thread.is_alive() if r.thread is not None else False,
                    "handle_val": r.handle.raw_value() if r.handle is not None else r.handle_val,
                    "thread_handle_val": r.thread_handle.raw_value() if r.thread_handle is not None else r.thread_handle_val,
                    "handle_closed": r.handle.is_confirmed_closed() if r.handle is not None else r.handle_closed,
                    "thread_handle_closed": r.thread_handle.is_confirmed_closed() if r.thread_handle is not None else r.thread_handle_closed,
                    "handle_close_error": r.handle.close_error if r.handle is not None else r.handle_close_error,
                    "thread_handle_close_error": r.thread_handle.close_error if r.thread_handle is not None else r.thread_handle_close_error,
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
        _inject_writer_setup_hang: bool = False,
        _inject_cancel_io_failure: bool = False,
        _inject_writer_join_timeout: bool = False,
        _inject_normal_write_join_timeout: bool = False,
        _inject_late_duplicate_handle: bool = False,
        _inject_close_handle_failure: bool = False,
        _inject_job_close_failure: bool = False,
        _inject_process_close_failure: bool = False,
        _inject_thread_close_failure: bool = False,
        _inject_stdout_close_failure: bool = False,
        _inject_stderr_close_failure: bool = False,
        _inject_terminate_process_failure: bool = False,
        _inject_termination_wait_timeout: bool = False,
        _inject_termination_wait_failure: bool = False,
        _inject_exit_code_failure: bool = False,
        _inject_protected_job_config_cleanup_failure: bool = False,
        _inject_appcontainer_attribute_failure: bool = False,
        _inject_token_mismatch: bool = False,
        _inject_sid_mismatch: bool = False,
        _worker_cmd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute request inside a disposable sandboxed worker and return the response."""
        operation = "UNKNOWN"
        if isinstance(request, dict) and "operation" in request:
            operation = _normalize_operation(request["operation"])

        # Enforce single-request-at-a-time contract atomically
        if not self._request_lock.acquire(blocking=False):
            return _build_controller_error(
                WORKER_RESOURCE_EXHAUSTED,
                "WorkerController does not support concurrent request execution. Single-request contract violated.",
                operation=operation,
            )

        try:
            return self._execute_request_locked(
                request,
                timeout_sec=timeout_sec,
                operation=operation,
                _inject_job_creation_failure=_inject_job_creation_failure,
                _inject_job_config_failure=_inject_job_config_failure,
                _inject_process_creation_failure=_inject_process_creation_failure,
                _inject_assignment_failure=_inject_assignment_failure,
                _inject_resume_failure=_inject_resume_failure,
                _inject_duplicate_handle_failure=_inject_duplicate_handle_failure,
                _inject_writer_setup_hang=_inject_writer_setup_hang,
                _inject_cancel_io_failure=_inject_cancel_io_failure,
                _inject_writer_join_timeout=_inject_writer_join_timeout,
                _inject_normal_write_join_timeout=_inject_normal_write_join_timeout,
                _inject_late_duplicate_handle=_inject_late_duplicate_handle,
                _inject_close_handle_failure=_inject_close_handle_failure,
                _inject_job_close_failure=_inject_job_close_failure,
                _inject_process_close_failure=_inject_process_close_failure,
                _inject_thread_close_failure=_inject_thread_close_failure,
                _inject_stdout_close_failure=_inject_stdout_close_failure,
                _inject_stderr_close_failure=_inject_stderr_close_failure,
                _inject_terminate_process_failure=_inject_terminate_process_failure,
                _inject_termination_wait_timeout=_inject_termination_wait_timeout,
                _inject_termination_wait_failure=_inject_termination_wait_failure,
                _inject_exit_code_failure=_inject_exit_code_failure,
                _inject_protected_job_config_cleanup_failure=_inject_protected_job_config_cleanup_failure,
                _inject_appcontainer_attribute_failure=_inject_appcontainer_attribute_failure,
                _inject_token_mismatch=_inject_token_mismatch,
                _inject_sid_mismatch=_inject_sid_mismatch,
                _worker_cmd=_worker_cmd,
            )
        finally:
            self._request_lock.release()

    def _execute_request_locked(
        self,
        request: Union[str, bytes, Dict[str, Any]],
        timeout_sec: Optional[float] = None,
        operation: str = "UNKNOWN",
        _inject_job_creation_failure: bool = False,
        _inject_job_config_failure: bool = False,
        _inject_process_creation_failure: bool = False,
        _inject_assignment_failure: bool = False,
        _inject_resume_failure: bool = False,
        _inject_duplicate_handle_failure: bool = False,
        _inject_writer_setup_hang: bool = False,
        _inject_cancel_io_failure: bool = False,
        _inject_writer_join_timeout: bool = False,
        _inject_normal_write_join_timeout: bool = False,
        _inject_late_duplicate_handle: bool = False,
        _inject_close_handle_failure: bool = False,
        _inject_job_close_failure: bool = False,
        _inject_process_close_failure: bool = False,
        _inject_thread_close_failure: bool = False,
        _inject_stdout_close_failure: bool = False,
        _inject_stderr_close_failure: bool = False,
        _inject_terminate_process_failure: bool = False,
        _inject_termination_wait_timeout: bool = False,
        _inject_termination_wait_failure: bool = False,
        _inject_exit_code_failure: bool = False,
        _inject_protected_job_config_cleanup_failure: bool = False,
        _inject_appcontainer_attribute_failure: bool = False,
        _inject_token_mismatch: bool = False,
        _inject_sid_mismatch: bool = False,
        _worker_cmd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Internal execution body running under single-request lock."""
        effective_timeout = timeout_sec if timeout_sec is not None else self.timeout_sec

        # Reset per-request cancellation and write telemetry before every request
        self._last_write_info = None
        self._current_writer_thread = None

        # Settle any previously completed quarantined handles and reconcile unresolved resources
        self.settle_quarantine(timeout=0.0)
        self.reconcile_unresolved_resources()

        # Enforce active quarantine capacity ceiling
        active_count = self.get_active_quarantine_count()
        if active_count >= MAX_ACTIVE_QUARANTINE:
            return _build_controller_error(
                WORKER_RESOURCE_EXHAUSTED,
                f"Active quarantined handle capacity exceeded ({active_count}/{MAX_ACTIVE_QUARANTINE}). Refusing new request.",
                details={"active_quarantine_count": active_count, "max_active_quarantine": MAX_ACTIVE_QUARANTINE},
                operation=operation,
            )

        # Enforce unresolved handle ceiling / fail-closed if unresolved handles remain (Task 1 & Task 2)
        unresolved_count = self.get_unresolved_count()
        if unresolved_count > 0:
            return _build_controller_error(
                WORKER_RESOURCE_EXHAUSTED,
                f"WorkerController has {unresolved_count} unresolved native handle(s) from previous request teardown. Refusing new request.",
                details={
                    "safe_cleanup": False,
                    "unresolved_count": unresolved_count,
                    "unresolved_job_count": len(self.get_unresolved_job_handles()),
                    "unresolved_handle_count": len(self.get_unresolved_handles()),
                },
                operation=operation,
            )

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

        # Track handle owners for guaranteed cleanup in finally block
        h_job_owner: Optional[SafeWin32Handle] = None
        h_job: Optional[wintypes.HANDLE] = None
        stdin_read_owner: Optional[SafePipeHandle] = None
        pipe_owner: Optional[SafePipeHandle] = None
        stdout_read_owner: Optional[SafePipeHandle] = None
        stdout_write_owner: Optional[SafePipeHandle] = None
        stderr_read_owner: Optional[SafePipeHandle] = None
        stderr_write_owner: Optional[SafePipeHandle] = None
        proc_owner: Optional[SafeProcessHandle] = None
        thread_owner: Optional[SafeThreadHandle] = None
        pi = PROCESS_INFORMATION()
        attr_buf: Optional[Any] = None
        job_creation_failure: Optional[Dict[str, Any]] = None
        appcontainer_lease: Optional[AppContainerLease] = None
        appcontainer_lease_released = False
        appcontainer_manager = get_appcontainer_manager()
        security_capabilities: Optional[Any] = None

        try:
            try:
                appcontainer_lease = appcontainer_manager.acquire()
                security_capabilities = appcontainer_manager.security_capabilities()
            except Exception as exc:
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to prepare AppContainer worker runtime: {type(exc).__name__}.",
                    operation=operation,
                )

            # 1. Create and configure Windows Job Object
            if _inject_job_creation_failure:
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    "Injected failure during Job Object creation.",
                    operation=operation,
                )

            raw_job, job_err = create_configured_job_object(
                process_memory_limit=self.process_memory_limit,
                job_memory_limit=self.job_memory_limit,
                _protect_from_close_on_failure=_inject_protected_job_config_cleanup_failure,
            )
            failed_cleanup_owner = claim_last_job_object_cleanup_failure()
            if failed_cleanup_owner is not None:
                job_creation_failure = failed_cleanup_owner.as_dict()
                h_job_owner = SafeWin32Handle(failed_cleanup_owner.handle)
                h_job_owner.adopt_native_close_failure(
                    failed_cleanup_owner.cleanup_error,
                    handle_valid_after_failure=failed_cleanup_owner.handle_valid_after_failure,
                )
                h_job = h_job_owner.handle
                self._last_job_owner = h_job_owner
            elif raw_job:
                h_job_owner = SafeWin32Handle(raw_job, _inject_close_failure=_inject_job_close_failure)
                h_job = h_job_owner.handle
                self._last_job_owner = h_job_owner
            else:
                h_job_owner = None
                h_job = None
                self._last_job_owner = None

            if not raw_job or _inject_job_config_failure:
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to create or configure Job Object (win32 error {job_err}).",
                    details={
                        "win32_error": job_err,
                        "job_creation_failure": job_creation_failure,
                    },
                    operation=operation,
                )

            # 2. Create anonymous pipes with explicit handle inheritance
            sa = SECURITY_ATTRIBUTES()
            sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
            sa.bInheritHandle = True

            raw_stdin_read = wintypes.HANDLE()
            raw_stdin_write = wintypes.HANDLE()
            if not kernel32.CreatePipe(ctypes.byref(raw_stdin_read), ctypes.byref(raw_stdin_write), ctypes.byref(sa), self._stdin_pipe_buffer_size):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to create stdin pipe (win32 error {err}).",
                    operation=operation,
                )
            stdin_read_owner = SafePipeHandle(raw_stdin_read)
            pipe_owner = SafePipeHandle(raw_stdin_write, _inject_close_failure=_inject_close_handle_failure)

            raw_stdout_read = wintypes.HANDLE()
            raw_stdout_write = wintypes.HANDLE()
            if not kernel32.CreatePipe(ctypes.byref(raw_stdout_read), ctypes.byref(raw_stdout_write), ctypes.byref(sa), 0):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to create stdout pipe (win32 error {err}).",
                    operation=operation,
                )
            stdout_read_owner = SafePipeHandle(raw_stdout_read, _inject_close_failure=_inject_stdout_close_failure)
            stdout_write_owner = SafePipeHandle(raw_stdout_write)

            raw_stderr_read = wintypes.HANDLE()
            raw_stderr_write = wintypes.HANDLE()
            if not kernel32.CreatePipe(ctypes.byref(raw_stderr_read), ctypes.byref(raw_stderr_write), ctypes.byref(sa), 0):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to create stderr pipe (win32 error {err}).",
                    operation=operation,
                )
            stderr_read_owner = SafePipeHandle(raw_stderr_read, _inject_close_failure=_inject_stderr_close_failure)
            stderr_write_owner = SafePipeHandle(raw_stderr_write)

            # Ensure controller pipe ends are strictly NOT inheritable
            if not kernel32.SetHandleInformation(pipe_owner.handle, HANDLE_FLAG_INHERIT, 0):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to set handle information on stdin pipe (win32 error {err}).",
                    operation=operation,
                )

            if not kernel32.SetHandleInformation(stdout_read_owner.handle, HANDLE_FLAG_INHERIT, 0):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to set handle information on stdout pipe (win32 error {err}).",
                    operation=operation,
                )

            if not kernel32.SetHandleInformation(stderr_read_owner.handle, HANDLE_FLAG_INHERIT, 0):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to set handle information on stderr pipe (win32 error {err}).",
                    operation=operation,
                )

            # 3. Configure the strict handle allowlist and AppContainer identity.
            attr_size = ctypes.c_size_t(0)
            kernel32.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(attr_size))
            attr_buf = ctypes.create_string_buffer(attr_size.value)
            if not kernel32.InitializeProcThreadAttributeList(attr_buf, 2, 0, ctypes.byref(attr_size)):
                err = ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to initialize thread attribute list (win32 error {err}).",
                    operation=operation,
                )

            inherited_handles = (wintypes.HANDLE * 3)(stdin_read_owner.handle, stdout_write_owner.handle, stderr_write_owner.handle)
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

            if _inject_appcontainer_attribute_failure or not kernel32.UpdateProcThreadAttribute(
                attr_buf, 0, PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
                ctypes.byref(security_capabilities), ctypes.sizeof(security_capabilities), None, None
            ):
                err = 5 if _inject_appcontainer_attribute_failure else ctypes.get_last_error()
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"Failed to update AppContainer security capabilities (win32 error {err}).",
                    details={"win32_error": err},
                    operation=operation,
                )

            # 4. Prepare STARTUPINFOEXW and CreateProcessW with CREATE_SUSPENDED
            siex = STARTUPINFOEXW()
            siex.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
            siex.StartupInfo.dwFlags = STARTF_USESTDHANDLES
            siex.StartupInfo.hStdInput = stdin_read_owner.handle
            siex.StartupInfo.hStdOutput = stdout_write_owner.handle
            siex.StartupInfo.hStdError = stderr_write_owner.handle
            siex.lpAttributeList = ctypes.cast(attr_buf, ctypes.c_void_p)

            custom_cmd = _worker_cmd if _worker_cmd is not None else self._custom_worker_cmd
            try:
                cmd = (
                    appcontainer_manager.rewrite_python_command(custom_cmd)
                    if custom_cmd is not None
                    else appcontainer_manager.default_command()
                )
            except ValueError as exc:
                return _build_controller_error(WORKER_STARTUP_FAILURE, str(exc), operation=operation)
            environment = appcontainer_manager.environment_block()
            creation_flags = EXTENDED_STARTUPINFO_PRESENT | CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT

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
                ctypes.cast(environment, ctypes.c_void_p),
                str(appcontainer_manager.stage_root),
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

            # Wrap process and primary thread immediately upon creation
            proc_owner = SafeProcessHandle(pi.hProcess, _inject_close_failure=_inject_process_close_failure)
            self._last_process_owner = proc_owner
            thread_owner = SafeThreadHandle(pi.hThread, _inject_close_failure=_inject_thread_close_failure)

            # Close worker ends of pipes in controller immediately after creation
            stdin_read_owner.close()
            stdout_write_owner.close()
            stderr_write_owner.close()

            # 5. Assign process to Job Object and verify assignment BEFORE resuming thread
            if _inject_assignment_failure:
                # Terminate suspended process immediately and fail closed
                kernel32.TerminateProcess(proc_owner.handle, 1)
                return _build_controller_error(
                    WORKER_ASSIGNMENT_FAILURE,
                    "Injected failure during Job Object assignment.",
                    operation=operation,
                )

            assign_ok, assign_err = assign_and_verify_process_in_job(h_job, proc_owner.handle)
            if not assign_ok:
                # Terminate suspended process immediately and fail closed
                kernel32.TerminateProcess(proc_owner.handle, 1)
                return _build_controller_error(
                    WORKER_ASSIGNMENT_FAILURE,
                    f"Failed to assign or verify worker process in Job Object (win32 error {assign_err}).",
                    details={"win32_error": assign_err},
                    operation=operation,
                )

            # 6. Verify the suspended child's native token before any code runs.
            token_evidence = verify_appcontainer_process_token(
                proc_owner.handle,
                appcontainer_manager.sid,
                inject_token_mismatch=_inject_token_mismatch,
                inject_sid_mismatch=_inject_sid_mismatch,
            )
            token_evidence.update({
                "profile_name": appcontainer_manager.profile_name,
                "expected_sid": appcontainer_manager.sid_string,
                "job_assignment_verified": True,
                "process_was_resumed": False,
            })
            self._last_appcontainer_evidence = token_evidence
            if not token_evidence.get("accepted"):
                kernel32.TerminateProcess(proc_owner.handle, 1)
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    "Suspended worker failed AppContainer token verification.",
                    details={"appcontainer_verification": token_evidence},
                    operation=operation,
                )

            # 7. Resume only after Job assignment and token verification.
            if _inject_resume_failure:
                kernel32.TerminateProcess(proc_owner.handle, 1)
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    "Injected failure during thread resumption.",
                    operation=operation,
                )

            suspend_count = kernel32.ResumeThread(thread_owner.handle)
            if suspend_count == 0xFFFFFFFF:
                err = ctypes.get_last_error()
                kernel32.TerminateProcess(proc_owner.handle, 1)
                return _build_controller_error(
                    WORKER_STARTUP_FAILURE,
                    f"ResumeThread failed for worker (win32 error {err}).",
                    operation=operation,
                )
            token_evidence["process_was_resumed"] = True
            self._last_appcontainer_evidence = token_evidence

            # 8. Establish full-lifecycle deadline before worker IPC
            deadline = time.monotonic() + effective_timeout

            # Write length-prefixed request to stdin pipe within full-lifecycle deadline
            header = struct.pack(">I", len(raw_payload))
            msg = header + raw_payload

            write_res = self._write_exact_bytes_with_timeout(
                pipe_owner,
                msg,
                deadline,
                proc_owner.handle,
                h_job,
                operation=operation,
                _inject_duplicate_handle_failure=_inject_duplicate_handle_failure,
                _inject_cancel_io_failure=_inject_cancel_io_failure,
                _inject_writer_join_timeout=_inject_writer_join_timeout,
                _inject_normal_write_join_timeout=_inject_normal_write_join_timeout,
                _inject_writer_setup_hang=_inject_writer_setup_hang,
                _inject_late_duplicate_handle=_inject_late_duplicate_handle,
                _inject_close_handle_failure=_inject_close_handle_failure,
            )
            if isinstance(write_res, dict):
                return write_res

            # Close stdin write handle to signal EOF to worker
            if pipe_owner is not None and not pipe_owner.is_quarantined():
                pipe_owner.close(_inject_failure=_inject_close_handle_failure)
                if not pipe_owner.is_confirmed_closed():
                    pipe_owner.quarantine()
                    with self._quarantine_lock:
                        self._quarantine_counter += 1
                        rec = QuarantineRecord(
                            record_id=self._quarantine_counter,
                            thread=None,
                            handle=pipe_owner,
                            thread_handle=None,
                            handle_val=pipe_owner.raw_value(),
                            thread_handle_val=0,
                            handle_closed=False,
                            thread_handle_closed=True,
                            handle_close_error=pipe_owner.close_error,
                            thread_handle_close_error=0,
                            created_at=time.monotonic(),
                            settled=False,
                            settled_at=None,
                        )
                        self._quarantine.append(rec)
                    return _build_controller_error(
                        WORKER_RESOURCE_EXHAUSTED,
                        f"Failed to close stdin pipe during request execution (win32 error {pipe_owner.close_error}).",
                        details={
                            "safe_cleanup": False,
                            "handle_quarantined": True,
                            "pipe_close_error": pipe_owner.close_error,
                            "handle_val": pipe_owner.raw_value(),
                        },
                        operation=operation,
                    )

            # 8. Bounded read from stdout pipe with same effective deadline
            response_header = self._read_exact_bytes(
                stdout_read_owner.handle, proc_owner.handle, IPC_HEADER_SIZE, deadline, h_job, h_stderr=stderr_read_owner.handle, operation=operation
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
                stdout_read_owner.handle, proc_owner.handle, resp_length, deadline, h_job, h_stderr=stderr_read_owner.handle, operation=operation
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
                if pipe_owner is not None and not pipe_owner.is_confirmed_closed():
                    return _build_controller_error(
                        WORKER_RESOURCE_EXHAUSTED,
                        f"Failed to close stdin pipe handle during request completion (win32 error {pipe_owner.close_error}).",
                        details={
                            "safe_cleanup": False,
                            "handle_quarantined": True,
                            "pipe_close_error": pipe_owner.close_error,
                            "handle_val": pipe_owner.raw_value(),
                        },
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
            cleanup_failures: Dict[str, Any] = {}
            cleanup_close_evidence: Dict[str, Any] = {}
            process_termination_deferred = False

            # Terminate and close the worker only after positive native evidence.
            if proc_owner is not None and proc_owner.raw_value() > 0:
                termination_evidence = self._terminate_and_confirm_process(
                    proc_owner,
                    _inject_terminate_process_failure=_inject_terminate_process_failure,
                    _inject_termination_wait_timeout=_inject_termination_wait_timeout,
                    _inject_termination_wait_failure=_inject_termination_wait_failure,
                    _inject_exit_code_failure=_inject_exit_code_failure,
                )
                if termination_evidence["termination_confirmed"]:
                    if appcontainer_lease is not None and not appcontainer_lease_released:
                        appcontainer_lease.release()
                        appcontainer_lease_released = True
                    ok = proc_owner.close(_inject_failure=_inject_process_close_failure)
                    if not ok:
                        cleanup_failures["process_handle"] = proc_owner.close_error
                        cleanup_close_evidence["process_handle"] = proc_owner.close_evidence
                        with self._quarantine_lock:
                            if proc_owner not in self._unresolved_handles:
                                self._unresolved_handles.append(proc_owner)
                else:
                    process_termination_deferred = True
                    proc_owner.block_close("PROCESS_TERMINATION_UNCONFIRMED")
                    cleanup_failures["process_termination"] = termination_evidence
                    with self._quarantine_lock:
                        if proc_owner not in self._unresolved_handles:
                            self._unresolved_handles.append(proc_owner)
                        self._unresolved_process_termination[id(proc_owner)] = termination_evidence
                        if appcontainer_lease is not None and not appcontainer_lease_released:
                            self._deferred_appcontainer_leases[id(proc_owner)] = appcontainer_lease

            # Close worker primary thread handle
            if thread_owner is not None and thread_owner.raw_value() > 0:
                ok = thread_owner.close(_inject_failure=_inject_thread_close_failure)
                if not ok:
                    cleanup_failures["thread_handle"] = thread_owner.close_error
                    with self._quarantine_lock:
                        if thread_owner not in self._unresolved_handles:
                            self._unresolved_handles.append(thread_owner)

            # Close all pipe handles through their safe wrappers
            for name, owner, inj in [
                ("stdin_read", stdin_read_owner, False),
                ("stdout_read", stdout_read_owner, _inject_stdout_close_failure),
                ("stdout_write", stdout_write_owner, False),
                ("stderr_read", stderr_read_owner, _inject_stderr_close_failure),
                ("stderr_write", stderr_write_owner, False),
            ]:
                if owner is not None and owner.raw_value() > 0 and not owner.is_confirmed_closed():
                    ok = owner.close(_inject_failure=inj)
                    if not ok:
                        cleanup_failures[name] = owner.close_error
                        with self._quarantine_lock:
                            if owner not in self._unresolved_handles:
                                self._unresolved_handles.append(owner)

            # Handle ownership invariant: close pipe_owner ONLY IF not quarantined
            if pipe_owner is not None and not pipe_owner.is_quarantined() and not pipe_owner.is_confirmed_closed():
                writer_alive = (self._current_writer_thread is not None and self._current_writer_thread.is_alive())
                if writer_alive:
                    pipe_owner.quarantine()
                    cleanup_failures["pipe_owner"] = "STILL_WRITING"
                    with self._quarantine_lock:
                        self._quarantine_counter += 1
                        rec = QuarantineRecord(
                            record_id=self._quarantine_counter,
                            thread=self._current_writer_thread,
                            handle=pipe_owner,
                            thread_handle=None,
                            handle_val=pipe_owner.raw_value(),
                            thread_handle_val=0,
                            handle_closed=False,
                            thread_handle_closed=True,
                            handle_close_error=0,
                            thread_handle_close_error=0,
                            created_at=time.monotonic(),
                            settled=False,
                            settled_at=None,
                        )
                        self._quarantine.append(rec)
                else:
                    ok = pipe_owner.close(_inject_failure=_inject_close_handle_failure)
                    if not ok:
                        pipe_owner.quarantine()
                        cleanup_failures["pipe_owner"] = pipe_owner.close_error
                        with self._quarantine_lock:
                            self._quarantine_counter += 1
                            rec = QuarantineRecord(
                                record_id=self._quarantine_counter,
                                thread=None,
                                handle=pipe_owner,
                                thread_handle=None,
                                handle_val=pipe_owner.raw_value(),
                                thread_handle_val=0,
                                handle_closed=False,
                                thread_handle_closed=True,
                                handle_close_error=pipe_owner.close_error,
                                thread_handle_close_error=0,
                                created_at=time.monotonic(),
                                settled=False,
                                settled_at=None,
                            )
                            self._quarantine.append(rec)

            if attr_buf:
                try:
                    kernel32.DeleteProcThreadAttributeList(attr_buf)
                except Exception as ex:
                    cleanup_failures["attr_list"] = str(ex)

            # Closing Job Object handle triggers KILL_ON_JOB_CLOSE for any remaining child processes
            if h_job_owner is not None and not h_job_owner.is_confirmed_closed():
                h_job_owner.close(_inject_failure=_inject_job_close_failure)
                if not h_job_owner.is_confirmed_closed():
                    cleanup_failures["job_object"] = h_job_owner.close_error
                    cleanup_close_evidence["job_object"] = h_job_owner.close_evidence
                    with self._quarantine_lock:
                        if h_job_owner not in self._unresolved_job_handles:
                            self._unresolved_job_handles.append(h_job_owner)

            # A successfully closed KILL_ON_JOB_CLOSE Job Object supplies a second
            # containment-backed opportunity to confirm termination. If the Job
            # Object itself remains unresolved, retain both owners and do not guess.
            if (
                process_termination_deferred
                and proc_owner is not None
                and h_job_owner is not None
                and h_job_owner.is_confirmed_closed()
            ):
                post_job_evidence = self._observe_process_termination(proc_owner, wait_ms=1000)
                self._last_termination_evidence = post_job_evidence
                with self._quarantine_lock:
                    self._unresolved_process_termination[id(proc_owner)] = post_job_evidence
                if post_job_evidence["termination_confirmed"]:
                    lease = self._deferred_appcontainer_leases.pop(id(proc_owner), None)
                    if lease is not None:
                        lease.release()
                        appcontainer_lease_released = True
                    proc_owner.unblock_close()
                    cleanup_failures.pop("process_termination", None)
                    ok = proc_owner.close(_inject_failure=_inject_process_close_failure)
                    if ok:
                        with self._quarantine_lock:
                            if proc_owner in self._unresolved_handles:
                                self._unresolved_handles.remove(proc_owner)
                            self._unresolved_process_termination.pop(id(proc_owner), None)
                    else:
                        cleanup_failures["process_handle"] = proc_owner.close_error
                        cleanup_close_evidence["process_handle"] = proc_owner.close_evidence

            # Preparation may have acquired a lease before CreateProcess failed.
            if proc_owner is None and appcontainer_lease is not None and not appcontainer_lease_released:
                appcontainer_lease.release()
                appcontainer_lease_released = True

            if cleanup_failures:
                # Fail closed: never return success or unqualified result if any handle cleanup failed
                return _build_controller_error(
                    WORKER_RESOURCE_EXHAUSTED,
                    f"Failed to safely release worker resources during teardown: {list(cleanup_failures.keys())}.",
                    details={
                        "safe_cleanup": False,
                        "handle_quarantined": True if (pipe_owner and pipe_owner.is_quarantined()) else False,
                        "cleanup_failures": cleanup_failures,
                        "cleanup_close_evidence": cleanup_close_evidence,
                        "job_close_error": cleanup_failures.get("job_object"),
                        "job_creation_failure": job_creation_failure,
                        "process_termination": self._last_termination_evidence,
                        "unresolved_count": self.get_unresolved_count(),
                    },
                    operation=operation,
                )

    def _handle_worker_timeout(
        self,
        h_process: wintypes.HANDLE,
        h_job: Optional[wintypes.HANDLE],
        timeout_phase: str = "UNKNOWN",
        operation: str = "UNKNOWN",
        safe_cleanup: bool = True,
    ) -> Dict[str, Any]:
        """Build a timeout error; centralized teardown establishes termination evidence."""
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
        _inject_writer_setup_hang: bool = False,
        _inject_late_duplicate_handle: bool = False,
        _inject_close_handle_failure: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Write exact bytes to pipe within full-lifecycle deadline, handling partial writes and blocking worker."""
        write_error = [None]
        bytes_written_total = [0]
        write_done = threading.Event()
        setup_done = threading.Event()
        barrier_writer_ready = threading.Event()
        barrier_controller_proceed = threading.Event()
        write_in_progress = threading.Event()
        abort_requested = threading.Event()
        dup_invoked = [False]
        dup_success = [False]
        dup_error = [0]
        dup_raw_val = [0]
        write_status = ["NOT_STARTED"]
        thread_handle_owner = SafeThreadHandle(_inject_close_failure=_inject_close_handle_failure)

        def _writer():
            try:
                if _inject_writer_setup_hang:
                    time.sleep(0.08)

                if _inject_late_duplicate_handle:
                    # Step 1: Worker reaches barrier BEFORE DuplicateHandle
                    barrier_writer_ready.set()
                    # Wait for controller to signal abort and permit proceeding
                    barrier_controller_proceed.wait(timeout=2.0)

                dup_invoked[0] = True
                if _inject_duplicate_handle_failure:
                    dup_ok = False
                    ctypes.set_last_error(5)  # ERROR_ACCESS_DENIED
                else:
                    cur_proc = kernel32.GetCurrentProcess()
                    cur_th = kernel32.GetCurrentThread()
                    raw_th = wintypes.HANDLE()
                    dup_ok = bool(kernel32.DuplicateHandle(
                        cur_proc,
                        cur_th,
                        cur_proc,
                        ctypes.byref(raw_th),
                        0,
                        False,
                        DUPLICATE_SAME_ACCESS,
                    ))
                    if dup_ok:
                        dup_raw_val[0] = int(raw_th.value) if raw_th.value else 0
                        thread_handle_owner.set_handle(raw_th)

                if not dup_ok:
                    dup_error[0] = ctypes.get_last_error()
                    dup_success[0] = False
                    write_status[0] = "DUPLICATE_HANDLE_FAILED"
                    setup_done.set()
                    if self._last_write_info is not None:
                        self._last_write_info["duplicate_handle_invoked"] = True
                        self._last_write_info["duplicate_handle_raw_val"] = dup_raw_val[0]
                        self._last_write_info["write_file_status"] = write_status[0]
                    return

                # DuplicateHandle completed successfully
                dup_success[0] = True
                write_status[0] = "ENTERED"
                setup_done.set()

                # Worker detects abort before WriteFile
                if abort_requested.is_set():
                    write_status[0] = "ABORTED_BEFORE_WRITE"
                    if self._last_write_info is not None:
                        self._last_write_info["duplicate_handle_invoked"] = True
                        self._last_write_info["duplicate_handle_raw_val"] = dup_raw_val[0]
                        self._last_write_info["write_file_status"] = write_status[0]
                    return

                total = 0
                while total < len(data):
                    if abort_requested.is_set():
                        write_status[0] = "ABORTED_DURING_WRITE"
                        return
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
                # Ensure thread handle is closed upon thread termination
                thread_handle_owner.close(_inject_failure=_inject_close_handle_failure)
                # Deferred release: if quarantined, safely close handle upon thread termination
                if pipe_owner.is_quarantined():
                    pipe_owner.close(_inject_failure=_inject_close_handle_failure)

        writer_thread = threading.Thread(target=_writer, daemon=True, name="mke-ipc-writer")
        self._current_writer_thread = writer_thread
        writer_thread.start()

        if _inject_late_duplicate_handle:
            # Step 1: Controller waits for writer to reach barrier BEFORE DuplicateHandle
            barrier_writer_ready.wait(timeout=1.0)

            # Step 2: Abort precedes duplication
            abort_requested.set()

            # Step 3: Register quarantine in ledger BEFORE releasing writer
            pipe_owner.quarantine()
            quarantined = True
            with self._quarantine_lock:
                self._quarantine_counter += 1
                rec = QuarantineRecord(
                    record_id=self._quarantine_counter,
                    thread=writer_thread,
                    handle=pipe_owner,
                    thread_handle=thread_handle_owner,
                    handle_val=pipe_owner.raw_value(),
                    thread_handle_val=thread_handle_owner.raw_value(),
                    handle_closed=pipe_owner.is_confirmed_closed(),
                    thread_handle_closed=thread_handle_owner.is_confirmed_closed(),
                    handle_close_error=pipe_owner.close_error,
                    thread_handle_close_error=thread_handle_owner.close_error,
                    created_at=time.monotonic(),
                    settled=False,
                    settled_at=None,
                )
                self._quarantine.append(rec)

            self._last_write_info = {
                "duplicate_handle_invoked": False,
                "duplicate_handle_raw_val": 0,
                "duplicate_handle_success": False,
                "duplicate_handle_error": 0,
                "write_entered": False,
                "write_blocked_at_deadline": False,
                "cancellation_requested": False,
                "cancel_synchronous_io_called": False,
                "cancel_synchronous_io_success": False,
                "cancel_synchronous_io_return": None,
                "cancel_synchronous_io_last_error": None,
                "writer_thread_alive_before_cancel": False,
                "writer_thread_alive_after_join": True,
                "write_file_status": "PAUSED_BEFORE_DUPLICATE",
                "writer_exited": False,
                "all_handles_safely_released": False,
                "handle_quarantined": True,
                "bytes_written": 0,
                "total_bytes": len(data),
            }

            # Step 4: Release paused writer thread to proceed with DuplicateHandle AFTER quarantine registration
            barrier_controller_proceed.set()

            return _build_controller_error(
                WORKER_STARTUP_FAILURE,
                "Writer thread setup timed out before DuplicateHandle completion.",
                details={"setup_timed_out": True, "writer_exited": False, "handle_quarantined": True},
                operation=operation,
            )

        setup_ok = setup_done.wait(timeout=0.02 if _inject_writer_setup_hang else 1.0)

        # Check DuplicateHandle status and setup completion before proceeding
        if not setup_ok or not dup_success[0] or _inject_late_duplicate_handle:
            abort_requested.set()
            writer_thread.join(timeout=0.001 if (_inject_writer_setup_hang or _inject_late_duplicate_handle) else 1.0)
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
                        thread_handle=thread_handle_owner,
                        handle_val=pipe_owner.raw_value(),
                        thread_handle_val=thread_handle_owner.raw_value(),
                        handle_closed=pipe_owner.is_confirmed_closed(),
                        thread_handle_closed=thread_handle_owner.is_confirmed_closed(),
                        handle_close_error=pipe_owner.close_error,
                        thread_handle_close_error=thread_handle_owner.close_error,
                        created_at=time.monotonic(),
                        settled=False,
                        settled_at=None,
                    )
                    self._quarantine.append(rec)
            else:
                thread_handle_owner.close(_inject_failure=_inject_close_handle_failure)
                if not thread_handle_owner.is_confirmed_closed():
                    quarantined = True
                    with self._quarantine_lock:
                        self._quarantine_counter += 1
                        rec = QuarantineRecord(
                            record_id=self._quarantine_counter,
                            thread=None,
                            handle=None,
                            thread_handle=thread_handle_owner,
                            handle_val=None,
                            thread_handle_val=thread_handle_owner.raw_value(),
                            handle_closed=True,
                            thread_handle_closed=False,
                            handle_close_error=0,
                            thread_handle_close_error=thread_handle_owner.close_error,
                            created_at=time.monotonic(),
                            settled=False,
                            settled_at=None,
                        )
                        self._quarantine.append(rec)

            self._last_write_info = {
                "duplicate_handle_invoked": dup_invoked[0],
                "duplicate_handle_raw_val": dup_raw_val[0],
                "duplicate_handle_success": dup_success[0],
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
                "all_handles_safely_released": writer_exited and thread_handle_owner.is_confirmed_closed(),
                "handle_quarantined": quarantined,
                "bytes_written": 0,
                "total_bytes": len(data),
            }
            return _build_controller_error(
                WORKER_STARTUP_FAILURE,
                f"Failed to duplicate writer thread handle for safe cancellation (win32 error {dup_error[0]})." if not dup_success[0] and setup_ok else "Writer thread setup timed out.",
                details={"win32_error": dup_error[0], "setup_timed_out": not setup_ok, "writer_exited": writer_exited, "handle_quarantined": quarantined},
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
            abort_requested.set()
            write_blocked = write_in_progress.is_set()
            writer_alive_before = writer_thread.is_alive()
            cancel_called = True
            cancel_ret = False
            cancel_err = 0

            if _inject_cancel_io_failure:
                cancel_ret = False
                cancel_err = 1168  # ERROR_NOT_FOUND
            elif thread_handle_owner.handle and thread_handle_owner.handle.value:
                cancel_ret = bool(kernel32.CancelSynchronousIo(thread_handle_owner.handle))
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
                        thread_handle=thread_handle_owner,
                        handle_val=pipe_owner.raw_value(),
                        thread_handle_val=thread_handle_owner.raw_value(),
                        handle_closed=pipe_owner.is_confirmed_closed(),
                        thread_handle_closed=thread_handle_owner.is_confirmed_closed(),
                        handle_close_error=pipe_owner.close_error,
                        thread_handle_close_error=thread_handle_owner.close_error,
                        created_at=time.monotonic(),
                        settled=False,
                        settled_at=None,
                    )
                    self._quarantine.append(rec)
            else:
                thread_handle_owner.close(_inject_failure=_inject_close_handle_failure)
                if not thread_handle_owner.is_confirmed_closed():
                    quarantined = True
                    with self._quarantine_lock:
                        self._quarantine_counter += 1
                        rec = QuarantineRecord(
                            record_id=self._quarantine_counter,
                            thread=None,
                            handle=None,
                            thread_handle=thread_handle_owner,
                            handle_val=None,
                            thread_handle_val=thread_handle_owner.raw_value(),
                            handle_closed=True,
                            thread_handle_closed=False,
                            handle_close_error=0,
                            thread_handle_close_error=thread_handle_owner.close_error,
                            created_at=time.monotonic(),
                            settled=False,
                            settled_at=None,
                        )
                        self._quarantine.append(rec)

            safe_cleanup = writer_exited and thread_handle_owner.is_confirmed_closed()

            self._last_write_info = {
                "duplicate_handle_invoked": dup_invoked[0],
                "duplicate_handle_raw_val": dup_raw_val[0],
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
                "all_handles_safely_released": safe_cleanup,
                "handle_quarantined": quarantined,
                "bytes_written": bytes_written_total[0],
                "total_bytes": len(data),
            }

            if not safe_cleanup:
                # Do NOT claim safe cleanup if writer thread is still running or handle close failed
                return _build_controller_error(
                    WORKER_TIMEOUT,
                    "Worker execution timed out during WRITE phase and writer resources failed to clean up safely.",
                    details={
                        "timeout_phase": "WRITE",
                        "safe_cleanup": False,
                        "writer_exited": writer_exited,
                        "handle_quarantined": True,
                        "cancel_synchronous_io_return": cancel_ret,
                        "cancel_synchronous_io_last_error": cancel_err,
                        "thread_handle_close_error": thread_handle_owner.close_error,
                        "timeout_sec": self.timeout_sec,
                    },
                    operation=operation,
                )

            return self._handle_worker_timeout(
                h_process, h_job, timeout_phase="WRITE", operation=operation, safe_cleanup=True
            )

        if abnormal_exit_code is not None:
            abort_requested.set()
            cancel_called = False
            cancel_ret = None
            cancel_err = None
            if thread_handle_owner.handle and thread_handle_owner.handle.value:
                cancel_called = True
                cancel_ret = bool(kernel32.CancelSynchronousIo(thread_handle_owner.handle))
                cancel_err = 0 if cancel_ret else ctypes.get_last_error()

            writer_thread.join(timeout=2.0)
            writer_exited = not writer_thread.is_alive()
            if writer_exited:
                thread_handle_owner.close(_inject_failure=_inject_close_handle_failure)
                if not thread_handle_owner.is_confirmed_closed():
                    quarantined = True
                    with self._quarantine_lock:
                        self._quarantine_counter += 1
                        rec = QuarantineRecord(
                            record_id=self._quarantine_counter,
                            thread=None,
                            handle=None,
                            thread_handle=thread_handle_owner,
                            handle_val=None,
                            thread_handle_val=thread_handle_owner.raw_value(),
                            handle_closed=True,
                            thread_handle_closed=False,
                            handle_close_error=0,
                            thread_handle_close_error=thread_handle_owner.close_error,
                            created_at=time.monotonic(),
                            settled=False,
                            settled_at=None,
                        )
                        self._quarantine.append(rec)

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
                        thread_handle=thread_handle_owner,
                        handle_val=pipe_owner.raw_value(),
                        thread_handle_val=thread_handle_owner.raw_value(),
                        handle_closed=pipe_owner.is_confirmed_closed(),
                        thread_handle_closed=thread_handle_owner.is_confirmed_closed(),
                        handle_close_error=pipe_owner.close_error,
                        thread_handle_close_error=thread_handle_owner.close_error,
                        created_at=time.monotonic(),
                        settled=False,
                        settled_at=None,
                    )
                    self._quarantine.append(rec)

            self._last_write_info = {
                "duplicate_handle_invoked": dup_invoked[0],
                "duplicate_handle_raw_val": dup_raw_val[0],
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
                "all_handles_safely_released": writer_exited and thread_handle_owner.is_confirmed_closed(),
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
        if writer_exited:
            thread_handle_owner.close(_inject_failure=_inject_close_handle_failure)
            if not thread_handle_owner.is_confirmed_closed():
                with self._quarantine_lock:
                    self._quarantine_counter += 1
                    rec = QuarantineRecord(
                        record_id=self._quarantine_counter,
                        thread=None,
                        handle=None,
                        thread_handle=thread_handle_owner,
                        handle_val=None,
                        thread_handle_val=thread_handle_owner.raw_value(),
                        handle_closed=True,
                        thread_handle_closed=False,
                        handle_close_error=0,
                        thread_handle_close_error=thread_handle_owner.close_error,
                        created_at=time.monotonic(),
                        settled=False,
                        settled_at=None,
                    )
                    self._quarantine.append(rec)

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
                    thread_handle=thread_handle_owner,
                    handle_val=pipe_owner.raw_value(),
                    thread_handle_val=thread_handle_owner.raw_value(),
                    handle_closed=pipe_owner.is_confirmed_closed(),
                    thread_handle_closed=thread_handle_owner.is_confirmed_closed(),
                    handle_close_error=pipe_owner.close_error,
                    thread_handle_close_error=thread_handle_owner.close_error,
                    created_at=time.monotonic(),
                    settled=False,
                    settled_at=None,
                )
                self._quarantine.append(rec)

        safe_cleanup = writer_exited and thread_handle_owner.is_confirmed_closed()

        self._last_write_info = {
            "duplicate_handle_invoked": dup_invoked[0],
            "duplicate_handle_raw_val": dup_raw_val[0],
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
            "all_handles_safely_released": safe_cleanup,
            "handle_quarantined": quarantined or (not thread_handle_owner.is_confirmed_closed()),
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

        if not thread_handle_owner.is_confirmed_closed():
            return _build_controller_error(
                WORKER_RESOURCE_EXHAUSTED,
                f"Failed to close duplicated writer thread handle during cleanup (win32 error {thread_handle_owner.close_error}).",
                details={
                    "safe_cleanup": False,
                    "handle_quarantined": True,
                    "thread_handle_close_error": thread_handle_owner.close_error,
                    "thread_handle_val": thread_handle_owner.raw_value(),
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
