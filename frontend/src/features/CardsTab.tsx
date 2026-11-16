import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, pdfUrl, type Card as EvidenceCard } from "@/lib/api";
import { QUOTE_STATUS, REVIEW_STATUS } from "@/lib/labels";
import { useState } from "react";

export default function CardsTab({ pid }: { pid: number }) {
  const qc = useQueryClient();
  const { data: cards = [] } = useQuery({ queryKey: ["cards", pid], queryFn: () => api.cards(pid) });
  const decide = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => api.patchCard(id, { review_status: status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cards", pid] }),
  });
  const edit = useMutation({
    mutationFn: ({ id, values }: { id: number; values: Partial<EvidenceCard> }) => api.patchCard(id, values),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cards", pid] }),
  });

  if (!cards.length) return <p className="text-sm text-muted-foreground">Карточек пока нет. Они появятся после обработки документов.</p>;
  return (
    <div className="space-y-3">
      {cards.map((c) => {
        const q = QUOTE_STATUS[c.quote_verified];
        const Preview = () => {
          const [statement, setStatement] = useState(c.statement_ru);
          const [population, setPopulation] = useState(c.population ?? "");
          const [intervention, setIntervention] = useState(c.intervention ?? "");
          const [outcome, setOutcome] = useState(c.outcome ?? "");
          const [conditions, setConditions] = useState(c.conditions ?? "");
          const pending = c.pending_version;
          const pendingField = (key: string) => {
            const value = pending?.[key];
            return typeof value === "string" && value.trim() ? value : null;
          };
          const pendingProblems = Array.isArray(pending?.problems)
            ? pending.problems.filter((value): value is string => typeof value === "string")
            : [];
          return <>
            <details className="text-sm">
              <summary className="cursor-pointer text-link">Просмотр PDF рядом с цитатой</summary>
              <iframe title={`Страница ${c.page_number} документа`} src={pdfUrl(c.document_id, c.page_number)} className="mt-2 h-[520px] w-full rounded-lg border" />
            </details>
            <details className="text-sm">
              <summary className="cursor-pointer text-link">Править карточку</summary>
              <div className="mt-2 grid gap-2">
                <textarea className="field" rows={3} aria-label="Формулировка" value={statement} onChange={(e) => setStatement(e.target.value)} />
                <input className="field" aria-label="Популяция" placeholder="Популяция" value={population} onChange={(e) => setPopulation(e.target.value)} />
                <input className="field" aria-label="Вмешательство" placeholder="Вмешательство" value={intervention} onChange={(e) => setIntervention(e.target.value)} />
                <input className="field" aria-label="Исход" placeholder="Исход" value={outcome} onChange={(e) => setOutcome(e.target.value)} />
                <input className="field" aria-label="Условия" placeholder="Доза, сроки, условия" value={conditions} onChange={(e) => setConditions(e.target.value)} />
                <Button size="sm" disabled={edit.isPending || !statement.trim()} onClick={() => edit.mutate({ id: c.id, values: { statement_ru: statement, population: population || null, intervention: intervention || null, outcome: outcome || null, conditions: conditions || null } })}>Сохранить правку</Button>
              </div>
            </details>
            {pending && <div className="rounded-lg border p-3 text-sm">
              <p className="font-medium">Новая версия после повторной обработки</p>
              {pendingField("statement_ru") && <p className="mt-1">{pendingField("statement_ru")}</p>}
              <dl className="mt-2 grid gap-1 sm:grid-cols-[max-content_1fr] sm:gap-x-2">
                {pendingField("population") && <><dt className="font-medium">Популяция</dt><dd>{pendingField("population")}</dd></>}
                {pendingField("subject") && <><dt className="font-medium">Вмешательство</dt><dd>{pendingField("subject")}</dd></>}
                {pendingField("object_") && <><dt className="font-medium">Исход</dt><dd>{pendingField("object_")}</dd></>}
                {pendingField("conditions") && <><dt className="font-medium">Условия</dt><dd>{pendingField("conditions")}</dd></>}
                {pending?.page != null && <><dt className="font-medium">Страница</dt><dd>{String(pending.page)}</dd></>}
              </dl>
              {pendingField("quote") && <blockquote className="mt-2 border-l-[3px] border-accent pl-3 italic text-black/70">{pendingField("quote")}</blockquote>}
              <p className="mt-2 text-muted-foreground">Цитата: {String(pending.quote_verified ?? "ожидает проверки")}; смысл и отрицания: {String(pending.meaning_verified ?? "ожидает проверки")}</p>
              {pendingProblems.map((problem) => <p key={problem} className="mt-1 text-destructive">{problem}</p>)}
              <p className="mt-2 text-muted-foreground">Текущая карточка не изменена; новую версию нужно проверить.</p>
            </div>}
          </>;
        };
        return (
          <Card key={c.id} className="space-y-2">
            <p className="font-medium">{c.statement_ru}</p>
            <blockquote className="border-l-[3px] border-accent pl-3 text-[15px] italic leading-snug text-black/70">{c.quote}</blockquote>
            <Preview />
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <a className="text-link" href={pdfUrl(c.document_id, c.page_number)} target="_blank" rel="noreferrer">
                Открыть стр. {c.page_number}
              </a>
              <Badge tone={q.tone}>{q.label}</Badge>
              <Badge>{REVIEW_STATUS[c.review_status]}</Badge>
            </div>
            {c.problems.map((p) => <p key={p} className="text-sm text-destructive">{p}</p>)}
            <div className="flex gap-2">
              <Button size="sm" className="rounded-full" onClick={() => decide.mutate({ id: c.id, status: "confirmed" })}>Подтвердить</Button>
              <Button size="sm" variant="outline" className="rounded-full" onClick={() => decide.mutate({ id: c.id, status: "rejected" })}>Отклонить</Button>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
