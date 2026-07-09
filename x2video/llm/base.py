"""Abstract LLM provider interface.

All implementations use neutral naming — no vendor-specific identifiers
in class names, method signatures, or docstrings.
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract base for LLM providers.

    Two modes:
    - complete():       plain text completion (Script generation)
    - complete_structured():  JSON Schema-driven structured output (Curation scoring)
    """

    @abstractmethod
    async def complete(
        self, messages: list[dict[str, str]], **kwargs: Any
    ) -> str:
        """Send a chat completion request and return the response text.

        Args:
            messages: Standard chat messages as `[{"role": "...", "content": "..."}]`.
            **kwargs: Provider-specific overrides (temperature, max_tokens, etc.).

        Returns:
            The model's text response.
        """
        ...

    @abstractmethod
    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        output_schema: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a chat completion and parse structured output via JSON Schema.

        Used for curation scoring where the response must be a validated
        list of scored candidates.

        Args:
            messages: Chat messages.
            output_schema: JSON Schema dict describing the expected output.
            **kwargs: Provider-specific overrides.

        Returns:
            Parsed structured output as a dict (e.g. `{"picks": [{...}, ...]}`).
        """
        ...
