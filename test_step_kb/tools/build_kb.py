import json
import importlib
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from parser.assertion_parser import ExpectedResultParser
from parser.step_parser import TestStepParser


class KnowledgeBaseBuilder:
    """Builds and updates the test-step knowledge base from raw step text."""

    def __init__(self, kb_dir: Path, enable_embeddings: bool = False) -> None:
        self.kb_dir = kb_dir
        self.dataset_path = kb_dir / "test_steps.json"
        self.parser = TestStepParser(kb_dir)
        self.assertion_parser = ExpectedResultParser(kb_dir)
        self.enable_embeddings = False
        self.model = None
        if enable_embeddings:
            self.model = self._build_embedding_model()
            self.enable_embeddings = self.model is not None

    def _build_embedding_model(self) -> Any:
        """Load optional embedding model only when requested and available."""
        try:
            module = importlib.import_module("sentence_transformers")
            model_cls = getattr(module, "SentenceTransformer")
            return model_cls("all-MiniLM-L6-v2")
        except Exception:
            return None

    def _load_dataset(self) -> Dict[str, Any]:
        with self.dataset_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save_dataset(self, payload: Dict[str, Any]) -> None:
        with self.dataset_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def build(self, steps: List[str]) -> Dict[str, Any]:
        pairs = [{"step_text": s, "expected_result": ""} for s in steps]
        return self.build_pairs(pairs)

    def build_pairs(self, step_result_pairs: List[Dict[str, str]]) -> Dict[str, Any]:
        dataset = self._load_dataset()
        action_counter = Counter(dataset.get("frequency", {}).get("actions", {}))
        pattern_counter = Counter(dataset.get("frequency", {}).get("patterns", {}))
        assertion_counter = Counter(dataset.get("frequency", {}).get("assertions", {}))
        assertion_pattern_counter = Counter(dataset.get("frequency", {}).get("assertion_patterns", {}))

        existing_steps = dataset.get("steps", [])
        start_index = len(existing_steps) + 1
        unknown_expressions: Counter[str] = Counter()
        unknown_assertions: Counter[str] = Counter()

        for offset, pair in enumerate(step_result_pairs):
            raw = pair.get("step_text", "")
            expected_raw = pair.get("expected_result", "")

            parsed = self.parser.parse(start_index + offset, raw)
            action_json = self.parser.to_action_schema_json(parsed)
            parsed_assertion = self.assertion_parser.parse(expected_raw)
            assertion_json = self.assertion_parser.to_assertion_schema_json(parsed_assertion)

            record = {
                "step": parsed.step,
                "original_text": parsed.original_text,
                "normalized_text": parsed.normalized_text,
                "matched_pattern_id": parsed.pattern_id,
                "parsed_action": action_json,
                "expected_result_text": expected_raw,
                "normalized_expected_result": parsed_assertion.normalized_text,
                "matched_assertion_pattern_id": parsed_assertion.pattern_id,
                "parsed_assertion": assertion_json,
            }

            if self.enable_embeddings and self.model is not None:
                vec = self.model.encode([parsed.normalized_text])[0]
                record["embedding"] = [float(x) for x in vec]

            existing_steps.append(record)
            action_counter[action_json["action"]] += 1
            if parsed.pattern_id:
                pattern_counter[parsed.pattern_id] += 1
            else:
                unknown_expressions[parsed.normalized_text] += 1

            assertion_counter[assertion_json["assertion"]] += 1
            if parsed_assertion.pattern_id:
                assertion_pattern_counter[parsed_assertion.pattern_id] += 1
            elif parsed_assertion.normalized_text:
                unknown_assertions[parsed_assertion.normalized_text] += 1

        total = len(existing_steps)
        unknown_total = int(action_counter.get("UNKNOWN", 0))
        unknown_assertion_total = int(assertion_counter.get("UNKNOWN_ASSERTION", 0))

        dataset["meta"] = {
            "version": dataset.get("meta", {}).get("version", "1.0"),
            "total_steps": total,
            "unknown_steps": unknown_total,
            "unknown_assertions": unknown_assertion_total,
        }
        dataset["frequency"] = {
            "actions": dict(action_counter),
            "patterns": dict(pattern_counter),
            "assertions": dict(assertion_counter),
            "assertion_patterns": dict(assertion_pattern_counter),
        }
        dataset["steps"] = existing_steps
        dataset["suggested_new_patterns"] = [
            {"expression": expr, "count": count}
            for expr, count in unknown_expressions.most_common()
        ]
        dataset["suggested_new_assertion_patterns"] = [
            {"expression": expr, "count": count}
            for expr, count in unknown_assertions.most_common()
        ]

        self._save_dataset(dataset)
        return {
            "total_steps": total,
            "unknown_steps": unknown_total,
            "new_unknown_candidates": len(dataset["suggested_new_patterns"]),
            "unknown_assertions": unknown_assertion_total,
            "new_unknown_assertion_candidates": len(dataset["suggested_new_assertion_patterns"]),
        }

    def add_pattern(self, pattern: Dict[str, Any]) -> None:
        self.parser.matcher.add_pattern(pattern)
