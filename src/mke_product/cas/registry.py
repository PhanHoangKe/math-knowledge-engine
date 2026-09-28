"""Engine registry for registering, discovering, and inspecting CAS engines."""

from __future__ import annotations

from typing import Dict, List, Optional
from .contracts import EngineCapability, MathEngine, OperationType
from .native_adapter import NativeMKEAdapter
from .sympy_adapter import SymPyAdapter


class EngineRegistry:
    """Central registry for discovering and accessing mathematical engines."""

    def __init__(self) -> None:
        self._engines: Dict[str, MathEngine] = {}
        self._future_stubs: Dict[str, EngineCapability] = {}

        # Register default available engines
        self.register_engine(NativeMKEAdapter())
        self.register_engine(SymPyAdapter())

        # Register future planned engine declarations (without installing or importing)
        self.register_future_stub(
            EngineCapability(
                engine_id="scipy_numerical",
                engine_name="SciPy Numerical Engine",
                version="N/A (Planned)",
                license="3-clause BSD",
                supported_operations={
                    OperationType.SOLVE,
                    OperationType.PLOT_2D,
                },
                is_installed=False,
                is_verified_kernel=False,
                description="High-performance numerical optimization, root-finding, and scientific routines (planned future integration).",
            )
        )
        self.register_future_stub(
            EngineCapability(
                engine_id="sagemath_cas",
                engine_name="SageMath Mathematical Suite",
                version="N/A (Planned)",
                license="GPL v2+",
                supported_operations={
                    OperationType.SOLVE,
                    OperationType.SIMPLIFY,
                    OperationType.DIFFERENTIATE,
                    OperationType.INTEGRATE,
                },
                is_installed=False,
                is_verified_kernel=False,
                description="Comprehensive mathematical software system combining multiple open-source mathematics libraries (planned future integration).",
            )
        )

    def register_engine(self, engine: MathEngine) -> None:
        self._engines[engine.engine_id] = engine

    def register_future_stub(self, capability: EngineCapability) -> None:
        self._future_stubs[capability.engine_id] = capability

    def get_engine(self, engine_id: str) -> Optional[MathEngine]:
        return self._engines.get(engine_id)

    def list_engines(self) -> List[EngineCapability]:
        caps = [engine.get_capabilities() for engine in self._engines.values()]
        caps.extend(self._future_stubs.values())
        return caps

    def list_active_engines(self) -> List[EngineCapability]:
        return [engine.get_capabilities() for engine in self._engines.values()]

    def get_capabilities_map(self) -> Dict[str, Dict]:
        return {cap.engine_id: cap.to_dict() for cap in self.list_engines()}


CASRegistry = EngineRegistry

# Global singleton registry instance
_default_registry: Optional[EngineRegistry] = None


def get_engine_registry() -> EngineRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = EngineRegistry()
    return _default_registry

