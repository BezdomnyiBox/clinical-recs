import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";

const field = "h-9 w-full rounded-md border px-3 text-sm";

export default function ProjectsPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const [form, setForm] = useState({ title: "", age_group: "", icd: "", organization: "" });
  const create = useMutation({
    mutationFn: () => api.createProject({
      title: form.title, age_group: form.age_group, organization: form.organization,
      icd_codes: form.icd.split(",").map((c) => c.trim()).filter(Boolean),
    }),
    onSuccess: (p) => { qc.invalidateQueries({ queryKey: ["projects"] }); navigate(`/projects/${p.id}`); },
  });
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <section>
        <h2 className="mb-3 font-semibold">Проекты</h2>
        <div className="space-y-2">
          {projects.map((p) => (
            <Card key={p.id}>
              <Link to={`/projects/${p.id}`} className="font-medium text-primary">{p.title}</Link>
              <p className="text-sm text-muted-foreground">{p.age_group} {p.icd_codes.join(", ")}</p>
            </Card>
          ))}
          {!projects.length && <p className="text-sm text-muted-foreground">Проектов пока нет. Создайте первый справа.</p>}
        </div>
      </section>
      <section>
        <h2 className="mb-3 font-semibold">Новый проект</h2>
        <div className="space-y-2">
          <input className={field} placeholder="Тема" value={form.title} onChange={set("title")} />
          <input className={field} placeholder="Возрастная группа" value={form.age_group} onChange={set("age_group")} />
          <input className={field} placeholder="Коды МКБ-10 через запятую" value={form.icd} onChange={set("icd")} />
          <input className={field} placeholder="Организация-разработчик" value={form.organization} onChange={set("organization")} />
          <Button disabled={!form.title || create.isPending} onClick={() => create.mutate()}>Создать проект</Button>
        </div>
      </section>
    </div>
  );
}
