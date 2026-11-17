import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, pdfUrl, type ActivityEvent, type ProcessingJob } from "@/lib/api";
import { DOC_STATUS } from "@/lib/labels";
import {
  CircleAlertIcon,
  CircleCheckIcon,
  CircleDashedIcon,
  FileTextIcon,
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

const CALL_STAGE: Record<string, string> = { biblio: "relevance", meaning: "verify" };
const STAGE_ORDER = ["ingest", "relevance", "extract", "verify", "dedupe", "assign_sections", "finalize"];

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

function formatTime(value: string | null | undefined): string {
  if (!value) return "время неизвестно";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "medium" }).format(date);
}

function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds)) return "время неизвестно";
  if (seconds <= 0) return "< 0,1 с";
  if (seconds < 0.1) return `${Math.max(1, Math.round(seconds * 1000))} мс`;
  if (seconds < 1) return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(seconds)} с`;
  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(seconds)} с`;
}

function plural(count: number, forms: [string, string, string]): string {
  const n = Math.abs(count) % 100;
  const last = n % 10;
  if (n > 10 && n < 20) return forms[2];
  if (last > 1 && last < 5) return forms[1];
  if (last === 1) return forms[0];
  return forms[2];
}

function traceStatus(status: string): "running" | "error" | "pending" | undefined {
  if (status === "running" || status === "queued") return "running";
  if (["failed", "parse_error", "error"].includes(status)) return "error";
  if (status === "skipped") return "pending";
  return undefined;
}

function ActivityIcon({ status }: { status: string }) {
  if (status === "running" || status === "queued") return <LoaderCircleIcon className={status === "running" ? "animate-spin" : ""} />;
  if (["failed", "parse_error", "error"].includes(status)) return <CircleAlertIcon />;
  if (status === "skipped") return <CircleDashedIcon />;
  return <CircleCheckIcon />;
}

function normalizeStep(event: ActivityEvent): string {
  return event.kind === "model" ? CALL_STAGE[event.step] ?? event.step : event.step;
}

function eventIsError(event: ActivityEvent): boolean {
  return ["failed", "parse_error"].includes(event.status);
}

function eventDuration(event: ActivityEvent): number | null {
  if (event.status === "running" && event.started_at) {
    return Math.max(0, (Date.now() - new Date(event.started_at).getTime()) / 1000);
  }
  return event.duration_seconds;
}

function cardIdFor(event: ActivityEvent): number | null {
  const value = event.parameters?.card_id ?? event.result_summary?.card_id ?? event.result_summary?.evidence_card_id;
  const id = typeof value === "number" ? value : typeof value === "string" ? Number(value) : NaN;
  return Number.isInteger(id) && id > 0 ? id : null;
}

function eventTitle(event: ActivityEvent): string {
  const cardId = cardIdFor(event);
  if (cardId != null) return `Карточка ev_${cardId}`;
  return event.kind === "model" ? "Вызов модели" : STEP_LABELS[event.step] ?? event.step;
}

function eventDescription(event: ActivityEvent): string {
  const elapsed = eventDuration(event);
  return [event.model, elapsed != null ? formatDuration(elapsed) : null].filter(Boolean).join(" · ");
}

