import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { api, pdfUrl } from "@/lib/api";

export default function ConflictsTab({ pid }: { pid: number }) {
  const { data: conflicts = [] } = useQuery({
    queryKey: ["conflicts", pid],
    queryFn: () => api.conflicts(pid),
  });

  if (!conflicts.length) {
    return <p className="text-sm text-muted-foreground">Кандидатов на противоречие пока нет.</p>;
  }

  return (
    <div className="space-y-3">
      {conflicts.map((conflict) => (
        <Card key={conflict.id} className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg">Кандидат на противоречие</h3>
            <Badge tone="warn">{conflict.status}</Badge>
            {conflict.card_ids.map((id) => <Badge key={id}>Карточка ev_{id}</Badge>)}
          </div>
          <p className="text-sm text-muted-foreground">{conflict.description}</p>
          <div className="grid gap-3 md:grid-cols-2">
            {conflict.sides.map((side) => (
              <section key={side.card_id} className="rounded-lg border p-3">
                <p className="text-sm font-medium">Карточка ev_{side.card_id}</p>
                <p className="mt-1">{side.statement_ru}</p>
                {side.predicate && <p className="mt-1 text-sm text-muted-foreground">Направление: {side.predicate}{side.negation ? "; отрицание отмечено" : ""}</p>}
                <blockquote className="mt-2 border-l-[3px] border-accent pl-3 text-sm italic text-black/70">{side.quote}</blockquote>
                <p className="mt-2 text-sm text-muted-foreground">{side.filename ?? `Документ ${side.document_id}`}, стр. {side.page_number}</p>
                <a className="text-link text-sm" href={pdfUrl(side.document_id, side.page_number)} target="_blank" rel="noreferrer">Открыть страницу PDF</a>
              </section>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}
