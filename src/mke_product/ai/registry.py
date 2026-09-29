"""Configurable runtime provider registry for MKE AI Intake."""

import os
from typing import Dict, Type, List, Optional
from mke_product.ai.adapter import ModelProviderAdapter


class ModelProviderRegistry:
    """Registry supporting dynamic registration and resolution of provider adapters."""

    _registry: Dict[str, Type[ModelProviderAdapter]] = {}

    @classmethod
    def register(cls, provider_id: str, adapter_cls: Type[ModelProviderAdapter]) -> None:
        """Register a provider adapter class under a unique provider_id."""
        normalized_id = provider_id.strip().lower()
        if not normalized_id:
            raise ValueError("provider_id cannot be empty")
        cls._registry[normalized_id] = adapter_cls

    @classmethod
    def unregister(cls, provider_id: str) -> None:
        """Unregister a provider adapter."""
        normalized_id = provider_id.strip().lower()
        cls._registry.pop(normalized_id, None)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered adapters (primarily for test isolation)."""
        cls._registry.clear()

    @classmethod
    def list_providers(cls) -> List[str]:
        """Return list of registered provider IDs."""
        return sorted(list(cls._registry.keys()))

    @classmethod
    def resolve(
        cls,
        provider_id: Optional[str] = None,
        model_id: Optional[str] = None,
        **kwargs
    ) -> ModelProviderAdapter:
        """Resolve and instantiate a provider adapter by ID or environment variable."""
        pid = provider_id or os.getenv("MKE_INTAKE_PROVIDER", "mock")
        normalized_id = pid.strip().lower()

        adapter_cls = cls._registry.get(normalized_id)
        if not adapter_cls:
            available = cls.list_providers()
            raise ValueError(
                f"Unsupported provider '{pid}'. Registered providers: {available}. "
                f"Ensure the adapter is registered before resolution."
            )

        resolved_model_id = model_id or os.getenv("MKE_INTAKE_MODEL_ID", "default-model")
        return adapter_cls(model_id=resolved_model_id, **kwargs)
