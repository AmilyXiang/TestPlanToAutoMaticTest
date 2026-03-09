import json
import re
from itertools import product
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MatchResult:
    pattern_id: str
    action: str
    parameters: Dict[str, Any]
    match_text: str


class StepPatternMatcher:
    """Loads step patterns from JSON and matches normalized test steps."""

    def __init__(self, pattern_file: Path) -> None:
        self.pattern_file = pattern_file
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> List[Dict[str, Any]]:
        with self.pattern_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        patterns = data.get("patterns", [])
        # Higher priority patterns are matched first to avoid broad regex taking precedence.
        patterns.sort(key=lambda p: int(p.get("priority", 0)), reverse=True)
        for pattern in patterns:
            pattern["__compiled_regex"] = re.compile(pattern["regex"], flags=re.IGNORECASE)
        return patterns

    def _expand_or_variants(self, normalized_text: str) -> List[str]:
        """Create text variants for segments containing 'or' to improve matching coverage."""
        if " or " not in normalized_text:
            return [normalized_text]

        # Normalize separators so each phrase chunk can be expanded independently.
        chunks = [chunk.strip() for chunk in re.split(r"\s*,\s*", normalized_text) if chunk.strip()]
        expanded_chunks: List[List[str]] = []
        for chunk in chunks:
            # Split on standalone 'or' while preserving phrase pieces.
            options = [part.strip() for part in re.split(r"\bor\b", chunk) if part.strip()]
            if len(options) == 1:
                expanded_chunks.append([options[0]])
            else:
                expanded_chunks.append(options)

        variants = [" ".join(combo).strip() for combo in product(*expanded_chunks)]
        variants.append(normalized_text)
        return list(dict.fromkeys(v for v in variants if v))

    def match(self, normalized_text: str) -> Optional[MatchResult]:
        variants = self._expand_or_variants(normalized_text)

        for variant in variants:
            for pattern in self.patterns:
                m = pattern["__compiled_regex"].fullmatch(variant)
                if not m:
                    continue

                groups = m.groupdict()
                # Start from static defaults and let extracted groups override them.
                params = dict(pattern.get("static_parameters", {}))
                for output_name, source_name in pattern.get("parameter_mapping", {}).items():
                    params[output_name] = groups.get(source_name) if source_name else None

                return MatchResult(
                    pattern_id=pattern["pattern_id"],
                    action=pattern["action"],
                    parameters=params,
                    match_text=variant,
                )

        return None

    def add_pattern(self, pattern: Dict[str, Any]) -> None:
        pattern["__compiled_regex"] = re.compile(pattern["regex"], flags=re.IGNORECASE)
        self.patterns.append(pattern)
        self.patterns.sort(key=lambda p: int(p.get("priority", 0)), reverse=True)

        serializable = []
        for item in self.patterns:
            clean = {k: v for k, v in item.items() if not k.startswith("__")}
            serializable.append(clean)

        payload = {"patterns": serializable}
        with self.pattern_file.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
