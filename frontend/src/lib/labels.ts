import type { Tone } from "@/components/ui/badge";

// Должно совпадать с SECTIONS в backend/app/models.py
export const SECTIONS: [string, string][] = [
  ["1.1", "1.1 Определение"], ["1.2", "1.2 Этиология и патогенез"], ["1.3", "1.3 Эпидемиология"],
  ["1.4", "1.4 Особенности кодирования"], ["1.5", "1.5 Классификация"], ["1.6", "1.6 Клиническая картина"],
  ["2.1", "2.1 Жалобы и анамнез"], ["2.2", "2.2 Физикальное обследование"], ["2.3", "2.3 Лабораторные исследования"],
  ["2.4", "2.4 Инструментальные исследования"], ["2.5", "2.5 Иные диагностические исследования"],
  ["3.1", "3.1 Консервативное лечение"], ["3.2", "3.2 Хирургическое лечение"], ["3.3", "3.3 Иное лечение"],
  ["4", "4. Медицинская реабилитация и санаторно-курортное лечение"], ["5", "5. Профилактика и диспансерное наблюдение"],
  ["6", "6. Организация оказания медицинской помощи"], ["7", "7. Дополнительная информация"],
];
// Тезисы-рекомендации допустимы только в разделах 2-5 (полные названия для Word хранятся в backend/app/models.py)
export const THESIS_SECTIONS = SECTIONS.filter(([k]) => /^(2\.|3\.)/.test(k) || k === "4" || k === "5");

export const DOC_STATUS: Record<string, { label: string; tone: Tone }> = {
  queued: { label: "В очереди", tone: "neutral" },
  processing: { label: "Обработка", tone: "warn" },
  done: { label: "Обработан", tone: "ok" },
  done_empty: { label: "Обработан, утверждений нет", tone: "neutral" },
  done_partial: { label: "Обработан частично", tone: "warn" },
  failed: { label: "Ошибка обработки", tone: "bad" },
  duplicate: { label: "Дубликат", tone: "neutral" },
  irrelevant: { label: "Нерелевантен", tone: "warn" },
  unsupported: { label: "Не поддерживается", tone: "bad" },
};

export const QUOTE_STATUS: Record<string, { label: string; tone: Tone }> = {
  pending: { label: "Цитата не проверена", tone: "neutral" },
  verified: { label: "Цитата найдена", tone: "ok" },
  failed: { label: "Цитата не подтверждена", tone: "bad" },
};

export const REVIEW_STATUS: Record<string, string> = {
  new: "Не проверено", confirmed: "Подтверждено", rejected: "Отклонено", merged: "Объединено",
};