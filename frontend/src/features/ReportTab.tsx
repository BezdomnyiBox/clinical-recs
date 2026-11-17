import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { api, type ActivityEvent } from "@/lib/api";
import { DOC_STATUS } from "@/lib/labels";
import {
  CircleAlertIcon,
  CircleCheckIcon,
  CircleDashedIcon,
  LoaderCircleIcon,
} from "lucide-react";
import {
  Trace,
  TraceCollapsible,
  TraceCollapsibleContent,
  TraceCollapsibleTrigger,
  TraceDescription,
  TraceIcon,
  TraceLine,
  TraceTitle,
} from "@/components/ui/trace";

const STEP_LABELS: Record<string, string> = {
  ingest: "Чтение PDF",
  relevance: "Оценка релевантности и библиографии",
  extract: "Извлечение утверждений",
  verify: "Проверка цитат и смысла",
  meaning: "Проверка смысла утверждения",
  biblio: "Анализ источника",
  dedupe: "Поиск дубликатов и противоречий",
  assign_sections: "Формирование тезисов",
  finalize: "Завершение обработки",
};

const SUMMARY_LABELS: Record<string, string> = {
  title: "Название источника",
  year: "Год",
  study_design: "Дизайн исследования",
  relevance: "Релевантность",
  relevance_reason: "Обоснование релевантности",
  cards_proposed: "Предложено карточек",
  recommendations_proposed: "Рекомендаций",
  results_proposed: "Результатов исследований",
  card_id: "Карточка",
  verified: "Смысл подтверждён",
  negation_mismatch: "Расхождение в отрицании",
  explanation: "Пояснение модели",
  cards_total: "Всего карточек",
  recommendations: "Рекомендаций",
  results: "Результатов исследований",
  pending_versions: "Новых версий на проверке",
  pages_processed: "Обработано страниц",
  pages_failed: "Страниц с ошибкой",
  cards_checked: "Проверено карточек",
  quotes_verified: "Цитат подтверждено",
  quotes_failed: "Цитат не подтверждено",
  meaning_verified: "Формулировок по смыслу подтверждено",
  meaning_failed: "Формулировок по смыслу не подтверждено",
  meaning_pending: "Ожидают проверки смысла",
  merged_cards_in_project: "Объединено карточек в проекте",
  conflicts_in_project: "Противоречий в проекте",
  theses_linked: "Связано тезисов",
  automatic_theses: "Сгенерировано автоматически",
  pending_theses: "Новых версий тезисов на проверке",
  pages_total: "Всего страниц",
  text_layer_supported: "Текстовый слой поддерживается",
  document_status: "Итоговый статус документа",
  reason: "Причина пропуска",
};

const PARAMETER_LABELS: Record<string, string> = {
  provider: "Провайдер",
  temperature: "Температура",
  max_tokens: "Максимум токенов ответа",
  output_schema: "Формат ответа",
  pages: "Страницы в запросе",
  card_id: "Проверяемая карточка",
};

function formatNumber(value: unknown): string {
  if (typeof value === "number") return new Intl.NumberFormat("ru-RU").format(value);
  if (typeof value === "boolean") return value ? "да" : "нет";
  if (typeof value === "string") return value || "—";
  if (value == null) return "—";
  return JSON.stringify(value) ?? String(value);
}

function formatParameterValue(key: string, value: unknown): string {
  if (key === "provider" && value === "iacpaas") return "ИАПУ ДВО РАН";
  if (key === "provider" && value === "openrouter") return "OpenRouter";
  return formatNumber(value);
}

function formatCost(value: number | null | undefined): string {
  if (value == null) return "нет данных";
  return value < 0.01 ? value.toFixed(6) : value.toFixed(4);
}

function formatTime(value: string | null): string {
  if (!value) return "время неизвестно";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "medium" }).format(date);
}

function traceStatus(status: string): "running" | "error" | "pending" | undefined {
  if (status === "running") return "running";
  if (status === "failed" || status === "parse_error") return "error";
  if (status === "skipped") return "pending";
  return undefined;
}

function eventTitle(event: ActivityEvent): string {
  const label = STEP_LABELS[event.step] ?? event.step;
  const subject = event.kind === "model" ? "Модель" : "Этап";
  const prefix = event.status === "running"
    ? "Выполняется"
    : event.status === "failed"
      ? "Ошибка"
      : event.status === "parse_error"
        ? "Ответ не разобран"
        : event.status === "skipped"
          ? "Пропущено"
          : "Завершено";
  return `${prefix} · ${subject}: ${label}`;
}

function ActivityIcon({ status }: { status: string }) {
  if (status === "running") return <LoaderCircleIcon className="animate-spin" />;
  if (status === "failed" || status === "parse_error") return <CircleAlertIcon />;
  if (status === "skipped") return <CircleDashedIcon />;
  return <CircleCheckIcon />;
}

function eventDescription(event: ActivityEvent): string {
  const elapsed = event.status === "running" && event.started_at
    ? Math.max(0, (Date.now() - new Date(event.started_at).getTime()) / 1000)
    : event.duration_seconds;
  const parts = [
    event.filename,
    event.kind === "model" && event.model ? event.model : null,
    event.page_start != null
      ? event.page_end != null && event.page_end !== event.page_start
        ? `стр. ${event.page_start}–${event.page_end}`
        : `стр. ${event.page_start}`
      : null,
    elapsed != null ? `${elapsed.toFixed(1)} с` : null,
  ];
  return parts.filter(Boolean).join(" · ");
}

