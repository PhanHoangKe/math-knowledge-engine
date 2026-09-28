"""Core contracts, interfaces, and data models for the MKE CAS multi-engine architecture."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from mke_product.parser.ast import ASTNode

SCHEMA_VERSION_P03A = "mke.product03a.v0"


class OperationType(str, Enum):
    """Mathematical operations supported across CAS engines."""
    SOLVE = "SOLVE"
    SIMPLIFY = "SIMPLIFY"
    DIFFERENTIATE = "DIFFERENTIATE"
    INTEGRATE = "INTEGRATE"
    PLOT_2D = "PLOT_2D"
    CHECK_CANDIDATE = "CHECK_CANDIDATE"


class EngineStatus(str, Enum):
    """Standardized mathematical execution and verification status."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    UNRESOLVED = "UNRESOLVED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    DOMAIN_ERROR = "DOMAIN_ERROR"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_EXHAUSTED"
    SECURITY_REJECTED = "SECURITY_REJECTED"
    INVALID_INPUT = "INVALID_INPUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class VerificationStatus(str, Enum):
    """Standardized verification level for mathematical solutions."""
    VERIFIED_WITH_EVIDENCE = "VERIFIED_WITH_EVIDENCE"
    CANDIDATE_CHECKED = "CANDIDATE_CHECKED"
    COMPUTED = "COMPUTED"
    PARTIAL = "PARTIAL"
    UNRESOLVED = "UNRESOLVED"
    NOT_VERIFIED = "NOT_VERIFIED"
    ERROR = "ERROR"



@dataclass(frozen=True)
class EngineCapability:
    """Metadata and capability declaration for a mathematical engine."""
    engine_id: str
    engine_name: str
    version: str
    license: str
    supported_operations: Set[OperationType]
    is_installed: bool = True
    is_verified_kernel: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "engine_name": self.engine_name,
            "version": self.version,
            "license": self.license,
            "supported_operations": sorted([op.value for op in self.supported_operations]),
            "is_installed": self.is_installed,
            "is_verified_kernel": self.is_verified_kernel,
            "description": self.description,
        }


@dataclass
class ExecutionRequest:
    """Standard request passed to mathematical engines."""
    operation: OperationType
    raw_input: str = ""
    expression: str = ""
    request_id: str = ""
    ast: Optional[ASTNode] = None
    variable: str = "x"
    options: Dict[str, Any] = field(default_factory=dict)
    preferred_engine: Optional[str] = None
    timeout_sec: float = 5.0

    def __post_init__(self) -> None:
        if not self.raw_input and self.expression:
            self.raw_input = self.expression
        elif not self.expression and self.raw_input:
            self.expression = self.raw_input
        if self.preferred_engine and "engine_override" not in self.options:
            self.options["engine_override"] = self.preferred_engine


@dataclass
class ExecutionResponse:
    """Standardized versioned response envelope from any CAS engine."""
    schema_version: str = SCHEMA_VERSION_P03A
    request_id: str = ""
    operation: str = ""
    original_input: str = ""
    selected_engine: str = ""
    mathematical_status: EngineStatus = EngineStatus.SUCCESS
    symbolic_result: Optional[str] = None
    latex_output: Optional[str] = None
    domain_restrictions: List[str] = field(default_factory=list)
    verification_evidence: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    plot_data: Optional[Dict[str, Any]] = None
    execution_duration_sec: float = 0.0
    error_message: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None

    @property
    def status(self) -> EngineStatus:
        return self.mathematical_status

    @property
    def result_str(self) -> str:
        return self.symbolic_result or ""

    @property
    def latex_str(self) -> Optional[str]:
        return self.latex_output

    @property
    def engine_used(self) -> str:
        return self.selected_engine

    @property
    def domain_notes(self) -> List[str]:
        return self.domain_restrictions

    @property
    def timing_ms(self) -> float:
        return self.execution_duration_sec * 1000.0

    @property
    def details(self) -> Dict[str, Any]:
        return self.verification_evidence or {}

    @property
    def solution_set(self) -> List[str]:
        if self.verification_evidence and "solution_set" in self.verification_evidence:
            return self.verification_evidence["solution_set"]
        if self.symbolic_result:
            s = self.symbolic_result.strip()
            if s.startswith("{") and s.endswith("}"):
                inner = s[1:-1].strip()
                if not inner:
                    return []
                return [item.strip() for item in inner.split(",") if item.strip()]
            if s.startswith("x = "):
                return [s[4:].strip()]
        return []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "operation": self.operation,
            "original_input": self.original_input,
            "selected_engine": self.selected_engine,
            "mathematical_status": self.mathematical_status.value if isinstance(self.mathematical_status, EngineStatus) else str(self.mathematical_status),
            "verification_status": self.verification_status.value if isinstance(self.verification_status, VerificationStatus) else (str(self.verification_status) if self.verification_status is not None else None),
            "symbolic_result": self.symbolic_result,
            "latex_output": self.latex_output,
            "domain_restrictions": self.domain_restrictions,
            "verification_evidence": self.verification_evidence,
            "warnings": self.warnings,
            "plot_data": self.plot_data,
            "execution_duration_sec": round(self.execution_duration_sec, 6),
            "error_message": self.error_message,
        }


class MathEngine(ABC):
    """Abstract interface for mathematical engines in the MKE CAS architecture."""

    @property
    @abstractmethod
    def engine_id(self) -> str:
        """Unique identifier for this engine."""
        pass

    @abstractmethod
    def get_capabilities(self) -> EngineCapability:
        """Return engine capabilities and version metadata."""
        pass

    @abstractmethod
    def can_handle(self, request: ExecutionRequest) -> bool:
        """Predicate checking whether this engine can execute the given request."""
        pass

    @abstractmethod
    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """Execute the mathematical request and return a structured ExecutionResponse."""
        pass
