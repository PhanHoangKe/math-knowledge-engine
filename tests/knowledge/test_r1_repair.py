"""Comprehensive regression test suite for DEV-02A REPAIR R1.

Verifies:
1. Dispatcher fix for PROB_FAM02_V03 (5*x = 0, x*5 = 0, -3*x = 0, 0*x = 0, 0*x = 1, and deg >= 2 products).
2. Bounded M1 expansion for FAM03 (rational coefficients with non-zero constant denominators).
3. Variable denominator equations are strictly rejected by M1 and routed to M4.
4. Adjudicated provisional annotations for PROB_FAM07_V03 and PROB_FAM08_V03.
5. Preservation of PAIR_FAM09_V01_V03 transfer near-miss discrepancy.
"""

import pytest
import sympy

from mke.domain.extractor import extract_original_domain
from mke.knowledge.dev01_adapter import Dev01Adapter
from mke.knowledge.repository import MethodKnowledgeRepository
from mke.methods.m1_linear import LinearEquationMethod
from mke.methods.m3_factorization import FactorizationMethod
from mke.models.enums import MethodAdmissibility, MethodId, SolutionProofStatus, TransferValidity
from mke.parsing.normalizer import normalize_equation
from mke.parsing.parser import Parser
from mke.verification.engine import VerificationEngine


# ==============================================================================
# Requirement 1: Dispatcher Fix & Regressions
# ==============================================================================

def test_r1_dispatcher_prob_fam02_v03_5x_zero():
    """5*x = 0 dispatches to M1, returns exact root {0} with complete verification."""
    eng = VerificationEngine()
    res = eng.verify("5*x = 0")
    assert res.method_instance is not None
    assert res.method_instance.method_id == MethodId.M1_LINEAR_EQUATION
    assert res.is_verified_method is True
    assert res.is_verified_solution is True
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert res.verified_roots == ["0"]


def test_r1_dispatcher_x_times_5_zero():
    """x*5 = 0 dispatches to M1, returns exact root {0}."""
    eng = VerificationEngine()
    res = eng.verify("x*5 = 0")
    assert res.method_instance is not None
    assert res.method_instance.method_id == MethodId.M1_LINEAR_EQUATION
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert res.verified_roots == ["0"]


def test_r1_dispatcher_negative_coefficient():
    """-3*x = 0 dispatches to M1, returns exact root {0}."""
    eng = VerificationEngine()
    res = eng.verify("-3*x = 0")
    assert res.method_instance is not None
    assert res.method_instance.method_id == MethodId.M1_LINEAR_EQUATION
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert res.verified_roots == ["0"]


def test_r1_dispatcher_degenerate_identity_0x_zero():
    """0*x = 0 dispatches to M1 as degenerate linear identity on domain."""
    eng = VerificationEngine()
    res = eng.verify("0*x = 0")
    assert res.method_instance is not None
    assert res.method_instance.method_id == MethodId.M1_LINEAR_EQUATION
    assert res.is_identity_on_domain is True
    assert res.is_verified_solution is True
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE


def test_r1_dispatcher_degenerate_contradiction_0x_one():
    """0*x = 1 dispatches to M1, proves empty solution set on R."""
    eng = VerificationEngine()
    res = eng.verify("0*x = 1")
    assert res.method_instance is not None
    assert res.method_instance.method_id == MethodId.M1_LINEAR_EQUATION
    assert res.is_verified_solution is True
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert len(res.verified_roots) == 0


def test_r1_dispatcher_degree_ge_2_products_remain_m3():
    """Factored equations of degree >= 2 continue dispatching to M3."""
    eng = VerificationEngine()

    res1 = eng.verify("(x - 1)*(x + 2) = 0")
    assert res1.method_instance is not None
    assert res1.method_instance.method_id == MethodId.M3_FACTORIZATION
    assert set(res1.verified_roots) == {"-2", "1"}

    res2 = eng.verify("x*(x - 3) = 0")
    assert res2.method_instance is not None
    assert res2.method_instance.method_id == MethodId.M3_FACTORIZATION
    assert set(res2.verified_roots) == {"0", "3"}


# ==============================================================================
# Requirement 2: Bounded M1 Expansion for FAM03
# ==============================================================================

def test_r1_fam03_v01_concrete_rational_coefficients():
    """(1/2)*x + 3/4 = 0 solves via M1 with exact root {-3/2}."""
    eng = VerificationEngine()
    res = eng.verify("(1/2)*x + 3/4 = 0")
    assert res.method_instance.method_id == MethodId.M1_LINEAR_EQUATION
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert res.verified_roots == ["-3/2"]


def test_r1_fam03_v02_concrete_rational_coefficients():
    """(2/3)*x - 4/5 = 0 solves via M1 with exact root {6/5}."""
    eng = VerificationEngine()
    res = eng.verify("(2/3)*x - 4/5 = 0")
    assert res.method_instance.method_id == MethodId.M1_LINEAR_EQUATION
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert res.verified_roots == ["6/5"]


def test_r1_fam03_v03_concrete_rational_coefficients():
    """(1/2)*x + 3/4 = 1/4 solves via M1 with exact root {-1}."""
    eng = VerificationEngine()
    res = eng.verify("(1/2)*x + 3/4 = 1/4")
    assert res.method_instance.method_id == MethodId.M1_LINEAR_EQUATION
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert res.verified_roots == ["-1"]


