"""DomainAdapter abstract base class and domain execution contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field

from mke_product.coverage.contracts import (
    CandidateSolution,
    ProblemIR,
    ProblemKind,
    SolutionTrace,
    VerificationReport,
)


class DifficultyLevel(BaseModel):
    """Problem difficulty assessment."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    level_code: str  # EASY, MEDIUM, HARD, OLYMPIAD
    score: float = Field(default=1.0, ge=0.0)


class MethodAssessment(BaseModel):
    """Assessment of a pedagogical method for a given problem."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    method_id: str
    method_name_vi: str
    method_name_en: str = ""
    is_applicable: bool
    is_recommended: bool
    selection_reason: str = ""


class DomainClassification(BaseModel):
    """Domain classification summary."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    problem_kind: ProblemKind
    sub_form: str
    difficulty: str = "MEDIUM"
    applicable_methods: Tuple[MethodAssessment, ...] = Field(default_factory=tuple)


class ExecutionOptions(BaseModel):
    """Configuration options for candidate solver execution."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    timeout_sec: float = Field(default=5.0, gt=0.0)
    max_steps: int = Field(default=100, gt=0)
    flags: Tuple[Tuple[str, str], ...] = Field(default_factory=tuple)


class DomainAdapter(ABC):
    """Universal contract for mathematical domain handling."""

    @property
    @abstractmethod
    def adapter_id(self) -> str:
        """Unique identifier, e.g. 'mke.adapter.legacy_quadratic.v1'."""
        pass

    @property
    @abstractmethod
    def supported_problem_kinds(self) -> Tuple[ProblemKind, ...]:
        """Declared immutable sequence of problem kinds supported by this adapter."""
        pass

    @abstractmethod
    def can_handle(self, ir: ProblemIR) -> bool:
        """Predicate checking if this adapter can process the given ProblemIR."""
        pass

    @abstractmethod
    def normalize(self, ir: ProblemIR) -> ProblemIR:
        """Perform domain-specific canonical normalization on the ProblemIR."""
        pass

    @abstractmethod
    def classify(self, ir: ProblemIR) -> DomainClassification:
        """Classify sub-form, difficulty, and applicable methods."""
        pass

    @abstractmethod
    def solve_candidates(self, ir: ProblemIR, options: Optional[ExecutionOptions] = None) -> Tuple[CandidateSolution, ...]:
        """Generate candidate solutions using SymPy/CAS or legacy solver via containment."""
        pass

    @abstractmethod
    def verify(self, ir: ProblemIR, candidate: CandidateSolution) -> VerificationReport:
        """Independently verify candidate solution using deterministic MKE logic."""
        pass

    @abstractmethod
    def build_trace(
        self,
        ir: ProblemIR,
        candidate: CandidateSolution,
        verification: VerificationReport,
        selected_method_id: Optional[str] = None,
    ) -> SolutionTrace:
        """Construct structured, pedagogically sound, step-by-step solution trace."""
        pass

    @abstractmethod
    def supported_methods(self, ir: ProblemIR) -> Tuple[MethodAssessment, ...]:
        """List available pedagogical methods for this problem."""
        pass

    @abstractmethod
    def limitations(self) -> Tuple[str, ...]:
        """Document known mathematical boundaries and edge cases."""
        pass
