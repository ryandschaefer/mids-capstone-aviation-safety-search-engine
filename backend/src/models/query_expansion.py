"""
LLM-based query expansion for aviation safety search.
Calls a local Ollama instance to rewrite user queries using ASRS domain terminology.
"""

import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# --- Configuration defaults ---
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"
OLLAMA_TIMEOUT = 30.0  # seconds (first call is slow while model loads)
EXPANSION_ENABLED = True

EXPANSION_PROMPT = """You are an aviation safety domain expert familiar with NASA's ASRS (Aviation Safety Reporting System).
Rewrite the following user search query to improve retrieval from an ASRS incident report database.

Rules:
- Expand abbreviations and add standard aviation/ASRS terminology
- Include relevant synonyms used in ASRS reports
- Add related flight phases, aircraft components, or anomaly types where relevant
- Keep the rewritten query concise (under 50 words)
- Output ONLY the rewritten query, nothing else

Examples:
- "engine failure on takeoff" -> "engine failure power loss takeoff initial climb IFSD engine shutdown"
- "runway incursion" -> "runway incursion ground conflict taxiway crossing clearance deviation ground operations"
- "icing problems" -> "icing conditions airframe ice accumulation anti-ice deice system pitot static blockage"
- "near miss midair" -> "near midair collision NMAC TCAS RA traffic conflict airborne separation loss"
- "bird hit engine" -> "bird strike wildlife ingestion FOD engine damage compressor"
- "bad weather landing" -> "IMC approach wind shear low visibility ILS missed approach weather below minimums"

User query: {query}
Rewritten query:"""


def configure(
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
    enabled: Optional[bool] = None,
):
    """Update query expansion configuration at runtime."""
    global OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, EXPANSION_ENABLED
    if base_url is not None:
        OLLAMA_BASE_URL = base_url
    if model is not None:
        OLLAMA_MODEL = model
    if timeout is not None:
        OLLAMA_TIMEOUT = timeout
    if enabled is not None:
        EXPANSION_ENABLED = enabled


def expand_query(query: str, use_expansion: Optional[bool] = None) -> str:
    """
    Expand a user query using Ollama LLM.

    Args:
        query: Original user query
        use_expansion: Override the global EXPANSION_ENABLED flag.
                       True = force expand, False = skip, None = use global setting.

    Returns:
        Expanded query string, or the original query on failure.
    """
    should_expand = use_expansion if use_expansion is not None else EXPANSION_ENABLED
    if not should_expand:
        return query

    try:
        prompt = EXPANSION_PROMPT.format(query=query)

        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 80,
                    },
                },
            )
            response.raise_for_status()

        result = response.json()
        expanded = result.get("response", "").strip().strip('"')

        # Sanity checks
        if not expanded or len(expanded) < 3 or len(expanded) > 500:
            logger.warning("Query expansion returned invalid output, using original query")
            return query

        logger.info(f"Query expanded: '{query}' -> '{expanded}'")
        return expanded

    except httpx.ConnectError:
        logger.warning("Ollama not reachable, using original query")
        return query
    except httpx.TimeoutException:
        logger.warning("Ollama request timed out, using original query")
        return query
    except Exception as e:
        logger.warning(f"Query expansion failed: {e}, using original query")
        return query
