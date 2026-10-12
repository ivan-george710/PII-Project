"""Document-scoped, exact-value tags."""
from collections import defaultdict


class Tagger:
    def __init__(self) -> None:
        self._counts = defaultdict(int)
        self._tags = {}

    def tag(self, entity_type: str, value: str) -> str:
        key = (entity_type, value)
        if key not in self._tags:
            self._counts[entity_type] += 1
            self._tags[key] = f"[{entity_type}_{self._counts[entity_type]:03d}]"
        return self._tags[key]
