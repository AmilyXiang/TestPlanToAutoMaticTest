import re
import string
from typing import Dict


class StepNormalizer:
    """Normalizes raw test-step text into a canonical matching form."""

    def __init__(self) -> None:
        # Canonical replacements for common VoIP/phone terms.
        self.replacements: Dict[str, str] = {
            "short press": "press",
            "long-press": "long press",
            "longpress": "long press",
            "empty program key": "programmable key",
            "program key": "programmable key",
            "create key button": "create",
            "off hook": "offhook",
            "off-hook": "offhook",
            "on hook": "onhook",
            "on-hook": "onhook",
        }
        self._punct_table = str.maketrans("", "", string.punctuation)

    def normalize(self, text: str) -> str:
        """Lowercase, remove punctuation, collapse whitespace, and standardize phrases."""
        if text is None:
            return ""

        normalized = text.strip().lower()

        for src, dst in self.replacements.items():
            normalized = re.sub(rf"\b{re.escape(src)}\b", dst, normalized)

        normalized = normalized.translate(self._punct_table)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized
