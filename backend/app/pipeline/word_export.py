"""Fill the supplied Ministry clinical-recommendation DOCX template in place."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from io import BytesIO
from pathlib import Path
import re
import zipfile

import lxml.etree as etree

from app.models import Document, Project, Thesis
from app.pipeline.icd10 import load_index

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
W = lambda local: f"{{{WORD_NS}}}{local}"
TEMPLATE = Path(__file__).parent.parent / "spec" / "kr_template_2026.docx"
TEMPLATE_SHA256 = "a2f9664d4317e359a47f7c8e922c872ea68e4c219f4e95dfea6860df90be51e1"

RECOMMENDATION_SLOTS = {
    "2": (77, 78, 79),
    "2.1": (84, 85, 86),
    "2.2": (90, 91, 92),
    "2.3": (96, 97, 98),
    "2.4": (101, 102, 103),
    "2.5": (106, 107, 108),
    "3.1": (115, 116, 117),
    "3.2": (120, 121, 122),
    "3.3": (125, 126, 127),
    "4": (130, 131, 132),
    "5": (135, 136, 137),
}
GUIDANCE_TABLES = set(range(1, 21)) | set(range(23, 27)) | set(range(30, 34))
RECOMMENDATION_PHRASES = (
    "Не рекомендуется рассматривать",
    "Рекомендуется рассмотреть возможность",
    "Не рекомендуется",
    "Рекомендуется",
)


def _text(element) -> str:
    return "".join(element.itertext()).strip()


def _run_props(paragraph, *, bold: bool | None = None):
    runs = paragraph.findall(W("r"))
    for run in runs:
        props = run.find(W("rPr"))
        is_bold = props is not None and props.find(W("b")) is not None
        if bold is None or is_bold == bold:
            return deepcopy(props) if props is not None else None
    if runs:
        props = runs[0].find(W("rPr"))
        return deepcopy(props) if props is not None else None
    return None


def _run(text: str, props=None):
    run = etree.Element(W("r"))
    if props is not None:
        run.append(props)
    node = etree.SubElement(run, W("t"))
    if text[:1].isspace() or text[-1:].isspace() or "  " in text:
        node.set(f"{{{XML_NS}}}space", "preserve")
    node.text = text
    return run


def _set_paragraph(paragraph, chunks: list[tuple[str, bool | None]]) -> None:
    """Replace paragraph text while preserving paragraph properties and run roles."""
    default = _run_props(paragraph)
    regular = _run_props(paragraph, bold=False)
    bold = _run_props(paragraph, bold=True)
    ppr = paragraph.find(W("pPr"))
    for child in list(paragraph):
        if child is not ppr:
            paragraph.remove(child)
    for value, use_bold in chunks:
        if not value:
            continue
        props = bold if use_bold is True else regular if use_bold is False else default
        paragraph.append(_run(value, deepcopy(props) if props is not None else None))


def _set_plain_paragraph(paragraph, value: str) -> None:
    _set_paragraph(paragraph, [(value, None)])


def _clone_paragraph(paragraph, chunks: list[tuple[str, bool | None]]):
    clone = etree.Element(W("p"))
    ppr = paragraph.find(W("pPr"))
    if ppr is not None:
        clone.append(deepcopy(ppr))
    default = _run_props(paragraph)
    regular = _run_props(paragraph, bold=False)
    bold = _run_props(paragraph, bold=True)
    for value, use_bold in chunks:
        if not value:
            continue
        props = bold if use_bold is True else regular if use_bold is False else default
        clone.append(_run(value, deepcopy(props) if props is not None else None))
    return clone


def _cell_text(cell, value: str) -> None:
    paragraphs = cell.findall(W("p"))
    if paragraphs:
        _set_plain_paragraph(paragraphs[0], value)
        for paragraph in paragraphs[1:]:
            _set_plain_paragraph(paragraph, "")
    else:
        paragraph = etree.SubElement(cell, W("p"))
        _set_plain_paragraph(paragraph, value)


def _age_label(age_group: str | None) -> str:
    return {
        "adults": "взрослые",
        "children": "дети",
        "mixed": "взрослые и дети",
    }.get(age_group or "", age_group or "")


def _icd_label(code: str) -> str:
    item = load_index().get(code.strip().upper())
    return f"{code} — {item['name']}" if item else code


def _cover(document_xml, project: Project) -> None:
    body = document_xml.find(f".//{W('body')}")
    tables = body.findall(W("tbl"))
    cover_rows = tables[0].findall(W("tr"))

    # The disease-name row is a merged cell; its first cell is the editable slot.
    _cell_text(cover_rows[1].findall(W("tc"))[0], project.title)

    codes = [_icd_label(code) for code in (project.icd_codes or [])]
    if codes:
        cells = cover_rows[2].findall(W("tc"))
        _cell_text(cells[-1], "; ".join(codes))
    if project.age_group:
        cells = cover_rows[3].findall(W("tc"))
        _cell_text(cells[-1], _age_label(project.age_group))

    # The template asks for developer organizations as bullets. A semicolon-
    # separated project value can fill multiple bullets without inventing names.
    orgs = [part.strip() for part in re.split(r"[;\n]+", project.organization or "") if part.strip()]
    if orgs:
        orgs = orgs[:2] + (["; ".join(orgs[2:])] if len(orgs) > 2 else [])
        org_cell = cover_rows[6].findall(W("tc"))[0]
        paragraphs = org_cell.findall(W("p"))
        for index, paragraph in enumerate(paragraphs[:3]):
            if index < len(orgs):
                _set_plain_paragraph(paragraph, orgs[index])
            else:
                _set_plain_paragraph(paragraph, "")
                ppr = paragraph.find(W("pPr"))
                numpr = ppr.find(W("numPr")) if ppr is not None else None
                if numpr is not None:
                    ppr.remove(numpr)


def _recommendation_chunks(thesis: Thesis, citations: list[int]) -> list[tuple[str, bool | None]]:
    text = (thesis.text or "").strip()
    phrase = next((p for p in RECOMMENDATION_PHRASES if text.startswith(p)), None)
    suffix = "".join(f" [{citation}]" for citation in citations)
    if phrase:
        return [(phrase, True), (text[len(phrase):] + suffix, False)]
    return [(text + suffix, False)]


def _provenance(thesis: Thesis) -> str:
    return {
        "auto": "сформировано системой, требуется экспертное подтверждение",
        "auto+expert_review": "сформировано системой и отредактировано экспертом",
        "manual": "добавлено экспертом",
    }.get(thesis.provenance or "", "происхождение не указано")


def _grade_text(thesis: Thesis) -> str:
    uur = thesis.uur or "не определён"
    udd = thesis.udd if thesis.udd is not None else "не определён"
    return f"Уровень убедительности рекомендаций {uur} (уровень достоверности доказательств – {udd})"


def _comment_chunks(thesis: Thesis, cards: list) -> list[tuple[str, bool | None]]:
    details = [part.strip() for part in (thesis.comment, thesis.grade_rationale) if part and part.strip()]
    if cards:
        ids = ", ".join(f"ev_{card.id} (стр. {card.page_number})" for card in cards)
        details.append("Карточки источников: " + ids)
    details.append("Происхождение: " + _provenance(thesis))
    return [("Комментарии:", None), (" " + "; ".join(details), False)]


def _fill_recommendations(paragraphs, theses: list[Thesis], citation_numbers: dict[int, int]) -> None:
    groups: dict[str, list[Thesis]] = {}
    for thesis in theses:
        if thesis.review_status == "rejected":
            continue
        groups.setdefault(thesis.section, []).append(thesis)

    for section, (recommendation_index, grade_index, comment_index) in RECOMMENDATION_SLOTS.items():
        group = sorted(groups.get(section, []), key=lambda item: item.id)
        if not group:
            continue
        recommendation, grade, comment = (paragraphs[i] for i in (recommendation_index, grade_index, comment_index))
        source_templates = (deepcopy(recommendation), deepcopy(grade), deepcopy(comment))
        cursor = comment
        for index, thesis in enumerate(group):
            cards = sorted(thesis.cards, key=lambda card: card.id)
            citations = sorted({citation_numbers[card.document_id] for card in cards if card.document_id in citation_numbers})
            if index == 0:
                rec_node, grade_node, comment_node = recommendation, grade, comment
                _set_paragraph(rec_node, _recommendation_chunks(thesis, citations))
                _set_plain_paragraph(grade_node, _grade_text(thesis))
                _set_paragraph(comment_node, _comment_chunks(thesis, cards))
            else:
                rec_node = _clone_paragraph(source_templates[0], _recommendation_chunks(thesis, citations))
                grade_node = _clone_paragraph(source_templates[1], [(_grade_text(thesis), None)])
                comment_node = _clone_paragraph(source_templates[2], _comment_chunks(thesis, cards))
                for node in (rec_node, grade_node, comment_node):
                    cursor.addnext(node)
                    cursor = node

    # Rename the two generic treatment headings only when the project has a thesis there.
    section_heads = {"3.2": (118, "Хирургическое лечение"), "3.3": (123, "Иное лечение")}
    for section, (index, default_title) in section_heads.items():
        group = groups.get(section, [])
        if group:
            title = next((item.subsection_title for item in group if item.subsection_title), default_title)
            _set_plain_paragraph(paragraphs[index], f"{section} {title}")


def _format_reference(source: Document) -> str:
    data = source.biblio or {}
    parts = []
    authors = data.get("authors") or []
    if authors:
        parts.append(", ".join(str(author).strip() for author in authors if str(author).strip()))
    if data.get("title"):
        parts.append(str(data["title"]).strip())
    if data.get("journal"):
        parts.append(str(data["journal"]).strip())
    if data.get("year"):
        parts.append(str(data["year"]))
    if data.get("doi"):
        parts.append("DOI: " + str(data["doi"]))
    if data.get("pmid"):
        parts.append("PMID: " + str(data["pmid"]))
    if not parts:
        parts.append(source.filename)
    return ". ".join(parts).rstrip(".") + "."


def _fill_references(body, theses: list[Thesis], sources_by_id: dict[int, Document], citation_numbers: dict[int, int]) -> None:
    paragraphs = body.findall(W("p"))
    heading_index = next((i for i, p in enumerate(paragraphs) if _text(p) == "Список литературы"), None)
    next_heading_index = next((i for i, p in enumerate(paragraphs) if _text(p).startswith("Приложение А1.")), None)
    if heading_index is None or next_heading_index is None:
        return
    slots = [
        p for p in paragraphs[heading_index + 1:next_heading_index]
        if _text(p) == "….." and p.find(f"{W('pPr')}/{W('pStyle')}") is not None
    ]
    used_doc_ids = sorted(citation_numbers, key=lambda doc_id: citation_numbers[doc_id])
    references = [_format_reference(sources_by_id[doc_id]) for doc_id in used_doc_ids if doc_id in sources_by_id]
    while len(slots) < len(references) and slots:
        clone = _clone_paragraph(slots[-1], [("", None)])
        slots[-1].addnext(clone)
        slots.append(clone)
    for index, slot in enumerate(slots):
        if index < len(references):
            _set_plain_paragraph(slot, references[index])
        else:
            parent = slot.getparent()
            if parent is not None:
                parent.remove(slot)


def _fill_quality_criteria(tables, theses: list[Thesis]) -> None:
    table = tables[22]
    criteria = []
    for thesis in theses:
        data = thesis.quality_criterion or {}
        text = data.get("criterion_text") if data.get("is_criterion") else None
        if text and str(text).strip():
            cards = ", ".join(f"ev_{card.id}" for card in sorted(thesis.cards, key=lambda card: card.id))
            link = f" [тезис {thesis.section}" + (f"; карточки {cards}" if cards else "") + "]"
            criteria.append(str(text).strip() + link)
    rows = table.findall(W("tr"))
    while len(rows) < len(criteria):
        clone = deepcopy(rows[-1])
        table.append(clone)
        rows.append(clone)
    for row, criterion in zip(rows, criteria):
        cells = row.findall(W("tc"))
        _cell_text(cells[1], criterion)


def _fill_icd_section(paragraphs, project: Project) -> None:
    codes = [_icd_label(code) for code in (project.icd_codes or [])]
    if codes:
        _set_plain_paragraph(paragraphs[64], "Кодирование по МКБ-10: " + "; ".join(codes) + ".")


def _remove_author_guidance_tables(body, tables) -> None:
    for index in sorted(GUIDANCE_TABLES, reverse=True):
        if index < len(tables):
            node = tables[index]
            if node.getparent() is body:
                body.remove(node)


def _update_fields(settings_xml) -> bytes:
    root = etree.fromstring(settings_xml)
    update = root.find(W("updateFields"))
    if update is None:
        update = etree.SubElement(root, W("updateFields"))
    update.set(W("val"), "true")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def render_template_docx(
    project: Project,
    theses: list[Thesis],
    sources: list[Document],
) -> bytes:
    """Return a draft based on the retained template, preserving untouched package parts."""
    if not TEMPLATE.is_file():
        raise FileNotFoundError(f"Шаблон Word не найден: {TEMPLATE}")
    if hashlib.sha256(TEMPLATE.read_bytes()).hexdigest() != TEMPLATE_SHA256:
        raise RuntimeError("Файл шаблона Word отличается от проверенной версии")

    theses = [thesis for thesis in theses if thesis.review_status != "rejected"]
    source_map = {source.id: source for source in sources}
    citation_numbers: dict[int, int] = {}
    for thesis in sorted(theses, key=lambda item: item.id):
        for card in sorted(thesis.cards, key=lambda item: item.id):
            if card.document_id not in citation_numbers:
                citation_numbers[card.document_id] = len(citation_numbers) + 1

    with zipfile.ZipFile(TEMPLATE, "r") as source_zip:
        parts = [(info, source_zip.read(info.filename)) for info in source_zip.infolist()]

    replacements = {}
    for info, data in parts:
        if info.filename == "word/document.xml":
            root = etree.fromstring(data)
            body = root.find(f".//{W('body')}")
            paragraphs = body.findall(W("p"))
            tables = body.findall(W("tbl"))
            _cover(root, project)
            _fill_icd_section(paragraphs, project)
            _fill_recommendations(paragraphs, theses, citation_numbers)
            _fill_quality_criteria(tables, theses)
            _fill_references(body, theses, source_map, citation_numbers)
            _remove_author_guidance_tables(body, tables)
            replacements[info.filename] = etree.tostring(
                root, xml_declaration=True, encoding="UTF-8", standalone=True
            )
        elif info.filename == "word/settings.xml":
            replacements[info.filename] = _update_fields(data)

    output = BytesIO()
    with zipfile.ZipFile(output, "w") as result_zip:
        for info, data in parts:
            result_zip.writestr(info, replacements.get(info.filename, data))
    return output.getvalue()
