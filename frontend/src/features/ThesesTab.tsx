import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { THESIS_SECTIONS } from "@/lib/labels";

export default function ThesesTab({ pid }: { pid: number }) {
  const qc = useQueryClient();
  const { data: theses = [] } = useQuery({ queryKey: ["theses", pid], queryFn: () => api.theses(pid) });
  const [section, setSection] = useState(THESIS_SECTIONS[0][0]);
  const [text, setText] = useState("");
  const add = useMutation({
    mutationFn: () => api.addExpertThesis(pid, { section, text }),
    onSuccess: () => { setText(""); qc.invalidateQueries({ queryKey: ["theses", pid] }); },
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
                  <div className="mt-2 flex flex-wrap gap-2 text-sm">
                    {t.provenance === "manual" && <Badge tone="warn">Экспертный тезис, без цитаты</Badge>}
                    {t.provenance === "auto" && <Badge tone="warn">Предложено системой, нужно решение эксперта</Badge>}
                    <Badge>УДД: {t.udd ?? "не определён"}</Badge>
                    <Badge>УУР: {t.uur ?? "не определён"}</Badge>
                    <span className="text-muted-foreground">Карточек: {t.card_ids.length}</span>
                  </div>
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