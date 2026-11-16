import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { THESIS_SECTIONS } from "@/lib/labels";
import type { Thesis } from "@/lib/api";

function ThesisEditor({ thesis, onSave, onCriterionSave }: { thesis: Thesis; onSave: (text: string) => void; onCriterionSave: (criterion: Thesis["quality_criterion"]) => void }) {
  const [text, setText] = useState(thesis.text);
  const [criterionText, setCriterionText] = useState(thesis.quality_criterion?.criterion_text ?? "");
  const [isCriterion, setIsCriterion] = useState(thesis.quality_criterion?.is_criterion ?? false);
  const [stage, setStage] = useState(thesis.quality_criterion?.applicable_stage ?? "treatment");
  return <details className="mt-2 text-sm">
    <summary className="cursor-pointer text-link">Править тезис</summary>
    <div className="mt-2 grid gap-2">
      <textarea className="field" rows={3} value={text} onChange={(e) => setText(e.target.value)} />
      <Button size="sm" disabled={!text.trim()} onClick={() => onSave(text)}>Сохранить правку</Button>
      <label className="flex items-center gap-2"><input type="checkbox" checked={isCriterion} onChange={(e) => setIsCriterion(e.target.checked)} />Критерий оценки качества</label>
      {isCriterion && <>
        <textarea className="field" rows={2} placeholder="Выполнено…" value={criterionText} onChange={(e) => setCriterionText(e.target.value)} />
        <select className="field" value={stage} onChange={(e) => setStage(e.target.value)}>
          <option value="diagnosis">Диагностика</option><option value="treatment">Лечение</option>
          <option value="rehabilitation">Реабилитация</option><option value="prevention">Профилактика</option>
        </select>
      </>}
      <Button size="sm" variant="outline" disabled={isCriterion && !criterionText.trim()} onClick={() => onCriterionSave(isCriterion ? { is_criterion: true, criterion_text: criterionText, applicable_stage: stage, measurable: true, auto_eligible: ["A", "B"].includes(thesis.uur ?? "") && ["diagnostic", "therapeutic"].includes(thesis.intervention?.type ?? "") } : { is_criterion: false })}>Сохранить критерий</Button>
    </div>
  </details>;
}

export default function ThesesTab({ pid }: { pid: number }) {
  const qc = useQueryClient();
  const { data: theses = [] } = useQuery({ queryKey: ["theses", pid], queryFn: () => api.theses(pid) });
  const [section, setSection] = useState(THESIS_SECTIONS[0][0]);
  const [text, setText] = useState("");
  const add = useMutation({
    mutationFn: () => api.addExpertThesis(pid, { section, text }),
    onSuccess: () => { setText(""); qc.invalidateQueries({ queryKey: ["theses", pid] }); },
  });
  const edit = useMutation({
    mutationFn: ({ id, text }: { id: number; text: string }) => api.patchThesis(id, { text }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["theses", pid] }),
  });
  const editCriterion = useMutation({
    mutationFn: ({ id, criterion }: { id: number; criterion: Thesis["quality_criterion"] }) => api.patchThesis(id, { quality_criterion: criterion }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["theses", pid] }),
  });

  return (
    <div className="space-y-6">
      {THESIS_SECTIONS.map(([key, title]) => {
        const items = theses.filter((t) => t.section === key);
        return (
          <section key={key}>
            <h3 className="mb-2 text-xl">{title}</h3>
            {!items.length && <p className="text-sm text-muted-foreground">Недостаточно материалов</p>}
            <div className="space-y-2">
              {items.map((t) => (
                <Card key={t.id}>
                  <p>{t.text}</p>
                  <ThesisEditor thesis={t} onSave={(updated) => edit.mutate({ id: t.id, text: updated })} onCriterionSave={(criterion) => editCriterion.mutate({ id: t.id, criterion })} />
                  <div className="mt-2 flex flex-wrap gap-2 text-sm">
                    {t.provenance === "manual" && <Badge tone="warn">Экспертный тезис, без цитаты</Badge>}
                    {t.provenance === "auto" && <Badge tone="warn">Предложено системой, нужно решение эксперта</Badge>}
                    <Badge>УДД: {t.udd ?? "не определён"}</Badge>
                    <Badge>УУР: {t.uur ?? "не определён"}</Badge>
                    <span className="text-muted-foreground">Карточек: {t.card_ids.length}</span>
                  </div>
                  {t.grade_rationale && <p className="mt-2 text-sm text-muted-foreground">{t.grade_rationale}</p>}
                  {t.pending_version && <div className="mt-2 rounded-lg border p-3 text-sm">
                    <strong>Новая версия после обработки</strong>
                    {typeof t.pending_version.section === "string" && <p>Раздел: {t.pending_version.section}</p>}
                    {typeof t.pending_version.text === "string" && <p className="mt-1">{t.pending_version.text}</p>}
                    {(t.pending_version.udd != null || t.pending_version.uur != null) && <p className="mt-1 text-muted-foreground">УДД: {String(t.pending_version.udd ?? "не определён")}, УУР: {String(t.pending_version.uur ?? "не определён")}</p>}
                    {(typeof t.pending_version.quote_verified === "string" || typeof t.pending_version.meaning_verified === "string") && <p className="mt-1 text-muted-foreground">Цитата: {String(t.pending_version.quote_verified ?? "ожидает проверки")}; смысл: {String(t.pending_version.meaning_verified ?? "ожидает проверки")}</p>}
                    {t.pending_version.withdrawn === true && <p className="mt-1 text-muted-foreground">Новая версия карточки больше не содержит явную рекомендацию; проверьте, нужно ли сохранять тезис.</p>}
                    <p className="mt-1 text-muted-foreground">Текущий тезис сохранён до решения эксперта.</p>
                  </div>}
                </Card>
              ))}
            </div>
          </section>
        );
      })}
      <section className="space-y-2 border-t pt-4">
        <h3 className="text-xl">Добавить экспертный тезис</h3>
        <select className="field" value={section} onChange={(e) => setSection(e.target.value)}>
          {THESIS_SECTIONS.map(([k, t]) => <option key={k} value={k}>{t}</option>)}
        </select>
        <textarea className="field" rows={3} value={text} onChange={(e) => setText(e.target.value)} placeholder="Текст тезиса" />
        <Button disabled={!text.trim() || add.isPending} onClick={() => add.mutate()}>Добавить тезис</Button>
      </section>
    </div>
  );
}
