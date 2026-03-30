import aioboto3
import json
from fastapi import HTTPException
import os

client_config = {
    "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_BEDROCK"),
    "aws_secret_access_key": os.environ.get("AWS_SECRET_KEY_BEDROCK"),
    "region_name": os.environ.get("AWS_REGION_BEDROCK"),
}
session = aioboto3.Session(**client_config)

async def run_llm(prompt: str, max_tokens: int = 100) -> str:
    # Configure LLM inputs
    payload = {
        "messages": [{
            "role": "user",
            "content": [{
                "text": prompt
            }]
        }],
        "inferenceConfig": {
            "maxTokens": max_tokens
        },
    }
    print("LLM payload:")
    print(json.dumps(payload, indent = 4))
    
    try:
        # Generate response from bedrock
        async with session.client("bedrock-runtime") as bedrock_client:
            response = await bedrock_client.invoke_model(
                modelId="us.amazon.nova-pro-v1:0",
                body=json.dumps(payload),
                contentType="application/json",
                accept="application/json",
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Bedrock error: {e}")
    
    # Extract generated text from bedrock response
    body = json.loads(await response["body"].read())
    text = body["output"]["message"]["content"][0]["text"]
    
    return text

async def query_expansion_judge(original_query: str, expanded_query: str) -> str:
    # Prompt template for LLM judge of query expansion
    _judge_prompt_template = """\
    You are an aviation safety retrieval expert reviewing query expansion results.

    Original query: "{original}"
    Expanded query terms: "{expanded}"

    Keep a term only if it is a word from the original query, or a direct synonym, abbreviation, or closely related ASRS term for the original query's topic.
    Remove any term that introduces a concept not present or clearly implied in the original query.

    Output ONLY the filtered terms as space-separated words — no explanation."""
    
    # Fill in prompt template with old and new queries
    prompt = _judge_prompt_template.format(original=original_query, expanded=expanded_query)
    
    # Get new query from Bedrock
    qe_judge_raw = await run_llm(prompt)
    # Take only the first line (guard against model hallucinating more Input:/Output: pairs)
    new_query = qe_judge_raw.strip().splitlines()[0].strip().strip('"')
    
    # Only use new filtered query if it isn't too short
    if new_query and len(new_query) >= len(original_query) * 0.5:
        return new_query
    
    return expanded_query

async def query_expansion(query: str, use_judge: bool = False) -> str:
    # ASRS anomaly categories used to ground the prompt in real data vocabulary.
    _ASRS_ANOMALY_CONTEXT = """
    Common ASRS anomaly categories:
    - Deviation / Discrepancy - Procedural Published Material / Policy
    - ATC Issue All Types
    - Deviation / Discrepancy - Procedural Clearance
    - Aircraft Equipment Problem Less Severe / Critical
    - Inflight Event / Encounter Weather / Turbulence
    - Conflict Airborne Conflict / NMAC / Ground Conflict
    - Inflight Event / Encounter CFTT / CFIT
    - Deviation - Altitude Excursion / Overshoot / Undershoot / Crossing Restriction
    - Airspace Violation All Types
    - Inflight Event / Encounter Fuel Issue / Unstabilized Approach / Loss Of Aircraft Control
    """

    # Prompt template for query expansion
    _QE_PROMPT_TEMPLATE = """\
    You are an aviation safety retrieval expert specializing in NASA ASRS incident reports.

    {anomaly_context}
    Task: Expand the search query with synonyms and ASRS-specific terms to improve recall.
    Only add terms directly implied by the query topic. Keep ALL original words.
    Output ONLY space-separated terms — no punctuation, no explanation.

    Input: policy deviation
    Output: policy deviation procedural non-compliance published material regulatory deviation SOP

    Input: atc instruction issue
    Output: ATC instruction issue communication error clearance readback controller pilot

    Input: near midair collision
    Output: near midair collision NMAC TCAS RA airborne conflict traffic separation loss

    Input: controlled flight into terrain
    Output: controlled flight into terrain CFIT GPWS terrain conflict descent IMC

    Input: fuel emergency
    Output: fuel exhaustion fuel starvation in-flight fuel emergency low fuel reserves fuel imbalance

    Input: {query}
    Output:""".format(anomaly_context=_ASRS_ANOMALY_CONTEXT, query="{query}")
    
    # Fill in prompt template with current query
    prompt = _QE_PROMPT_TEMPLATE.format(query=query)
    
    # Get new query from Bedrock
    qe_raw = await run_llm(prompt)
    # Take only the first line (guard against model hallucinating more Input:/Output: pairs)
    query_expanded = qe_raw.strip().splitlines()[0].strip().strip('"')
    
    # Check if LLM as a judge should be used on the expanded query
    if use_judge:
        query_expanded = await query_expansion_judge(query, query_expanded)
        
    return query_expanded
