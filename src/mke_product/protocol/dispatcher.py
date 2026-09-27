"""Deterministic mathematical request dispatcher for MKE Product protocol."""

from __future__ import annotations
import json
from typing import Any, Dict, Optional, Union

from ..core.rational import Rational
from ..parser.parser import parse_equation
from ..parser.errors import MKEParserError, ParserError, LexerError, InputBoundsExceededError
from ..evaluator.budget import EvaluationBudget
from ..evaluator.evaluator import check_candidate
from ..evaluator.result import CandidateCheckStatus
from ..evaluator.errors import InvalidCandidateError
from ..solver.solver import solve_equation
from ..solver.result import SolverScopeStatus
from .errors import ProtocolError
from .schema import (
    SCHEMA_VERSION,
    OPERATION_SOLVE,
    OPERATION_CHECK_CANDIDATE,
    MAX_RESPONSE_BYTES,
    MIN_RESPONSE_BYTES,
    serialize_rational,
    serialize_span,
)
from .validator import parse_and_validate_raw_payload, validate_request_dict


def _build_bounded_response(
    res_dict: Dict[str, Any],
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> Dict[str, Any]:
    """Ensure response serialized length does not exceed maximum response byte ceiling.

    If exceeded, fail closed with ERR_RESPONSE_LIMIT_EXCEEDED and definedness: None,
    without truncating numbers or fabricating certificates.
    """
    if type(max_bytes) is not int or max_bytes < MIN_RESPONSE_BYTES:
        raise ValueError(
            f"max_response_bytes must be an integer >= {MIN_RESPONSE_BYTES}; got {max_bytes!r}."
        )

    try:
        serialized = json.dumps(res_dict, separators=(",", ":")).encode("utf-8")
        if len(serialized) <= max_bytes:
            return res_dict
    except Exception:
        pass

    op = res_dict.get("operation")
    fallback = {
        "schema_version": SCHEMA_VERSION,
        "operation": op,
        "outcome": "RESOURCE_EXHAUSTED",
        "status": "ERR_RESPONSE_LIMIT_EXCEEDED",
        "error": {
            "code": "ERR_RESPONSE_LIMIT_EXCEEDED",
            "message": f"Serialized response exceeded maximum limit of {max_bytes} bytes.",
            "span": None,
        },
        "definedness": None,
        "is_provisional_evidence": False,
    }
    fallback_serialized = json.dumps(fallback, separators=(",", ":")).encode("utf-8")
    if len(fallback_serialized) > max_bytes:
        raise ValueError(
            f"Fallback response length ({len(fallback_serialized)} bytes) exceeds max_bytes ({max_bytes} bytes)."
        )
    return fallback


def dispatch_request(
    payload: Union[str, bytes, Dict[str, Any]],
    budget: Optional[EvaluationBudget] = None,
    max_response_bytes: int = MAX_RESPONSE_BYTES,
) -> Dict[str, Any]:
    """Validate and dispatch a versioned request over the S0-S3 mathematical kernel.

    Guarantees:
    - Side-effect-free in-memory execution.
    - Strict framing, version, operation, and type allowlists.
    - Decoupled independent execution for SOLVE and CHECK_CANDIDATE.
    - Exact rational numbers serialized as decimal-string numerator/denominator.
    - Explicit distinction between protocol errors, syntax errors, and mathematical outcomes.
    - Three-valued definedness (true, false, null).
    - Clear marking of provisional mathematical inspection evidence.
    - Enforceable response serialized byte bounds.
    """
    if type(max_response_bytes) is not int or max_response_bytes < MIN_RESPONSE_BYTES:
        raise ValueError(
            f"max_response_bytes must be an integer >= {MIN_RESPONSE_BYTES}; got {max_response_bytes!r}."
        )
    # Step 1: Decode and validate payload framing
    try:
        raw_dict = parse_and_validate_raw_payload(payload)
        req = validate_request_dict(raw_dict)
    except ProtocolError as err:
        return _build_bounded_response({
            "schema_version": SCHEMA_VERSION,
            "operation": err.operation,
            "outcome": "PROTOCOL_ERROR",
            "status": err.code,
            "error": err.to_dict(),
            "definedness": None,
            "is_provisional_evidence": False,
        }, max_bytes=max_response_bytes)

    op = req["operation"]
    eq_str = req["equation"]

    # Step 2: Parse Equation AST using S1 parser
    try:
        eq_ast = parse_equation(eq_str)
    except MKEParserError as err:
        err_code = getattr(err, "code", f"ERR_SYNTAX_{type(err).__name__}")
        return _build_bounded_response({
            "schema_version": SCHEMA_VERSION,
            "operation": op,
            "outcome": "SYNTAX_ERROR",
            "status": err_code,
            "error": {
                "code": err_code,
                "message": err.message,
                "span": serialize_span(err.span),
            },
            "definedness": None,
            "is_provisional_evidence": False,
        }, max_bytes=max_response_bytes)

    # Step 3: Operational dispatch
    if op == OPERATION_SOLVE:
        res = solve_equation(eq_ast, budget=budget)

        if res.status == SolverScopeStatus.IN_SCOPE:
            outcome = "SUCCESS"
            status_str = res.classification.value if res.classification else "UNKNOWN"
            definedness = True
            error_payload = None
        elif res.status == SolverScopeStatus.DOMAIN_ERROR:
            outcome = "DOMAIN_ERROR"
            status_str = res.error_code or "ERR_DOMAIN_ERROR"
            definedness = False
            error_payload = {
                "code": res.error_code or "ERR_DOMAIN_ERROR",
                "message": res.error_message or "Proven domain error in original unreduced expression.",
                "span": serialize_span(res.error_span),
            }
        elif res.status == SolverScopeStatus.OUT_OF_SCOPE:
            outcome = "OUT_OF_SCOPE"
            status_str = res.error_code or "ERR_OUT_OF_SCOPE"
            definedness = None
            error_payload = {
                "code": res.error_code or "ERR_OUT_OF_SCOPE",
                "message": res.error_message or "Equation is out of scope for affine linear solver.",
                "span": serialize_span(res.error_span),
            }
        elif res.status == SolverScopeStatus.RESOURCE_EXHAUSTED:
            outcome = "RESOURCE_EXHAUSTED"
            status_str = res.error_code or "ERR_RESOURCE_EXHAUSTED"
            definedness = None
            error_payload = {
                "code": res.error_code or "ERR_RESOURCE_EXHAUSTED",
                "message": res.error_message or "Resource budget exhausted during equation solving.",
                "span": serialize_span(res.error_span),
            }
        else:  # INTERNAL_VERIFICATION_FAILURE
            outcome = "INTERNAL_VERIFICATION_FAILURE"
            status_str = res.error_code or "ERR_INTERNAL_VERIFICATION_FAILURE"
            definedness = None
            error_payload = {
                "code": res.error_code or "ERR_INTERNAL_VERIFICATION_FAILURE",
                "message": res.error_message or "Internal independent candidate verification failed.",
                "span": serialize_span(res.error_span),
            }

        evidence_dict = res.evidence.to_dict() if res.evidence is not None else None

        return _build_bounded_response({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "outcome": outcome,
            "status": status_str,
            "classification": res.classification.value if res.classification else None,
            "root": serialize_rational(res.root),
            "definedness": definedness,
            "error": error_payload,
            "is_provisional_evidence": evidence_dict is not None,
            "evidence": evidence_dict,
        }, max_bytes=max_response_bytes)

    elif op == OPERATION_CHECK_CANDIDATE:
        cand_str = req["candidate"]
        try:
            cand_res = check_candidate(eq_ast, cand_str, budget=budget)
        except InvalidCandidateError as err:
            return _build_bounded_response({
                "schema_version": SCHEMA_VERSION,
                "operation": OPERATION_CHECK_CANDIDATE,
                "outcome": "PROTOCOL_ERROR",
                "status": err.code,
                "candidate": None,
                "exact_equality": None,
                "residual": None,
                "left_value": None,
                "right_value": None,
                "definedness": None,
                "error": {
                    "code": err.code,
                    "message": err.message,
                    "span": None,
                },
                "is_provisional_evidence": False,
            }, max_bytes=max_response_bytes)

        if cand_res.status == CandidateCheckStatus.VALID:
            outcome = "SUCCESS"
            status_str = "VALID"
            exact_equality = True
            residual = Rational(0, 1)
            definedness = True
            error_payload = None
        elif cand_res.status == CandidateCheckStatus.INVALID:
            outcome = "SUCCESS"
            status_str = "INVALID"
            exact_equality = False
            if cand_res.left_value is not None and cand_res.right_value is not None:
                diff = cand_res.left_value - cand_res.right_value
                residual = abs(diff)
            else:
                residual = None
            definedness = True
            error_payload = None
        elif cand_res.status == CandidateCheckStatus.DOMAIN_ERROR:
            outcome = "DOMAIN_ERROR"
            status_str = cand_res.error_code or "ERR_DOMAIN_ERROR"
            exact_equality = None
            residual = None
            definedness = False
            error_payload = {
                "code": cand_res.error_code or "ERR_DOMAIN_ERROR",
                "message": cand_res.error_message or "Original expression undefined at candidate.",
                "span": serialize_span(cand_res.error_span),
            }
        elif cand_res.status == CandidateCheckStatus.RESOURCE_EXHAUSTED:
            outcome = "RESOURCE_EXHAUSTED"
            status_str = cand_res.error_code or "ERR_RESOURCE_EXHAUSTED"
            exact_equality = None
            residual = None
            definedness = None
            error_payload = {
                "code": cand_res.error_code or "ERR_RESOURCE_EXHAUSTED",
                "message": cand_res.error_message or "Resource budget exhausted during candidate check.",
                "span": serialize_span(cand_res.error_span),
            }
        else:  # UNSUPPORTED
            outcome = "UNSUPPORTED"
            status_str = cand_res.error_code or "ERR_UNSUPPORTED"
            exact_equality = None
            residual = None
            definedness = None
            error_payload = {
                "code": cand_res.error_code or "ERR_UNSUPPORTED",
                "message": cand_res.error_message or "Expression unsupported for evaluation.",
                "span": serialize_span(cand_res.error_span),
            }

        return _build_bounded_response({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "outcome": outcome,
            "status": status_str,
            "candidate": serialize_rational(cand_res.candidate),
            "exact_equality": exact_equality,
            "residual": serialize_rational(residual),
            "left_value": serialize_rational(cand_res.left_value),
            "right_value": serialize_rational(cand_res.right_value),
            "definedness": definedness,
            "error": error_payload,
            "is_provisional_evidence": True,
            "diagnostics": dict(cand_res.diagnostics),
        }, max_bytes=max_response_bytes)

    else:
        # Fallback for unexpected operation
        return _build_bounded_response({
            "schema_version": SCHEMA_VERSION,
            "operation": op,
            "outcome": "PROTOCOL_ERROR",
            "status": "ERR_PROTOCOL_UNKNOWN_OPERATION",
            "error": {
                "code": "ERR_PROTOCOL_UNKNOWN_OPERATION",
                "message": f"Operation {op!r} is not supported.",
                "span": None,
            },
            "definedness": None,
            "is_provisional_evidence": False,
        }, max_bytes=max_response_bytes)


def dispatch_json(
    payload: Union[str, bytes],
    budget: Optional[EvaluationBudget] = None,
    max_response_bytes: int = MAX_RESPONSE_BYTES,
) -> str:
    """Convenience helper dispatching JSON string/bytes and returning compact JSON string."""
    if type(max_response_bytes) is not int or max_response_bytes < MIN_RESPONSE_BYTES:
        raise ValueError(
            f"max_response_bytes must be an integer >= {MIN_RESPONSE_BYTES}; got {max_response_bytes!r}."
        )
    res_dict = dispatch_request(payload, budget=budget, max_response_bytes=max_response_bytes)
    return json.dumps(res_dict, separators=(",", ":"))
