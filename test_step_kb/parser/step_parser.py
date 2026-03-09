import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .normalizer import StepNormalizer
from .pattern_matcher import MatchResult, StepPatternMatcher


@dataclass
class ParsedStep:
    step: int
    action: str
    parameters: Dict[str, Any]
    original_text: str
    normalized_text: str
    pattern_id: Optional[str]


class TestStepParser:
    """Pipeline: normalize -> pattern match -> parameter extraction -> action schema."""

    def __init__(self, kb_dir: Path) -> None:
        self.kb_dir = kb_dir
        self.normalizer = StepNormalizer()
        self.matcher = StepPatternMatcher(kb_dir / "step_patterns.json")
        self.actions_schema = self._load_actions_schema(kb_dir / "actions.json")

    def _load_actions_schema(self, actions_file: Path) -> Dict[str, Any]:
        with actions_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _compact_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Keep only meaningful parameters; drop null/empty placeholders."""
        compact: Dict[str, Any] = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if key == "seconds" and isinstance(value, str) and value.isdigit():
                compact[key] = int(value)
                continue
            compact[key] = value
        return compact

    def parse(self, step_number: int, raw_text: str) -> ParsedStep:
        normalized = self.normalizer.normalize(raw_text)
        match: Optional[MatchResult] = self.matcher.match(normalized)

        if not match:
            # Unknown expressions can be reviewed and promoted into new patterns.
            return ParsedStep(
                step=step_number,
                action="UNKNOWN",
                parameters={},
                original_text=raw_text,
                normalized_text=normalized,
                pattern_id=None,
            )

        action = match.action
        valid_actions = set(self.actions_schema.get("action_enums", []))
        if action not in valid_actions:
            action = "UNKNOWN"

        compact_params = self._compact_parameters(match.parameters)

        return ParsedStep(
            step=step_number,
            action=action,
            parameters=compact_params,
            original_text=raw_text,
            normalized_text=normalized,
            pattern_id=match.pattern_id,
        )

    def to_action_schema_json(self, parsed: ParsedStep) -> Dict[str, Any]:
        return {
            "step": parsed.step,
            "action": parsed.action,
            "parameters": parsed.parameters,
        }
