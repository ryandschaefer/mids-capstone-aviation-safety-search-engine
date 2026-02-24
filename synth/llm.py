import json
import os
import time
from openai import OpenAI


class LLMQueryGenerator:
    def __init__(self, cfg):
        self.cfg = cfg
        key = os.environ.get(cfg.api_key_env)
        if not key:
            raise RuntimeError(f"Missing env var: {cfg.api_key_env}")
        self.client = OpenAI(api_key=key)

    def schema(self):
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "queries": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "query": {"type": "string"},
                            "style": {"type": "string", "enum": ["keyword", "question", "natural"]},
                            "used_fields": {"type": "array", "items": {"type": "string"}},
                            "facets": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "airport": {"type": "string"},
                                    "state": {"type": "string"},
                                    "aircraft": {"type": "string"},
                                    "anomaly": {"type": "string"},
                                    "phase": {"type": "string"},
                                    "year": {"type": "string"},
                                },
                                "required": ["airport", "state", "aircraft", "anomaly", "phase", "year"],
                            },
                        },
                        "required": ["query", "style", "used_fields", "facets"],
                    },
                }
            },
            "required": ["queries"],
        }

    def _prompt(self, record_json, n):
        sys = (
            "You generate realistic Google-style search queries for aviation incident reports. "
            "Use any useful fields from the record, including curated metadata (location, state, aircraft model, phase, anomalies, etc.). "
            "Queries should be short, specific, and natural; do not copy long passages. "
            "You MUST output facets with ALL keys (airport, state, aircraft, anomaly, phase, year). "
            "If unknown, set the value to an empty string ''."
        )

        user = (
            f"Generate {n} distinct search queries that a user might type.\n"
            f"Return JSON matching the schema.\n"
            f"Record JSON:\n{record_json}"
        )
        return sys, user

    def generate(self, record_json, n):
        sys, user = self._prompt(record_json, n)
        resp = self.client.responses.create(
            model=self.cfg.openai_model,
            input=[
                {"role": "system", "content": sys},
                {"role": "user", "content": user},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "asrs_google_query_gen",
                    "schema": self.schema(),
                    "strict": True,
                }
            },
        )
        data = json.loads(resp.output_text)
        return data["queries"]

    def build_batch_requests(self, items):
        reqs = []
        schema = self.schema()

        for cache_key, record_json, n in items:
            sys, user = self._prompt(record_json, n)
            body = {
                "model": self.cfg.openai_model,
                "input": [
                    {"role": "system", "content": sys},
                    {"role": "user", "content": user},
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "asrs_google_query_gen",
                        "schema": schema,
                        "strict": True,
                    }
                },
            }

            reqs.append({
                "custom_id": cache_key,
                "method": "POST",
                "url": "/v1/responses",
                "body": body,
            })

        return reqs

    def run_batch_and_collect(self, reqs):
        in_path = "openai_batch_input.jsonl"
        with open(in_path, "w", encoding="utf-8") as f:
            for r in reqs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        file_obj = self.client.files.create(file=open(in_path, "rb"), purpose="batch")

        batch = self.client.batches.create(
            input_file_id=file_obj.id,
            endpoint="/v1/responses",
            completion_window=self.cfg.batch_completion_window,
        )

        while True:
            b = self.client.batches.retrieve(batch.id)
            if b.status in ("completed", "failed", "cancelled", "expired"):
                batch = b
                break
            time.sleep(self.cfg.batch_poll_seconds)

        if batch.status != "completed":
            raise RuntimeError(f"Batch did not complete: status={batch.status}")

        out_file_id = batch.output_file_id
        content = self.client.files.content(out_file_id).read().decode("utf-8")

        out = {}
        for line in content.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)

            custom_id = obj.get("custom_id")
            if not custom_id:
                continue

            resp = obj.get("response", {})
            out_text = resp.get("output_text", "")
            if not out_text:
                continue

            data = json.loads(out_text)
            out[custom_id] = data.get("queries", [])

        return out