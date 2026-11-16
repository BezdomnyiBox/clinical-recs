import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { DOC_STATUS } from "@/lib/labels";

export default function ReportTab({ pid }: { pid: number }) {
  const { data } = useQuery({ queryKey: ["report", pid], queryFn: () => api.report(pid) });
  if (!data) return null;
  const { llm } = data;
  return (
    <div className="space-y-4">
      <Card>
        <h3 className="mb-1 text-xl">Ресурсы</h3>
        <p className="text-sm">
          Запросов к модели: {llm.requests}. Токены: {llm.input_tokens} на входе, {llm.output_tokens} на выходе.
          Стоимость: {llm.cost_usd ?? "нет данных"} USD. Время: {llm.seconds.toFixed(1)} с.
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
