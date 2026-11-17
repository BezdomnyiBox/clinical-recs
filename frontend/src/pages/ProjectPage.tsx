import { useQuery } from "@tanstack/react-query";
import { useSearchParams, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import CardsTab from "@/features/CardsTab";
import ChecklistTab from "@/features/ChecklistTab";
import ConflictsTab from "@/features/ConflictsTab";
import DocumentsTab from "@/features/DocumentsTab";
import ReportTab from "@/features/ReportTab";
import ThesesTab from "@/features/ThesesTab";
import { api } from "@/lib/api";

const TABS = [["docs", "Документы"], ["cards", "Карточки"], ["theses", "Тезисы"], ["conflicts", "Противоречия"], ["checklist", "Чек-лист"], ["report", "Отчёт и выгрузка"]] as const;

export default function ProjectPage() {
  const pid = Number(useParams().id);
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedTab = searchParams.get("tab");
  const tab = TABS.some(([key]) => key === requestedTab)
    ? requestedTab as (typeof TABS)[number][0]
    : "docs";
  const { data: project } = useQuery({ queryKey: ["project", pid], queryFn: () => api.project(pid) });

  function selectTab(nextTab: (typeof TABS)[number][0]) {
    const next = new URLSearchParams(searchParams);
    next.set("tab", nextTab);
    if (nextTab !== "cards") next.delete("card");
    setSearchParams(next);
  }

  return (
    <div>
      <h1 className="text-[28px] leading-tight">{project?.title}</h1>
      <p className="mb-5 text-[15px] text-muted-foreground">
        {[project?.age_group, project?.icd_codes.join(", "), project?.organization].filter(Boolean).join(" · ")}
      </p>
      <nav className="mb-6 flex flex-wrap gap-2">
        {TABS.map(([key, label]) => (
          <Button key={key} size="sm" className="rounded-full" variant={tab === key ? "dark" : "outline"} onClick={() => selectTab(key)}>{label}</Button>
        ))}
      </nav>
      {tab === "docs" && <DocumentsTab pid={pid} />}
      {tab === "cards" && <CardsTab pid={pid} />}
      {tab === "theses" && <ThesesTab pid={pid} />}
      {tab === "conflicts" && <ConflictsTab pid={pid} />}
      {tab === "checklist" && <ChecklistTab pid={pid} />}
      {tab === "report" && <ReportTab pid={pid} />}
    </div>
  );
}
