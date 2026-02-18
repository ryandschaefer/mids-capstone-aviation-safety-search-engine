#!/usr/bin/env python3
"""
Quick script to build semantic index.

Usage:
    python build_semantic_index.py [model_name]

Examples:
    python build_semantic_index.py
    python build_semantic_index.py sentence-transformers/all-mpnet-base-v2
    python build_semantic_index.py sentence-transformers/all-MiniLM-L12-v2
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from datasets import load_dataset
from models.semantic_service import SemanticIndex

# Default model (best Recall@100 in comprehensive evaluation)
DEFAULT_MODEL = "bert-base-cased"

def main():
    # Get model name from command line or use default
    model_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL

    print("=" * 80)
    print("Building Semantic Index for Aviation Safety Search")
    print("=" * 80)
    print(f"\nModel: {model_name}")
    print("\nThis will take 10-30 minutes depending on your hardware.")
    print("Progress will be shown below.\n")

    # Load dataset
    print("Loading ASRS dataset...")
    ds = load_dataset("elihoole/asrs-aviation-reports")
    work = ds["train"].to_list()
    print(f"Loaded {len(work)} reports\n")

    # Build index
    print(f"Building semantic index with {model_name}...")
    print("(Encoding ~47k chunks - grab a coffee ☕)\n")

    semantic_idx = SemanticIndex.build(
        work,
        model_name=model_name,
        chunk_size=250,
        overlap=50,
        batch_size=32,
        show_progress=True
    )

    # Save index
    output_path = Path(__file__).parent / "src" / "models" / "semantic_index.pkl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nSaving index to {output_path}...")
    semantic_idx.save(str(output_path))

    print("\n" + "=" * 80)
    print("✅ Success! Semantic index built and saved.")
    print("=" * 80)
    print(f"\nIndex location: {output_path}")
    print(f"Index size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"Chunks indexed: {semantic_idx.N}")
    print(f"Embedding dimension: {semantic_idx.embeddings.shape[1]}")
    print("\nYou can now run the FastAPI server with hybrid search enabled!")
    print("\nNext steps:")
    print("  1. Test the index: poetry run python -c \"from models import semantic_service; print('OK')\"")
    print("  2. Run evaluation: jupyter notebook src/notebooks/01_model_exploration.ipynb")
    print("  3. Start API: poetry run fastapi dev src/main.py")

if __name__ == "__main__":
    main()
