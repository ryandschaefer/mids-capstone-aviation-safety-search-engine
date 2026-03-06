from typing import List

import requests

from .base import BaseLLM, ChatMessage, ChatResponse
from ..config import OllamaConfig


class OllamaLLM(BaseLLM):
    """
    Client that sends chat requests to a local Ollama server.
    """
    def __init__(self, cfg: OllamaConfig):
        self.cfg = cfg

    def chat(self, messages: List[ChatMessage]) -> ChatResponse:
        """
        Call Ollama's endpoint with the given messages.
        """
        payload = {
            "model": self.cfg.model,
            "stream": False,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }

        resp = requests.post(f"{self.cfg.base_url}/api/chat", json=payload)
        resp.raise_for_status()

        data = resp.json()
        content = (data.get("message") or {}).get("content") or ""
        return ChatResponse(content=content)