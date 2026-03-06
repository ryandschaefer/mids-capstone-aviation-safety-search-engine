from dataclasses import dataclass
from typing import List, Literal


Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    """Simple chat message used as input to any LLM client."""
    role: Role
    content: str


@dataclass(frozen=True)
class ChatResponse:
    """Minimal wrapper around the LLM's text response."""
    content: str


class BaseLLM:
    def chat(self, messages: List[ChatMessage]) -> ChatResponse:
        """
        Run a chat completion with underlying model.
        """
        raise NotImplementedError