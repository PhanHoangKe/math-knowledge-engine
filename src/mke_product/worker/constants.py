"""Constants, resource limits, and taxonomy codes for S4-B1 worker process containment."""

# ---------------------------------------------------------------------------
# S4-B1 Resource Limits
# ---------------------------------------------------------------------------
PROCESS_MEMORY_LIMIT_BYTES: int = 256 * 1024 * 1024  # 256 MiB per process
JOB_MEMORY_LIMIT_BYTES: int = 512 * 1024 * 1024      # 512 MiB job-wide

# ---------------------------------------------------------------------------
# S4-B1 Result Taxonomy
# ---------------------------------------------------------------------------
WORKER_STARTUP_FAILURE: str = "WORKER_STARTUP_FAILURE"
WORKER_ASSIGNMENT_FAILURE: str = "WORKER_ASSIGNMENT_FAILURE"
WORKER_TIMEOUT: str = "WORKER_TIMEOUT"
WORKER_RESOURCE_EXHAUSTED: str = "WORKER_RESOURCE_EXHAUSTED"
WORKER_EXIT_FAILURE: str = "WORKER_EXIT_FAILURE"
WORKER_PROTOCOL_FAILURE: str = "WORKER_PROTOCOL_FAILURE"

ALL_WORKER_STATUSES = {
    WORKER_STARTUP_FAILURE,
    WORKER_ASSIGNMENT_FAILURE,
    WORKER_TIMEOUT,
    WORKER_RESOURCE_EXHAUSTED,
    WORKER_EXIT_FAILURE,
    WORKER_PROTOCOL_FAILURE,
}

# ---------------------------------------------------------------------------
# IPC Framing & Transport Limits
# ---------------------------------------------------------------------------
IPC_HEADER_SIZE: int = 4  # 4 bytes unsigned 32-bit big-endian length prefix
IPC_MAX_REQUEST_BYTES: int = 4096       # S4-A MAX_PAYLOAD_BYTES
IPC_MAX_RESPONSE_BYTES: int = 16384     # S4-A MAX_RESPONSE_BYTES
DEFAULT_WORKER_TIMEOUT_SEC: float = 10.0

# ---------------------------------------------------------------------------
# Win32 Kernel Constants
# ---------------------------------------------------------------------------
CREATE_SUSPENDED: int = 0x00000004
EXTENDED_STARTUPINFO_PRESENT: int = 0x00080000
STARTF_USESTDHANDLES: int = 0x00000100
PROC_THREAD_ATTRIBUTE_HANDLE_LIST: int = 0x00020002
HANDLE_FLAG_INHERIT: int = 0x00000001

JOB_OBJECT_LIMIT_PROCESS_MEMORY: int = 0x00000100
JOB_OBJECT_LIMIT_JOB_MEMORY: int = 0x00000200
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: int = 0x00002000
JOB_OBJECT_LIMIT_BREAKAWAY_OK: int = 0x00000800
JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK: int = 0x00001000
CREATE_BREAKAWAY_FROM_JOB: int = 0x01000000

# Job Object Information Classes
JobObjectBasicAccountingInformation: int = 1
JobObjectBasicLimitInformation: int = 2
JobObjectBasicProcessIdList: int = 3
JobObjectExtendedLimitInformation: int = 9

# Wait Results
WAIT_OBJECT_0: int = 0x00000000
WAIT_TIMEOUT: int = 0x00000102
WAIT_FAILED: int = 0xFFFFFFFF
INFINITE: int = 0xFFFFFFFF

# Win32 Error Codes
ERROR_SUCCESS: int = 0
ERROR_ACCESS_DENIED: int = 5
ERROR_INVALID_HANDLE: int = 6
ERROR_NOT_ENOUGH_MEMORY: int = 8
ERROR_BROKEN_PIPE: int = 109
ERROR_OPERATION_ABORTED: int = 995
ERROR_INSUFFICIENT_BUFFER: int = 122
ERROR_COMMITMENT_LIMIT: int = 1455
ERROR_NOT_ENOUGH_QUOTA: int = 1816
STATUS_COMMITMENT_LIMIT: int = 0xC000012D  # 3221225773 in unsigned 32-bit
DUPLICATE_SAME_ACCESS: int = 0x00000002

