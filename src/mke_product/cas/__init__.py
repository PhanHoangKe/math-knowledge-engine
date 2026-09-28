"""MKE Multi-Engine CAS Integration Package (PRODUCT-03A)."""

from .contracts import (
    EngineCapability,
    EngineStatus,
    ExecutionRequest,
    ExecutionResponse,
    MathEngine,
    OperationType,
    SCHEMA_VERSION_P03A,
)
from .registry import EngineRegistry, get_engine_registry
from .router import EngineRouter, execute_cas_operation
from .sympy_adapter import SymPyAdapter
from .native_adapter import NativeMKEAdapter
from .ast_bridge import ast_to_sympy, ast_to_sympy_expr
from .safety import inspect_ast_safety, extract_domain_restrictions, SafetyError, DomainRestrictionError

__all__ = [
    "EngineCapability",
    "EngineStatus",
    "ExecutionRequest",
    "ExecutionResponse",
    "MathEngine",
    "OperationType",
    "SCHEMA_VERSION_P03A",
    "EngineRegistry",
    "get_engine_registry",
    "EngineRouter",
    "execute_cas_operation",
    "SymPyAdapter",
    "NativeMKEAdapter",
    "ast_to_sympy",
    "ast_to_sympy_expr",
    "inspect_ast_safety",
    "extract_domain_restrictions",
    "SafetyError",
    "DomainRestrictionError",
]
