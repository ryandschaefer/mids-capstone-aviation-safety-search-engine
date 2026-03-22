"""
LLM-based query expansion for aviation safety search.
Calls a local Ollama instance to rewrite user queries using ASRS domain terminology.
Includes an LLM judge step to filter out irrelevant expanded terms.
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

# ASRS anomaly category names used to ground the prompt in real data vocabulary.
# Top 20 by frequency from ASRS dataset (38,655 reports).
_ASRS_TOP_ANOMALIES = """
- Deviation / Discrepancy - Procedural Published Material / Policy
- ATC Issue All Types
- Deviation / Discrepancy - Procedural Clearance
- Aircraft Equipment Problem Less Severe
- Aircraft Equipment Problem Critical
- Inflight Event / Encounter Weather / Turbulence
- Deviation - Track / Heading All Types
- Deviation / Discrepancy - Procedural FAR
- Conflict Airborne Conflict
- Conflict NMAC
- Inflight Event / Encounter CFTT / CFIT
- Deviation - Altitude Excursion From Assigned Altitude
- Flight Deck / Cabin / Aircraft Event Smoke / Fire / Fumes / Odor
- Conflict Ground Conflict
- Airspace Violation All Types
- Ground Event / Encounter Other / Unknown
- Deviation - Speed All Types
- Deviation / Discrepancy - Procedural Maintenance
- Inflight Event / Encounter Fuel Issue
- Inflight Event / Encounter Unstabilized Approach
"""

EXPANSION_PROMPT = """You are an aviation safety retrieval expert specializing in NASA ASRS (Aviation Safety Reporting System) incident reports.

ASRS reports are pilot/controller narratives describing real incidents. The database uses these anomaly categories:
{anomaly_list}

Your task: Given a user search query, expand it with synonyms and ASRS-specific terms to improve recall. ONLY add terms that are directly implied by the query topic.

Rules:
1. Keep ALL words from the original query
2. Add standard aviation abbreviations only when directly relevant (IFSD, NMAC, TCAS RA, CFIT, IMC, VMC, FOD, MEL)
3. Add synonyms or closely related ASRS anomaly terms — only for the specific topic in the query
4. Do NOT add unrelated concepts, even if they are common in aviation
5. Output ONLY space-separated terms — no punctuation, no explanation

Examples:
Original: policy deviation
Expanded: policy deviation procedural non-compliance published material regulatory deviation SOP

Original: atc instruction issue
Expanded: ATC instruction issue communication error clearance readback controller pilot

Original: clearance deviation
Expanded: clearance deviation ATC clearance violation flight path deviation separation

Original: equipment malfunction
Expanded: equipment malfunction aircraft component failure system anomaly mechanical failure MEL

Original: critical equipment failure
Expanded: critical equipment failure aircraft system failure emergency in-flight malfunction

Original: severe turbulence
Expanded: severe turbulence inflight encounter weather convective turbulence wake vortex

Original: near midair collision
Expanded: near midair collision NMAC TCAS RA airborne conflict traffic separation loss

Original: controlled flight into terrain
Expanded: controlled flight into terrain CFIT GPWS terrain conflict descent IMC

Original: smoke in cockpit
Expanded: smoke cockpit fire fumes odor flight deck aircraft event

Original: airspace violation
Expanded: airspace violation flight path deviation unauthorized operation restricted airspace

Original: fuel emergency
Expanded: fuel exhaustion fuel starvation in-flight fuel emergency low fuel reserves fuel imbalance

Original: unstabilized approach
Expanded: unstabilized approach flight path deviation descent rate go-around missed approach

Original: {query}
Expanded:""".format(anomaly_list=_ASRS_TOP_ANOMALIES, query="{query}")

JUDGE_PROMPT = """You are an aviation safety retrieval expert reviewing query expansion results.

Original query: "{original}"
Expanded query terms: "{expanded}"

Review each term in the expanded query. Keep a term only if it is:
- A word from the original query, OR
- A direct synonym, standard abbreviation, or closely related ASRS term for the original query's specific topic

Remove any term that introduces a concept not present or clearly implied in the original query.

Output ONLY the filtered terms as space-separated words — no explanation, no punctuation."""


def _call_ollama(prompt: str, num_predict: int = 80) -> str:
    """Make a single Ollama API call and return the response text."""
    with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
        response = client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": num_predict,
                },
            },
        )
        response.raise_for_status()
    return response.json().get("response", "").strip().strip('"')


def _judge_expansion(original: str, expanded: str) -> str:
    """
    Use LLM to filter out irrelevant terms from the expanded query.
    Returns the filtered expansion, or the original query on failure.
    """
    prompt = JUDGE_PROMPT.format(original=original, expanded=expanded)
    try:
        filtered = _call_ollama(prompt, num_predict=100)
        # Take first line only (guard against model continuing with explanations)
        filtered = filtered.splitlines()[0].strip().strip('"')
        if not filtered or len(filtered) < len(original) * 0.5:
            # Judge produced something too short — original terms likely stripped; fall back
            logger.warning("Judge output too short, using unfiltered expansion")
            return expanded
        logger.info(f"Judge filtered: '{expanded}' -> '{filtered}'")
        return filtered
    except Exception as e:
        logger.warning(f"Judge step failed: {e}, using unfiltered expansion")
        return expanded


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


def expand_query(query: str, use_expansion: Optional[bool] = None, use_judge: bool = True) -> str:
    """
    Expand a user query using Ollama LLM, then filter with an LLM judge.

    Args:
        query: Original user query
        use_expansion: Override the global EXPANSION_ENABLED flag.
                       True = force expand, False = skip, None = use global setting.
        use_judge: Whether to run the judge step to filter irrelevant terms (default True).

    Returns:
        Expanded (and optionally judged) query string, or the original query on failure.
    """
    should_expand = use_expansion if use_expansion is not None else EXPANSION_ENABLED
    if not should_expand:
        return query

    try:
        prompt = EXPANSION_PROMPT.format(query=query)
        expanded = _call_ollama(prompt, num_predict=80)
        # Take only first line — guard against model hallucinating more Input:/Output: pairs
        expanded = expanded.splitlines()[0].strip().strip('"')

        if not expanded or len(expanded) < 3 or len(expanded) > 500:
            logger.warning("Query expansion returned invalid output, using original query")
            return query

        logger.info(f"Query expanded: '{query}' -> '{expanded}'")

        if use_judge:
            expanded = _judge_expansion(query, expanded)

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
