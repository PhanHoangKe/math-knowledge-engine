"""Abstract base class and execution wrapper for MKE AI model adapters."""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Awaitable

from mke_product.ai.contracts import (
    ModelExtractionRequest,
    ModelExtractionResponse,
    ProviderError,
    ProviderTimeoutError,
    RetryPolicy,
    TelemetryRecord,
)


class ModelProviderAdapter(ABC):
    """Abstract interface defining required provider adapter methods."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider adapter (e.g. 'mock', 'openai', 'gemini')."""
        pass

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Configured model identifier resolved at runtime."""
        pass

    @abstractmethod
    async def extract_math_ir(
        self,
        request: ModelExtractionRequest,
        timeout: Optional[float] = None
    ) -> ModelExtractionResponse:
        """Extract structured mathematical intermediate representation from raw query."""
        pass

    @abstractmethod
    async def render_explanation(
        self,
        raw_query: str,
        structured_ir: Dict[str, Any],
        cas_evidence: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> str:
        """Render a pedagogical explanation strictly grounded in CAS evidence."""
        pass

    async def execute_with_retry(
        self,
        coro_factory: Callable[[], Awaitable[Any]],
        retry_policy: Optional[RetryPolicy] = None
    ) -> Any:
        """Execute an async operation with exponential backoff on retryable provider errors."""
        policy = retry_policy or RetryPolicy()
        attempts = 0
        current_delay = policy.initial_delay_seconds

        while True:
            try:
                return await coro_factory()
            except ProviderError as e:
                attempts += 1
                if not e.is_retryable or attempts > policy.max_retries:
                    raise
                await asyncio.sleep(current_delay)
                current_delay = min(current_delay * policy.backoff_multiplier, policy.max_delay_seconds)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # Wrap unclassified unexpected exceptions as permanent ProviderError
                raise ProviderError(f"Unexpected provider error: {str(e)}", provider_id=self.provider_id, is_retryable=False) from e
