"""MKE MVP V1 — Revision & Computation Cache Identity.

Provides deterministic cryptographic hashing separating:
1. Semantic Problem Identity (derived purely from mathematical truth inputs)
2. Engine / Rule Config Identity (derived from versioned verifiers and registries)
3. Computation Cache Identity (composite key for deterministic artifact caching)
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from mke_product.core.rational import Rational
from mke_product.domain.models import Assumption, ProblemCategory


def compute_semantic_quadratic_identity(
    a_rat: Rational,
    b_rat: Rational,
    c_rat: Rational,
    target_var: str = "x",
    assumptions: Optional[List[Assumption]] = None,
    schema_version: str = "1.0.0",
) -> str:
    """Compute deterministic SHA-256 semantic identity for a quadratic problem.

    Excludes:
    - UI presentation mode
    - UI theme / layout
    - Viewport zoom/pan coordinates
    - Timestamps
    - Vietnamese display strings
    """
    assump_payload = []
    if assumptions:
        for asm in assumptions:
            assump_payload.append({
                "symbol": asm.symbol,
                "domain": asm.domain,
            })
        assump_payload.sort(key=lambda x: x["symbol"])

    payload: Dict[str, Any] = {
        "schema_version": schema_version,
        "category": ProblemCategory.ALGEBRA_QUADRATIC.value,
        "target_variable": target_var,
        "a": {"numerator": a_rat.numerator, "denominator": a_rat.denominator},
        "b": {"numerator": b_rat.numerator, "denominator": b_rat.denominator},
        "c": {"numerator": c_rat.numerator, "denominator": c_rat.denominator},
        "coefficient_domain": "Q",
        "solution_domain": "R",
        "assumptions": assump_payload,
    }

    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_engine_config_identity(
    engine_version: str = "1.0.0",
    registry_version: str = "1.0.0",
    verifier_version: str = "1.0.0",
    active_rule_set: str = "GDPT_2018_THCS",
) -> str:
    """Compute deterministic SHA-256 hash representing engine and verifier configuration."""
    payload = {
        "engine_version": engine_version,
        "registry_version": registry_version,
        "verifier_version": verifier_version,
        "active_rule_set": active_rule_set,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_computation_cache_identity(
    semantic_identity: str,
    engine_identity: str,
) -> str:
    """Compute composite cache key for memoizing verified computation artifacts."""
    combined = f"cache:{semantic_identity}:{engine_identity}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()
