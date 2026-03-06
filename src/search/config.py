from dataclasses import dataclass

@dataclass
class PipelineConfig:
    top_k_candidates: int = 30
    top_k_final: int = 10
    
    # refinement
    max_loops: int = 3
    accept_threshold: float = 1.0
    
    # embeddings
    chunk_size: int = 250
    overlap: int = 50
    
    # llm
    judge_batch_size: int = 6
    max_chunk_chars: int = 250


@dataclass(frozen=True)
class OllamaConfig:
    """
    Config for using a local Ollama model as the LLM backend.
    """
    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.2:3b"