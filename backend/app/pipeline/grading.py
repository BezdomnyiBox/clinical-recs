"""Детерминированные правила УДД/УУР (приказ 103н, шкалы 1-3) и проверки тезиса. Модель их не решает."""

from app.models import SECTIONS

SCALE_BY_TYPE = {
    "diagnostic": "udd_diagnostic",
    "therapeutic": "udd_treatment",
    "preventive": "udd_treatment",
    "rehab": "udd_treatment",
}

# дизайн источника -> УДД, по таблицам из семинара ЦЭККМП
UDD_BY_DESIGN = {
    "udd_treatment": {
        "meta_analysis_rct": 1,
        "systematic_review_rct": 2,
        "rct": 2,
        "meta_analysis_non_rct": 2,
        "systematic_review_non_rct": 3,
        "cohort": 3,
        "case_control": 4,
        "non_comparative": 4,
        "case_series": 4,
        "case_report": 4,
        "narrative_review": 5,
        "expert_opinion": 5,
    },
    "udd_diagnostic": {
        "meta_analysis_diagnostic": 1,
        "diagnostic_with_reference": 2,
        "rct": 2,
        "meta_analysis_non_rct": 2,
        "diagnostic_without_reference": 3,
        "cohort": 3,
        "systematic_review_non_rct": 3,
        "non_comparative": 4,
        "case_series": 4,
        "case_report": 4,
        "narrative_review": 5,
        "expert_opinion": 5,
    },
}

# ДОПУЩЕНИЕ: приказ не задаёт выбор формулировки, схема лишь требует детерминированности. Сверить с экспертом.
STRENGTH = {
    ("positive", "A"): "Рекомендуется",
    ("positive", "B"): "Рекомендуется",
    ("positive", "C"): "Рекомендуется рассмотреть возможность",
    ("negative", "A"): "Не рекомендуется",
    ("negative", "B"): "Не рекомендуется",
    ("negative", "C"): "Не рекомендуется рассматривать",
}
PHRASES = ("Рекомендуется", "Не рекомендуется")
THESIS_SECTIONS = {k for k in SECTIONS if k.startswith(("2.", "3.")) or k in ("4", "5")}


def udd_for_source(
    study_design: str | None, intervention_type: str | None
) -> int | None:
    scale = SCALE_BY_TYPE.get(intervention_type or "")
    if scale is None or study_design is None:
        return None
    return UDD_BY_DESIGN[scale].get(study_design)


def aggregate_udd(udds: list[int | None]) -> int | None:
    vals = [u for u in udds if u]
    return (
        min(vals) if vals else None
    )  # лучший из согласованных; согласованность проверяется отдельно


def validate_thesis(t: dict) -> list[str]:
    """Нарушения, которые эксперт должен увидеть. Пустой список - формальных замечаний нет."""
    p = []
    if t.get("section") not in THESIS_SECTIONS:
        p.append("тезисы-рекомендации размещаются только в разделах 2-5")
    if not (t.get("text") or "").startswith(PHRASES):
        p.append(
            "формулировка должна начинаться с «Рекомендуется» или «Не рекомендуется»"
        )
    if t.get("provenance") != "manual" and not t.get("card_ids"):
        p.append("нет ссылок на источники")
    udd, uur = t.get("udd"), t.get("uur")
    if udd is None or uur is None:
        p.append("УДД и УУР не определены")
    elif udd >= 4 and uur != "C":
        p.append("при УДД 4-5 допустим только УУР C")
    if not t.get("grade_rationale"):
        p.append("нет обоснования УДД/УУР")
    return p