def test_r1_m1_strictly_rejects_variable_denominators():
    """Equations with variable denominators are NOT admissible under M1 and route to M4."""
    m1 = LinearEquationMethod()

    # Case 1: (x - 2)/(x - 2) = 1 has variable denominator despite cancellation
    ast1 = Parser.from_text("(x - 2)/(x - 2) = 1").parse_equation()
    norm1 = normalize_equation(ast1)
    assert norm1.has_variable_denominator is True
    assert norm1.is_rational is True
    assert m1.evaluate_admissibility(norm1) == MethodAdmissibility.NOT_APPLICABLE

    # Case 2: 1/(x - 1) = 0 has variable denominator
    ast2 = Parser.from_text("1/(x - 1) = 0").parse_equation()
    norm2 = normalize_equation(ast2)
    assert norm2.has_variable_denominator is True
    assert norm2.is_rational is True
    assert m1.evaluate_admissibility(norm2) == MethodAdmissibility.NOT_APPLICABLE

    # Case 3: (x^2 - 1)/(x - 1) = 0 has variable denominator and excluded point
    ast3 = Parser.from_text("(x^2 - 1)/(x - 1) = 0").parse_equation()
    norm3 = normalize_equation(ast3)
    assert norm3.has_variable_denominator is True
    assert norm3.is_rational is True
    assert m1.evaluate_admissibility(norm3) == MethodAdmissibility.NOT_APPLICABLE


# ==============================================================================
# Requirement 3: Adjudication of Provisional Annotations
# ==============================================================================

def test_r1_prob_fam07_v03_adjudicated_applicable():
    """PROB_FAM07_V03: x*(x-3)=4 normalizes to x^2-3x-4=0, M3 is APPLICABLE with roots {-1, 4}."""
    repo = MethodKnowledgeRepository()
    prob = repo.get_problem("PROB_FAM07_V03")
    assert prob is not None

    annotations = repo.get_annotations_for_problem("PROB_FAM07_V03")
    assert len(annotations) == 1
    ann = annotations[0]
    assert ann.admissibility == MethodAdmissibility.APPLICABLE
    assert ann.review_status.value == "PROVISIONAL"

    eng = VerificationEngine()
    res = eng.verify(prob.original_expression, method_id=MethodId.M3_FACTORIZATION)
    assert res.method_instance.method_id == MethodId.M3_FACTORIZATION
    assert res.is_verified_solution is True
    assert set(res.verified_roots) == {"-1", "4"}


def test_r1_prob_fam08_v03_adjudicated_not_applicable():
    """PROB_FAM08_V03: x^2+9=0 has empty roots on R; M3 is NOT_APPLICABLE (irreducible over Q)."""
    repo = MethodKnowledgeRepository()
    prob = repo.get_problem("PROB_FAM08_V03")
    assert prob is not None

    annotations = repo.get_annotations_for_problem("PROB_FAM08_V03")
    assert len(annotations) == 1
    ann = annotations[0]
    assert ann.admissibility == MethodAdmissibility.NOT_APPLICABLE
    assert ann.review_status.value == "PROVISIONAL"

    # Solver check: M3 fails rational factorization guard
    m3 = FactorizationMethod()
    ast = Parser.from_text(prob.original_expression).parse_equation()
    norm = normalize_equation(ast)
    assert m3.evaluate_admissibility(norm) == MethodAdmissibility.NOT_APPLICABLE


# ==============================================================================
# Requirement 4: Preservation of Transfer Near-Miss Discrepancy
# ==============================================================================

def test_r1_pair_fam09_v01_v03_transfer_near_miss_preserved():
    """PAIR_FAM09_V01_V03 must reject naive transfer with residue -4 and preserve discrepancy."""
    repo = MethodKnowledgeRepository()
    pairs = repo.list_transfer_pairs()
    pair = next(p for p in pairs if p.pair_id == "PAIR_FAM09_V01_V03")
    assert pair is not None
    assert pair.proposed_transfer_status.value == "INAPPLICABLE_INSTANCE"
    assert pair.review_status.value == "PROVISIONAL"

    adapter = Dev01Adapter(repo)
    eval_res = adapter.evaluate_transfer_pair(pair)
    assert eval_res["has_discrepancy"] is True
    assert eval_res["proposed_status"] == "INAPPLICABLE_INSTANCE"
    assert eval_res["audited_status"] == "UNSAFE_COPY"
    assert len(eval_res["rejected_transferred_roots"]) == 2
    assert "residue=-4" in eval_res["rejected_transferred_roots"][0]


# ==============================================================================
# Global Acceptance Gate: Exactly 1 Discrepancy (the Transfer Near-Miss)
# ==============================================================================

def test_r1_full_dev_validation_discrepancies():
    """Full DEV_PILOT validation must report 41/41 solution verified and exactly 1 discrepancy."""
    repo = MethodKnowledgeRepository()
    adapter = Dev01Adapter(repo)
    summary = adapter.validate_dataset()

    assert summary["total_problems"] == 41
    assert summary["solution_verified_count"] == 41
    assert summary["match_ground_truth_count"] == 43
    assert summary["discrepancy_count"] == 1
    assert summary["discrepancies"][0]["type"] == "TRANSFER_DISCREPANCY"
    assert summary["discrepancies"][0]["transfer_pair_id"] == "PAIR_FAM09_V01_V03"
