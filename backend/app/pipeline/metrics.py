"""Deterministic one-to-one matching and PRF scores for an annotated benchmark."""

import re
import unicodedata

CATEGORIES = ("action", "population", "conditions", "direction", "numbers")


def normalize(value, category: str) -> str:
    if value is None:
        return ""
    value = unicodedata.normalize("NFKC", str(value)).casefold().strip()
    if category == "numbers":
        return " ".join(re.findall(r"(?<!\w)[+-]?\d+(?:[.,]\d+)?%?", value))
    return re.sub(r"[^\w]+", " ", value).strip()


def _maximum_matches(gold: list[dict], predicted: list[dict], category: str) -> int:
    """Maximum bipartite matching prevents one prediction scoring more than once."""
    adjacency = []
    for item in predicted:
        value = normalize(item.get(category), category)
        adjacency.append([
            i for i, target in enumerate(gold)
            if value and value == normalize(target.get(category), category)
        ])
    owner = {}

    def augment(pred_index, visited):
        for gold_index in adjacency[pred_index]:
            if gold_index in visited:
                continue
            visited.add(gold_index)
            if gold_index not in owner or augment(owner[gold_index], visited):
                owner[gold_index] = pred_index
                return True
        return False

    return sum(augment(i, set()) for i in range(len(predicted)))


def _scores(tp: int, predicted: int, gold: int) -> dict:
    precision = tp / predicted if predicted else 0.0
    recall = tp / gold if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "predicted": predicted, "gold": gold,
            "precision": precision, "recall": recall, "f1": f1}


def evaluate(gold: list[dict], predicted: list[dict]) -> dict:
    """Score exact normalized field matches per category and all-field matches overall."""
    metrics = {
        category: _scores(
            _maximum_matches(gold, predicted, category),
            sum(bool(normalize(item.get(category), category)) for item in predicted),
            sum(bool(normalize(item.get(category), category)) for item in gold),
        )
        for category in CATEGORIES
    }

    # A whole claim matches only when every supplied evaluation field matches.
    exact_predicted = [item for item in predicted if all(normalize(item.get(k), k) for k in CATEGORIES)]
    exact_gold = [item for item in gold if all(normalize(item.get(k), k) for k in CATEGORIES)]
    # Reuse the same one-to-one matcher with a composite field.
    composite_gold = [{"all": "|".join(normalize(x.get(k), k) for k in CATEGORIES)} for x in exact_gold]
    composite_pred = [{"all": "|".join(normalize(x.get(k), k) for k in CATEGORIES)} for x in exact_predicted]
    exact_tp = _maximum_matches(composite_gold, composite_pred, "all")
    metrics["overall"] = _scores(exact_tp, len(exact_predicted), len(exact_gold))
    return {"matching": "exact normalized values; maximum one-to-one bipartite matching",
            "categories": metrics}
