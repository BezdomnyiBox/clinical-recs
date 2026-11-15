import type { Tone } from "@/components/ui/badge";

// Должно совпадать с SECTIONS в backend/app/models.py
export const SECTIONS: [string, string][] = [
  ["summary", "Краткая информация"],
  ["diagnostics", "Диагностика"],
  ["treatment", "Лечение"],
  ["rehabilitation", "Реабилитация"],
  ["prevention", "Профилактика"],
  ["care_organization", "Организация помощи"],
];

export const DOC_STATUS: Record<string, { label: string; tone: Tone }> = {
  queued: { label: "В очереди", tone: "neutral" },
  processing: { label: "Обработка", tone: "warn" },
  done: { label: "Обработан", tone: "ok" },
  done_empty: { label: "Обработан, утверждений нет", tone: "neutral" },
  done_partial: { label: "Обработан частично", tone: "warn" },
  failed: { label: "Ошибка обработки", tone: "bad" },
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
