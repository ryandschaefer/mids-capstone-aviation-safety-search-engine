import os

from .base import BaseLLM
from .client import OllamaLLM
from ..config import OllamaConfig


def build_llm() -> BaseLLM:
    """
    Factory for building the LLM backend.
    """
    default_cfg = OllamaConfig()
    base_url = os.getenv("OLLAMA_URL") or default_cfg.base_url
    model = os.getenv("OLLAMA_MODEL") or default_cfg.model
    cfg = OllamaConfig(base_url=base_url, model=model)
    print("Model:", model)
    return OllamaLLM(cfg)