function ActivityDetails({ event, pid }: { event: ActivityEvent; pid: number }) {
  const summary = event.result_summary ?? {};
  const params = event.parameters ?? {};
  const cardId = cardIdFor(event);
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
      {(cardId != null || (event.document_id != null && event.page_start != null)) && (
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {cardId != null && <a className="text-link" href={`/projects/${pid}?tab=cards&card=${cardId}`}>Перейти к карточке ev_{cardId}</a>}
          {event.document_id != null && event.page_start != null && (
            <a className="text-link" href={pdfUrl(event.document_id, event.page_start)} target="_blank" rel="noreferrer">
              Открыть PDF, стр. {event.page_start}{event.page_end != null && event.page_end !== event.page_start ? `–${event.page_end}` : ""}
            </a>
          )}
        </div>
      )}
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

function pageGroupLabel(event: ActivityEvent, count: number, step: string): string {
  const pageLabel = event.page_start == null
    ? "Без номера страницы"
    : event.page_end != null && event.page_end !== event.page_start
      ? `Стр. ${event.page_start}–${event.page_end}`
      : `Стр. ${event.page_start}`;
  const noun = step === "verify"
    ? plural(count, ["проверка", "проверки", "проверок"])
    : step === "extract"
      ? plural(count, ["вызов извлечения", "вызова извлечения", "вызовов извлечения"])
      : step === "relevance"
        ? plural(count, ["вызов анализа", "вызова анализа", "вызовов анализа"])
        : plural(count, ["вызов модели", "вызова модели", "вызовов модели"]);
  return `${pageLabel} · ${count} ${noun}`;
}

function ModelCall({ event, pid }: { event: ActivityEvent; pid: number }) {
  const status = event.status;
  const title = eventTitle(event);
  const prefix = eventIsError(event) ? "Ошибка · " : status === "running" ? "Выполняется · " : "";
  return (
    <TraceCollapsible key={event.id} defaultOpen={eventIsError(event) || status === "running"}>
      <TraceCollapsibleTrigger>
        <TraceLine status={traceStatus(status)}>
          <TraceIcon><ActivityIcon status={status} /></TraceIcon>
          <TraceTitle>{prefix}{title}</TraceTitle>
          <TraceDescription className="max-w-[48%] whitespace-normal text-left">{eventDescription(event)}</TraceDescription>
        </TraceLine>
      </TraceCollapsibleTrigger>
      <TraceCollapsibleContent className="text-foreground"><ActivityDetails event={event} pid={pid} /></TraceCollapsibleContent>
    </TraceCollapsible>
  );
}

function ModelCallGroups({ calls, step, pid }: { calls: ActivityEvent[]; step: string; pid: number }) {
  const groups = new Map<string, ActivityEvent[]>();
  for (const call of calls) {
    const key = `${call.page_start ?? "none"}:${call.page_end ?? ""}`;
    groups.set(key, [...(groups.get(key) ?? []), call]);
  }
  const orderedGroups = [...groups.values()].sort((a, b) => {
    const aPage = a[0].page_start ?? Number.MAX_SAFE_INTEGER;
    const bPage = b[0].page_start ?? Number.MAX_SAFE_INTEGER;
    return aPage - bPage;
  });

  return (
    <Trace className="mt-2">
      {orderedGroups.map((group) => {
        const pageEvent = group[0];
        const failed = group.some(eventIsError);
        const running = group.some((event) => event.status === "running");
        const groupStatus = failed ? "failed" : running ? "running" : "completed";
        return (
          <TraceCollapsible key={`${pageEvent.page_start}-${pageEvent.page_end}-${pageEvent.id}`} defaultOpen={failed || running}>
            <TraceCollapsibleTrigger>
              <TraceLine status={traceStatus(groupStatus)}>
                <TraceIcon><ActivityIcon status={groupStatus} /></TraceIcon>
                <TraceTitle>{pageGroupLabel(pageEvent, group.length, step)}</TraceTitle>
              </TraceLine>
            </TraceCollapsibleTrigger>
            <TraceCollapsibleContent className="text-foreground">
              <Trace>{group.map((event) => <ModelCall key={event.id} event={event} pid={pid} />)}</Trace>
            </TraceCollapsibleContent>
          </TraceCollapsible>
        );
      })}
    </Trace>
  );
}

function stageStatus(stageEvents: ActivityEvent[], calls: ActivityEvent[]): string {
  if ([...stageEvents, ...calls].some(eventIsError)) return "failed";
  if ([...stageEvents, ...calls].some((event) => event.status === "running")) return "running";
  if (stageEvents.some((event) => event.status === "skipped")) return "skipped";
  return "completed";
}

function StageTrace({ events, pid }: { events: ActivityEvent[]; pid: number }) {
  const groups = new Map<string, { stages: ActivityEvent[]; calls: ActivityEvent[] }>();
  for (const event of events) {
    const step = normalizeStep(event);
    const group = groups.get(step) ?? { stages: [], calls: [] };
    (event.kind === "model" ? group.calls : group.stages).push(event);
    groups.set(step, group);
  }
  const ordered = [...groups.entries()].sort((a, b) => {
    const ai = STAGE_ORDER.indexOf(a[0]);
    const bi = STAGE_ORDER.indexOf(b[0]);
    return (ai < 0 ? STAGE_ORDER.length : ai) - (bi < 0 ? STAGE_ORDER.length : bi);
  });

  if (!ordered.length) return <p className="text-sm text-muted-foreground">Для этого запуска журнал событий пока пуст.</p>;

  return (
    <Trace>
      {ordered.map(([step, group]) => {
        const status = stageStatus(group.stages, group.calls);
        const stageEvent = [...group.stages].sort((a, b) => Number(eventIsError(b)) - Number(eventIsError(a)))[0];
        const duration = stageEvent ? eventDuration(stageEvent) : null;
        const callDescription = step === "verify"
          ? `${group.calls.length} ${plural(group.calls.length, ["проверка", "проверки", "проверок"])}`
          : `${group.calls.length} ${plural(group.calls.length, ["вызов модели", "вызова модели", "вызовов модели"])}`;
        const description = [group.calls.length ? callDescription : null, duration != null ? formatDuration(duration) : null]
          .filter(Boolean).join(" · ");
        const detailsOpen = status === "running" || status === "failed";
        return (
          <TraceCollapsible key={step} defaultOpen={detailsOpen}>
            <TraceCollapsibleTrigger>
              <TraceLine status={traceStatus(status)}>
                <TraceIcon><ActivityIcon status={status} /></TraceIcon>
                <TraceTitle>{STEP_LABELS[step] ?? step}</TraceTitle>
                <TraceDescription className="max-w-[48%] whitespace-normal text-left">{description}</TraceDescription>
              </TraceLine>
            </TraceCollapsibleTrigger>
            <TraceCollapsibleContent className="text-foreground">
              {group.stages.map((event) => <ActivityDetails key={event.id} event={event} pid={pid} />)}
              {group.calls.length > 0 && <ModelCallGroups calls={group.calls} step={step} pid={pid} />}
            </TraceCollapsibleContent>
          </TraceCollapsible>
        );
      })}
    </Trace>
  );
}

type RunGroup = { job: ProcessingJob | null; events: ActivityEvent[]; key: string };

function runsForDocument(documentId: number, jobs: ProcessingJob[], events: ActivityEvent[]): RunGroup[] {
  const byId = new Map<string, RunGroup>();
  for (const job of jobs.filter((item) => item.document_id === documentId)) {
    const key = `job-${job.id}`;
    byId.set(key, { job, events: [], key });
  }
  for (const event of events.filter((item) => item.document_id === documentId)) {
    const key = event.job_id == null ? "legacy" : `job-${event.job_id}`;
    const existing = byId.get(key) ?? { job: null, events: [], key };
    existing.events.push(event);
    byId.set(key, existing);
  }
  return [...byId.values()].sort((a, b) => {
    const aTime = a.job?.started_at ?? a.job?.created_at ?? a.events[0]?.started_at ?? "";
    const bTime = b.job?.started_at ?? b.job?.created_at ?? b.events[0]?.started_at ?? "";
    return bTime.localeCompare(aTime);
  });
}

function runStatus(run: RunGroup): string {
  if (run.job?.status === "error") return "failed";
  if (run.job?.status === "running" || run.job?.status === "queued") return run.job.status;
  if (run.events.some(eventIsError)) return "failed";
  if (run.events.some((event) => event.status === "running")) return "running";
  return "completed";
}

function runDuration(run: RunGroup): number | null {
  if (!run.job?.started_at) return null;
  const start = new Date(run.job.started_at).getTime();
  const end = run.job.finished_at ? new Date(run.job.finished_at).getTime() : Date.now();
  return Number.isFinite(start) && Number.isFinite(end) ? Math.max(0, (end - start) / 1000) : null;
}

function RunTrace({ run, pid }: { run: RunGroup; pid: number }) {
  const status = runStatus(run);
  const failedCount = run.events.filter(eventIsError).length + Number(run.job?.status === "error" && !run.events.some(eventIsError));
  const label = run.job ? `Запуск №${run.job.id}` : "События без номера запуска";
  const description = [
    status === "queued" ? "в очереди" : status === "running" ? "выполняется" : status === "failed" ? "есть ошибки" : "завершён",
    `${run.events.length} ${plural(run.events.length, ["событие", "события", "событий"])}`,
    runDuration(run) != null ? formatDuration(runDuration(run)) : null,
  ].filter(Boolean).join(" · ");
  return (
    <TraceCollapsible defaultOpen={status === "running" || status === "queued" || status === "failed"}>
      <TraceCollapsibleTrigger>
        <TraceLine status={traceStatus(status)}>
          <TraceIcon><ActivityIcon status={status} /></TraceIcon>
          <TraceTitle>{label}</TraceTitle>
          <TraceDescription className="max-w-[55%] whitespace-normal text-left">{description}</TraceDescription>
        </TraceLine>
      </TraceCollapsibleTrigger>
      <TraceCollapsibleContent className="text-foreground">
        {failedCount > 0 && <p className="mb-2 rounded bg-red-50 p-2 text-sm text-red-800">Ошибок: {failedCount}</p>}
        {run.job?.error && <p className="mb-2 whitespace-pre-wrap rounded bg-red-50 p-2 text-sm text-red-800">{run.job.error}</p>}
        <StageTrace events={run.events} pid={pid} />
      </TraceCollapsibleContent>
    </TraceCollapsible>
  );
}

function DocumentTrace({
  document,
  jobs,
  events,
  pid,
}: {
  document: ReportDocument;
  jobs: ProcessingJob[];
  events: ActivityEvent[];
  pid: number;
}) {
  const docEvents = events.filter((event) => event.document_id === document.document_id);
  const runs = runsForDocument(document.document_id, jobs, events);
  const active = jobs.some((job) => job.document_id === document.document_id && ["queued", "running"].includes(job.status));
  const hasErrors = document.status === "error"
    || docEvents.some(eventIsError)
    || jobs.some((job) => job.document_id === document.document_id && job.status === "error");
  const pagesStatus = Object.entries(document.pages_by_status).map(([status, count]) => `${status}: ${count}`).join(" · ");

  return (
    <Card>
      <Trace>
        <TraceCollapsible defaultOpen={active || hasErrors}>
          <TraceCollapsibleTrigger>
            <TraceLine status={active ? "running" : hasErrors ? "error" : undefined}>
              <TraceIcon>{active ? <LoaderCircleIcon className="animate-spin" /> : hasErrors ? <CircleAlertIcon /> : <FileTextIcon />}</TraceIcon>
              <TraceTitle className="font-medium">{document.filename}</TraceTitle>
              <TraceDescription className="whitespace-normal text-left">
                {DOC_STATUS[document.status]?.label ?? document.status} · {document.pages_total ?? "—"} стр. · {document.cards_count} карточек · {runs.length} запусков
              </TraceDescription>
            </TraceLine>
          </TraceCollapsibleTrigger>
          <TraceCollapsibleContent className="text-foreground">
            <div className="mb-3 space-y-1 text-xs text-muted-foreground">
              <p>Страниц в PDF: {document.pages_total ?? "нет данных"}; карточек: {document.cards_count}.</p>
              {pagesStatus && <p>Состояние страниц: {pagesStatus}</p>}
              {document.detail && <p className={document.status === "error" ? "text-destructive" : ""}>{document.detail}</p>}
            </div>
            {runs.length ? <Trace>{runs.map((run) => <RunTrace key={run.key} run={run} pid={pid} />)}</Trace> : (
              <p className="text-sm text-muted-foreground">История запусков пока отсутствует.</p>
            )}
          </TraceCollapsibleContent>
        </TraceCollapsible>
      </Trace>
    </Card>
  );
}

type ReportDocument = {
  document_id: number;
  filename: string;
  status: string;
  detail: string | null;
  pages_total: number | null;
  pages_by_status: Record<string, number>;
  cards_count: number;
};

function SummaryMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-medium tabular-nums">{value}</p>
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

  const jobs = data.jobs ?? [];
  const totalErrors = (data.stage_errors ?? 0) + data.llm.failed + data.llm.parse_errors;
  const status = data.active_jobs > 0
    ? "Выполняется"
    : data.documents.length === 0
      ? "Нет документов"
      : totalErrors > 0
        ? "Завершено с ошибками"
        : "Завершено";
  const totalPages = data.documents.reduce((sum, item) => sum + (item.pages_total ?? 0), 0);
  const totalCards = data.documents.reduce((sum, item) => sum + (item.cards_count ?? 0), 0);
  const totalJobSeconds = jobs.reduce((sum, job) => {
    if (!job.started_at) return sum;
    const start = new Date(job.started_at).getTime();
    const end = job.finished_at ? new Date(job.finished_at).getTime() : Date.now();
    return sum + (Number.isFinite(start) && Number.isFinite(end) ? Math.max(0, (end - start) / 1000) : 0);
  }, 0);
  const processingTime = totalJobSeconds || data.llm.seconds;

  return (
    <div className="space-y-4">
      <Card>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-xl">Сводка обработки проекта</h3>
          <Badge tone={totalErrors ? "bad" : data.active_jobs || data.documents.length === 0 ? "warn" : "ok"}>{status}</Badge>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <SummaryMetric label="Статей / PDF" value={data.documents.length} />
          <SummaryMetric label="Страниц" value={totalPages} />
          <SummaryMetric label="Карточек" value={totalCards} />
          <SummaryMetric label="Вызовов модели" value={data.llm.requests} />
          <SummaryMetric label="Ошибок" value={totalErrors} />
          <SummaryMetric label="Общее время" value={formatDuration(processingTime)} />
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          Токены: {formatNumber(data.llm.input_tokens)} на входе и {formatNumber(data.llm.output_tokens)} на выходе · стоимость: {formatCost(data.llm.cost_usd)} USD.
          {data.active_jobs > 0 && " Сводка автоматически обновляется во время обработки."}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Вызовы: успешно {data.llm.completed}, выполняется {data.llm.running}, ошибок {data.llm.failed}, ошибок разбора {data.llm.parse_errors}; ошибок этапов {data.stage_errors ?? 0}.
        </p>
      </Card>

      <section className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-xl">Ход обработки по статьям</h3>
          <span className="text-xs text-muted-foreground">Отдельная история для каждого PDF и запуска</span>
        </div>
        {data.documents.length === 0 ? (
          <Card><p className="text-sm text-muted-foreground">В проекте пока нет документов.</p></Card>
        ) : data.documents.map((document) => (
          <DocumentTrace key={document.document_id} document={document} jobs={jobs} events={data.activity} pid={pid} />
        ))}
        <p className="text-xs text-muted-foreground">
          В журнале указаны параметры, итоги и ошибки. Полные тексты запросов и ответов модели не сохраняются.
        </p>
      </section>

      <Card>
        <h3 className="mb-1 text-xl">Выгрузка</h3>
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
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
