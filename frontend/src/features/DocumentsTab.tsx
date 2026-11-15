import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { DOC_STATUS } from "@/lib/labels";

export default function DocumentsTab({ pid }: { pid: number }) {
  const qc = useQueryClient();
  const { data: docs = [] } = useQuery({ queryKey: ["docs", pid], queryFn: () => api.documents(pid), refetchInterval: 3000 });
  const refresh = () => qc.invalidateQueries({ queryKey: ["docs", pid] });
  const upload = useMutation({ mutationFn: (files: FileList) => api.upload(pid, files), onSuccess: refresh });
  const reprocess = useMutation({ mutationFn: api.reprocess, onSuccess: refresh });

  return (
    <div className="space-y-3">
      <label className="flex cursor-pointer flex-col items-center justify-center rounded-[20px] border border-dashed border-black/15 bg-card px-6 py-8 text-center transition-colors hover:border-black/40">
        <span className="text-[17px] font-medium">{upload.isPending ? "Загрузка…" : "Загрузить PDF"}</span>
        <span className="mt-1 text-sm text-muted-foreground">Один или несколько файлов по теме проекта</span>
        <input className="sr-only" type="file" accept="application/pdf" multiple onChange={(e) => e.target.files && upload.mutate(e.target.files)} />
      </label>
      {upload.error && <p className="text-sm text-destructive">{String(upload.error)}</p>}
      {docs.map((d) => {
        const st = DOC_STATUS[d.status] ?? { label: d.status, tone: "neutral" as const };
        return (
          <Card key={d.id} className="flex items-start justify-between gap-4">
            <div>
              <p className="font-medium">{d.filename}</p>
              <p className="text-sm text-muted-foreground">Страниц: {d.page_count ?? "—"}</p>
              {d.status_detail && <p className="mt-1 text-sm text-destructive">{d.status_detail}</p>}
            </div>
            <div className="flex items-center gap-2">
              <Badge tone={st.tone}>{st.label}</Badge>
              <Button size="sm" variant="outline" onClick={() => reprocess.mutate(d.id)}>Обработать заново</Button>
            </div>
          </Card>
        );
      })}
      {!docs.length && <p className="text-sm text-muted-foreground">Загрузите один или несколько PDF по теме проекта.</p>}
    </div>
  );
}