function ActivityDetails({ event }: { event: ActivityEvent }) {
  const summary = event.result_summary ?? {};
  const params = event.parameters ?? {};
  const items: [string, unknown][] = event.kind === "model"
    ? [
        ["Фактически использованная модель", event.actual_model],
        ["Токены на входе", event.input_tokens],
        ["Токены на выходе", event.output_tokens],
        ["Стоимость, USD", event.cost_usd == null ? "нет данных от провайдера" : formatCost(event.cost_usd)],
        ["Идентификатор ответа", event.response_id],
        ["Хеш запроса", event.prompt_hash],
      ]
    : [];

  return (
    <div className="space-y-2 text-xs">
      <p className="text-muted-foreground">Начало: {formatTime(event.started_at)}</p>
      {event.finished_at && <p className="text-muted-foreground">Завершено: {formatTime(event.finished_at)}</p>}
      {items.some(([, value]) => value != null) && (
        <dl className="grid gap-x-4 gap-y-1 sm:grid-cols-[max-content_1fr]">
          {items.filter(([, value]) => value != null).map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="break-all">{formatNumber(value)}</dd>
            </div>
          ))}
        </dl>
      )}
      {Object.keys(params).length > 0 && (
        <dl className="grid gap-x-4 gap-y-1 sm:grid-cols-[max-content_1fr]">
          {Object.entries(params).map(([key, value]) => (
            <div key={key} className="contents">
              <dt className="text-muted-foreground">{PARAMETER_LABELS[key] ?? key}</dt>
              <dd className="break-all">{formatParameterValue(key, value)}</dd>
            </div>
          ))}
        </dl>
      )}
      {Object.keys(summary).length > 0 && (
        <div>
          <p className="mb-1 font-medium">Результат</p>
          <dl className="grid gap-x-4 gap-y-1 sm:grid-cols-[max-content_1fr]">
            {Object.entries(summary).map(([key, value]) => (
              <div key={key} className="contents">
                <dt className="text-muted-foreground">{SUMMARY_LABELS[key] ?? key}</dt>
                <dd className="break-words">{formatNumber(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
      {event.error_message && (
        <p className="whitespace-pre-wrap break-words rounded bg-red-50 p-2 text-red-800">
          {event.error_type ? `${event.error_type}: ` : ""}{event.error_message}
        </p>
      )}
    </div>
  );
}

export default function ReportTab({ pid }: { pid: number }) {
  const { data } = useQuery({
    queryKey: ["report", pid],
    queryFn: () => api.report(pid),
    refetchInterval: (query) => query.state.data?.active_jobs ? 1500 : false,
  });
  if (!data) return null;
  const { llm } = data;
  return (
    <div className="space-y-4">
      <Card>
        <h3 className="mb-1 text-xl">Ресурсы</h3>
        <p className="text-sm">
          Запросов к модели: {llm.requests}. Токены: {llm.input_tokens} на входе, {llm.output_tokens} на выходе.
          Стоимость: {formatCost(llm.cost_usd)} USD. Время: {llm.seconds.toFixed(1)} с.
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Завершено: {llm.completed}; выполняется: {llm.running}; ошибок: {llm.failed}; ошибок разбора: {llm.parse_errors}.
          {data.active_jobs > 0 && " Отчёт обновляется во время обработки."}
        </p>
      </Card>
      <Card>
        <div className="mb-3 flex items-baseline justify-between gap-3">
          <h3 className="text-xl">Ход обработки</h3>
          <span className="text-xs text-muted-foreground">Последние {data.activity.length} событий</span>
        </div>
        {data.activity.length === 0 ? (
          <p className="text-sm text-muted-foreground">События появятся здесь после запуска обработки документа.</p>
        ) : (
          <Trace>
            {data.activity.map((event) => (
              <TraceCollapsible
                key={event.id}
                defaultOpen={event.status === "running"}
              >
                <TraceCollapsibleTrigger>
                  <TraceLine status={traceStatus(event.status)}>
                    <TraceIcon><ActivityIcon status={event.status} /></TraceIcon>
                    <TraceTitle>{eventTitle(event)}</TraceTitle>
                    <TraceDescription className="max-w-[50%] whitespace-normal text-left">
                      {eventDescription(event)}
                    </TraceDescription>
                  </TraceLine>
                </TraceCollapsibleTrigger>
                <TraceCollapsibleContent className="text-foreground">
                  <ActivityDetails event={event} />
                </TraceCollapsibleContent>
              </TraceCollapsible>
            ))}
          </Trace>
        )}
        <p className="mt-3 text-xs text-muted-foreground">
          Журнал содержит параметры, сводку результата и ошибки. Полные тексты запросов и ответов модели не сохраняются.
        </p>
      </Card>
      <Card>
        <h3 className="mb-1 text-xl">Покрытие по документам</h3>
        {data.documents.map((d) => (
          <p key={d.document_id} className="text-sm">
            {d.filename}: {DOC_STATUS[d.status]?.label ?? d.status}, страниц {d.pages_total ?? "—"},{" "}
            {Object.entries(d.pages_by_status).map(([s, n]) => `${s}: ${n}`).join(", ")}
          </p>
        ))}
      </Card>
      <Card>
        <h3 className="mb-1 text-xl">Выгрузка</h3>
        <div className="flex gap-4 text-sm">
          <a className="text-link" href={`/api/projects/${pid}/export/json`} target="_blank" rel="noreferrer">JSON</a>
          <a className="text-link" href={`/api/projects/${pid}/export/validate`} target="_blank" rel="noreferrer">Проверка по схеме</a>
          <a className="text-link" href="/api/checklist" target="_blank" rel="noreferrer">Чек-лист требований</a>
          <a className="text-link" href={`/api/projects/${pid}/export/text`}>Текст</a>
          <a className="text-link" href={`/api/projects/${pid}/export/docx`}>Word</a>
        </div>
      </Card>
    </div>
  );
}
