import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, type Checklist } from "@/lib/api";

const RESPONSES = [
  ["unreviewed", "Не проверено"],
  ["yes", "Да"],
  ["no", "Нет"],
  ["not_applicable", "Не применимо"],
] as const;

export default function ChecklistTab({ pid }: { pid: number }) {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["checklist", pid], queryFn: () => api.checklist(pid) });
  const save = useMutation({
    mutationFn: ({ itemId, response, comment }: { itemId: string; response: string; comment: string }) =>
      api.saveChecklistAnswer(pid, itemId, { response, comment }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["checklist", pid] }),
  });
  if (!data) return <p className="text-sm text-muted-foreground">Загружаю чек-лист…</p>;
  const completed = data.items.filter((item) => item.response !== "unreviewed").length;
  return <div className="space-y-5">
    <p className="text-sm text-muted-foreground">{data.source.title}. Отмечено пунктов: {completed} из {data.items.length}. Источник: стр. 1–{data.source.pages}.</p>
    {data.sections.map((section) => {
      const items = data.items.filter((item) => item.section === section.title);
      if (!items.length) return null;
      return <section key={`${section.page}-${section.title}`} className="space-y-2">
        <h2 className="text-lg font-medium">{section.title}</h2>
        {items.map((item) => <ChecklistRow key={item.id} item={item} onSave={(response, comment) => save.mutate({ itemId: item.id, response, comment })} />)}
      </section>;
    })}
  </div>;
}

function ChecklistRow({ item, onSave }: {
  item: Checklist["items"][number];
  onSave: (response: string, comment: string) => void;
}) {
  const [response, setResponse] = useState(item.response);
  const [comment, setComment] = useState(item.comment);
  return <article className="rounded-xl border bg-card p-3">
    <p className="text-sm">{item.text}</p>
    <div className="mt-2 grid gap-2 sm:grid-cols-[180px_1fr]">
      <select className="field" value={response} aria-label={`Ответ ${item.id}`} onChange={(e) => {
        setResponse(e.target.value);
        onSave(e.target.value, comment);
      }}>
        {RESPONSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select>
      <input className="field" placeholder="Комментарий" value={comment} aria-label={`Комментарий ${item.id}`} onChange={(e) => setComment(e.target.value)} onBlur={() => onSave(response, comment)} />
    </div>
    <p className="mt-1 text-xs text-muted-foreground">Источник: стр. {item.source_page} · {item.id}</p>
  </article>;
}
