from dataclasses import dataclass
from typing import List

from ..llm.base import BaseLLM, ChatMessage


@dataclass
class RefineResult:
    refined: str
    variants: List[str]


class QueryRefiner:
    def __init__(self, llm: BaseLLM):
        self.llm = llm

    def refine(self, user_query: str) -> RefineResult:
        prompt = (
            "Rewrite the query as ASRS KEYWORDS ONLY.\n"
            "Rules:\n"
            "- keywords/phrases only, NO full sentences\n"
            "- expand abbreviations + add ASRS synonyms\n"
            "- keep ONE LINE\n"
            "- no explanation\n\n"
            f"Query: {user_query}\n"
            "Rewrite:"
        )

        resp = self.llm.chat([ChatMessage(role="user", content=prompt)])
        refined = self._sanitize_one_line(resp.content, fallback=user_query)
        return RefineResult(refined=refined, variants=[])

    @staticmethod
    def _sanitize_one_line(text: str, fallback: str) -> str:
        if not text:
            return fallback
        for line in text.splitlines():
            line = line.strip().strip('"')
            if not line:
                continue
            low = line.lower()
            if "explanation" in low:
                break
            for p in ("rewrite:", "rewritten query:", "query:"):
                if low.startswith(p):
                    line = line.split(":", 1)[-1].strip()
                    break
            return line[:300] if len(line) >= 3 else fallback
        return fallback