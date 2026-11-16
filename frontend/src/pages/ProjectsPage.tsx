import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";

export default function ProjectsPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { data: projects = [] } = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const [form, setForm] = useState({ title: "", age_group: "adults", icd: "", organization: "" });
  const [icdQuery, setIcdQuery] = useState("");
  const { data: icdMatches = [] } = useQuery({
    queryKey: ["icd10", icdQuery], queryFn: () => api.searchIcd10(icdQuery),
    enabled: icdQuery.trim().length >= 2,
  });
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
        <h2 className="mb-4 text-2xl">Проекты</h2>
        <div className="space-y-2">
          {projects.map((p) => (
            <Card key={p.id}>
              <Link to={`/projects/${p.id}`} className="text-link text-[17px]">{p.title}</Link>
              <p className="text-sm text-muted-foreground">{p.age_group} {p.icd_codes.join(", ")}</p>
            </Card>
          ))}
          {!projects.length && <p className="text-sm text-muted-foreground">Проектов пока нет. Создайте первый справа.</p>}
        </div>
      </section>
      <section>
        <h2 className="mb-4 text-2xl">Новый проект</h2>
        <div className="space-y-3 rounded-[20px] border border-black/6 bg-card p-5">
          <input className="field" placeholder="Тема" value={form.title} onChange={set("title")} />
          <select className="field" value={form.age_group} onChange={(e) => setForm({ ...form, age_group: e.target.value })}>
            <option value="adults">Взрослые</option>
            <option value="children">Дети</option>
            <option value="mixed">Взрослые и дети</option>
          </select>
          <input className="field" placeholder="Поиск по коду или диагнозу МКБ-10" value={icdQuery} onChange={(e) => setIcdQuery(e.target.value)} />
          {!!icdMatches.length && <div className="max-h-56 overflow-auto rounded-xl border bg-card p-1">
            {icdMatches.map((item) => <button key={item.code} type="button" className="block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-black/5" onClick={() => {
              const codes = new Set(form.icd.split(",").map((code) => code.trim()).filter(Boolean));
              codes.add(item.code);
              setForm({ ...form, icd: Array.from(codes).join(", ") });
              setIcdQuery("");
            }}><strong>{item.code}</strong> — {item.name}</button>)}
          </div>}
          <p className="text-sm text-muted-foreground">Выбрано: {form.icd || "нет кодов"}</p>
          <input className="field" placeholder="Организация-разработчик" value={form.organization} onChange={set("organization")} />
          <Button disabled={!form.title || create.isPending} onClick={() => create.mutate()}>Создать проект</Button>
        </div>
      </section>
    </div>
  );
}
