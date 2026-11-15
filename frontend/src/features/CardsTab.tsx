import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, pdfUrl } from "@/lib/api";
import { QUOTE_STATUS, REVIEW_STATUS } from "@/lib/labels";

export default function CardsTab({ pid }: { pid: number }) {
  const qc = useQueryClient();
  const { data: cards = [] } = useQuery({ queryKey: ["cards", pid], queryFn: () => api.cards(pid) });
  const decide = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => api.patchCard(id, { review_status: status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cards", pid] }),
  });

  if (!cards.length) return <p className="text-sm text-muted-foreground">Карточек пока нет. Они появятся после обработки документов.</p>;
  return (
    <div className="space-y-3">
      {cards.map((c) => {
        const q = QUOTE_STATUS[c.quote_verified];
        return (
          <Card key={c.id} className="space-y-2">
            <p className="font-medium">{c.statement_ru}</p>
            <blockquote className="border-l-2 pl-3 text-sm italic text-muted-foreground">{c.quote}</blockquote>
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <a className="text-primary underline" href={pdfUrl(c.document_id, c.page_number)} target="_blank" rel="noreferrer">
                Открыть стр. {c.page_number}
              </a>
              <Badge tone={q.tone}>{q.label}</Badge>
              <Badge>{REVIEW_STATUS[c.review_status]}</Badge>
            </div>
            {c.problems.map((p) => <p key={p} className="text-sm text-destructive">{p}</p>)}
            <div className="flex gap-2">
              <Button size="sm" onClick={() => decide.mutate({ id: c.id, status: "confirmed" })}>Подтвердить</Button>
              <Button size="sm" variant="outline" onClick={() => decide.mutate({ id: c.id, status: "rejected" })}>Отклонить</Button>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
