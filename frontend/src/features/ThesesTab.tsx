import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { SECTIONS } from "@/lib/labels";

export default function ThesesTab({ pid }: { pid: number }) {
  const qc = useQueryClient();
  const { data: theses = [] } = useQuery({ queryKey: ["theses", pid], queryFn: () => api.theses(pid) });
  const [section, setSection] = useState(SECTIONS[0][0]);
  const [text, setText] = useState("");
  const add = useMutation({
    mutationFn: () => api.addExpertThesis(pid, { section, text }),
    onSuccess: () => { setText(""); qc.invalidateQueries({ queryKey: ["theses", pid] }); },
  });

  return (
    <div className="space-y-6">
      {SECTIONS.map(([key, title]) => {
        const items = theses.filter((t) => t.section === key);
        return (
          <section key={key}>
            <h3 className="mb-2 font-semibold">{title}</h3>
            {!items.length && <p className="text-sm text-muted-foreground">Недостаточно материалов</p>}
            <div className="space-y-2">
              {items.map((t) => (
                <Card key={t.id}>
                  <p>{t.text}</p>
                  <div className="mt-2 flex flex-wrap gap-2 text-sm">
                    {t.origin === "expert" && <Badge tone="warn">Экспертный тезис, без цитаты</Badge>}
                    {t.origin === "suggested" && <Badge tone="warn">Предложено системой, нужно решение эксперта</Badge>}
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
        <h3 className="font-semibold">Добавить экспертный тезис</h3>
        <select className="h-9 rounded-md border px-2 text-sm" value={section} onChange={(e) => setSection(e.target.value)}>
          {SECTIONS.map(([k, t]) => <option key={k} value={k}>{t}</option>)}
        </select>
        <textarea className="w-full rounded-md border p-2 text-sm" rows={3} value={text} onChange={(e) => setText(e.target.value)} />
        <Button disabled={!text.trim() || add.isPending} onClick={() => add.mutate()}>Добавить тезис</Button>
      </section>
    </div>
  );
}
