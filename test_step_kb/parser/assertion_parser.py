import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .normalizer import StepNormalizer


@dataclass
class ParsedAssertion:
    assertion: str
    parameters: Dict[str, Any]
    original_text: str
    normalized_text: str
    pattern_id: Optional[str]


class ExpectedResultParser:
    """Parses expected-result text into assertion schema JSON."""

    def __init__(self, kb_dir: Path) -> None:
        self.kb_dir = kb_dir
        self.normalizer = StepNormalizer()
        self.assertions_schema = self._load_json(kb_dir / "assertions.json")
        self.patterns = self._load_patterns(kb_dir / "assertion_patterns.json")

    def _load_json(self, path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _load_patterns(self, path: Path):
        data = self._load_json(path)
        patterns = data.get("patterns", [])
        patterns.sort(key=lambda p: int(p.get("priority", 0)), reverse=True)
        for p in patterns:
            p["__compiled_regex"] = re.compile(p["regex"], flags=re.IGNORECASE)
        return patterns

    def _compact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in params.items() if v is not None and not (isinstance(v, str) and not v.strip())}

    def parse(self, raw_text: str) -> ParsedAssertion:
        normalized = self.normalizer.normalize(raw_text)
        if not normalized:
            return ParsedAssertion(
                assertion="NO_ASSERTION",
                parameters={},
                original_text=raw_text,
                normalized_text=normalized,
                pattern_id=None,
            )

        valid_assertions = set(self.assertions_schema.get("assertion_enums", []))

        for pattern in self.patterns:
            m = pattern["__compiled_regex"].fullmatch(normalized)
            if not m:
                continue

            params = dict(pattern.get("static_parameters", {}))
            groups = m.groupdict()
            for output_name, source_name in pattern.get("parameter_mapping", {}).items():
                params[output_name] = groups.get(source_name) if source_name else None

            assertion = pattern.get("assertion", "UNKNOWN_ASSERTION")
            if assertion not in valid_assertions:
                assertion = "UNKNOWN_ASSERTION"

            return ParsedAssertion(
                assertion=assertion,
                parameters=self._compact(params),
                original_text=raw_text,
                normalized_text=normalized,
                pattern_id=pattern.get("pattern_id"),
            )

        return ParsedAssertion(
            assertion="UNKNOWN_ASSERTION",
            parameters={},
            original_text=raw_text,
            normalized_text=normalized,
            pattern_id=None,
        )

    def to_assertion_schema_json(self, parsed: ParsedAssertion) -> Dict[str, Any]:
        return {
            "assertion": parsed.assertion,
            "parameters": parsed.parameters,
        }
