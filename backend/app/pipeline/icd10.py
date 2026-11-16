"""Offline ICD-10 lookup from the supplied registry JSON snapshot."""

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_index() -> dict[str, dict]:
    path = Path(__file__).parent.parent / "spec" / "icd10.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["code"].upper(): item for item in data["items"]}


def validate_codes(codes: list[str]) -> list[str]:
    index = load_index()
    normalized = [code.strip().upper() for code in codes if code.strip()]
    unknown = sorted(set(normalized) - index.keys())
    if unknown:
        raise ValueError("Неизвестные коды МКБ-10: " + ", ".join(unknown))
    return list(dict.fromkeys(normalized))


def search_codes(query: str, limit: int = 20, active_only: bool = True) -> list[dict]:
    query = query.strip().casefold()
    if not query:
        return []
    results = []
    for item in load_index().values():
        if active_only and not item["active"]:
            continue
        if query in item["code"].casefold() or query in item["name"].casefold():
            results.append(item)
            if len(results) >= limit:
                break
    return results
