export type Project = { id: number; title: string; age_group: string; icd_codes: string[]; organization: string };
export type Doc = { id: number; filename: string; status: string; status_detail: string | null; page_count: number | null };
export type Card = {
  id: number; document_id: number; page_number: number; statement_ru: string; population: string | null;
  intervention: string | null; quote: string; quote_verified: string; problems: string[]; review_status: string;
};
export type Thesis = {
  id: number; section: string; text: string; origin: string; comment: string | null;
  udd: string | null; uur: string | null; review_status: string; card_ids: number[];
};
export type Report = {
  documents: { document_id: number; filename: string; status: string; detail: string | null; pages_total: number | null; pages_by_status: Record<string, number> }[];
  llm: { requests: number; input_tokens: number; output_tokens: number; cost_usd: number | null; seconds: number };
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch("/api" + path, init);
  if (!r.ok) throw new Error(`${r.status}: ${(await r.text()).slice(0, 300)}`);
  return r.json();
}
const send = (method: string, body: unknown): RequestInit => ({
  method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});

export const api = {
  projects: () => req<Project[]>("/projects"),
  project: (id: number) => req<Project>(`/projects/${id}`),
  createProject: (b: Omit<Project, "id">) => req<Project>("/projects", send("POST", b)),
  documents: (pid: number) => req<Doc[]>(`/projects/${pid}/documents`),
  upload: (pid: number, files: FileList) => {
    const fd = new FormData();
    Array.from(files).forEach((f) => fd.append("files", f));
    return req<Doc[]>(`/projects/${pid}/documents`, { method: "POST", body: fd });
  },
  reprocess: (did: number) => req<Doc>(`/documents/${did}/reprocess`, { method: "POST" }),
  cards: (pid: number) => req<Card[]>(`/projects/${pid}/cards`),
  patchCard: (id: number, b: Partial<Card>) => req<Card>(`/cards/${id}`, send("PATCH", b)),
  theses: (pid: number) => req<Thesis[]>(`/projects/${pid}/theses`),
  addExpertThesis: (pid: number, b: { section: string; text: string }) => req<Thesis>(`/projects/${pid}/theses`, send("POST", b)),
  report: (pid: number) => req<Report>(`/projects/${pid}/report`),
};
export const pdfUrl = (did: number, page: number) => `/api/documents/${did}/file#page=${page}`;
