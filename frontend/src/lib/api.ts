export type Project = { id: number; title: string; age_group: string; icd_codes: string[]; organization: string };
export type Doc = { id: number; filename: string; status: string; status_detail: string | null; page_count: number | null };
export type Card = {
  id: number; document_id: number; page_number: number; statement_ru: string; population: string | null;
  intervention: string | null; outcome: string | null; conditions: string | null; subject: string | null;
  quote: string; quote_verified: string; meaning_verified: string; problems: string[]; review_status: string;
  pending_version: Record<string, unknown> | null;
};
export type Thesis = {
  id: number; section: string; text: string; provenance: string; comment: string | null;
  udd: number | null; uur: string | null; review_status: string; card_ids: number[];
  pending_version: Record<string, unknown> | null; subsection_title: string | null;
  direction: string | null; strength_phrase: string | null; grade_rationale: string | null;
  intervention: { type?: string; action?: string } | null;
  quality_criterion: { is_criterion: boolean; criterion_text?: string | null; applicable_stage?: string; measurable?: boolean; auto_eligible?: boolean } | null;
};
export type Report = {
  documents: { document_id: number; filename: string; status: string; detail: string | null; pages_total: number | null; pages_by_status: Record<string, number> }[];
  active_jobs: number;
  activity: ActivityEvent[];
  llm: {
    requests: number; completed: number; failed: number; parse_errors: number; running: number;
    input_tokens: number; output_tokens: number; cost_usd: number | null; seconds: number;
  };
};
export type ActivityEvent = {
  id: string;
  kind: "stage" | "model";
  document_id: number;
  filename: string | null;
  step: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  model?: string | null;
  actual_model?: string | null;
  response_id?: string | null;
  prompt_hash?: string | null;
  page_start?: number | null;
  page_end?: number | null;
  parameters?: Record<string, unknown> | null;
  input_tokens?: number;
  output_tokens?: number;
  cost_usd?: number | null;
  result_summary?: Record<string, unknown> | null;
  error_type?: string | null;
  error_message?: string | null;
};
export type IcdCode = { code: string; name: string; parent_code: string | null; active: boolean };
export type Checklist = {
  source: { title: string; file: string; pages: number };
  sections: { title: string; page: number }[];
  items: { id: string; section: string; text: string; source_page: number; response: string; comment: string }[];
};
export type Conflict = {
  id: number; card_ids: number[]; status: string; description: string;
  sides: { card_id: number; statement_ru: string; predicate: string | null; negation: boolean;
    quote: string; page_number: number; document_id: number; filename: string | null }[];
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
  patchThesis: (id: number, b: Partial<Thesis>) => req<Thesis>(`/theses/${id}`, send("PATCH", b)),
  addExpertThesis: (pid: number, b: { section: string; text: string }) => req<Thesis>(`/projects/${pid}/theses`, send("POST", b)),
  report: (pid: number) => req<Report>(`/projects/${pid}/report`),
  searchIcd10: (query: string) => req<IcdCode[]>(`/icd10?q=${encodeURIComponent(query)}`),
  checklist: (pid: number) => req<Checklist>(`/projects/${pid}/checklist`),
  saveChecklistAnswer: (pid: number, itemId: string, body: { response: string; comment: string }) =>
    req(`/projects/${pid}/checklist/${itemId}`, send("PUT", body)),
  conflicts: (pid: number) => req<Conflict[]>(`/projects/${pid}/conflicts`),
};
export const pdfUrl = (did: number, page: number) => `/api/documents/${did}/file#page=${page}`;
