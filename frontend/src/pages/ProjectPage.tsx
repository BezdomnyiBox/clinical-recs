import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import CardsTab from "@/features/CardsTab";
import DocumentsTab from "@/features/DocumentsTab";
import ReportTab from "@/features/ReportTab";
import ThesesTab from "@/features/ThesesTab";
import { api } from "@/lib/api";

const TABS = [["docs", "Документы"], ["cards", "Карточки"], ["theses", "Тезисы"], ["report", "Отчёт и выгрузка"]] as const;

export default function ProjectPage() {
  const pid = Number(useParams().id);
  const [tab, setTab] = useState<(typeof TABS)[number][0]>("docs");
  const { data: project } = useQuery({ queryKey: ["project", pid], queryFn: () => api.project(pid) });

  return (
    <div>
      <h1 className="text-xl font-semibold">{project?.title}</h1>
      <p className="mb-4 text-sm text-muted-foreground">
        {project?.age_group} {project?.icd_codes.join(", ")} {project?.organization}
      </p>
      <nav className="mb-4 flex gap-2 border-b pb-2">
        {TABS.map(([key, label]) => (
          <Button key={key} size="sm" variant={tab === key ? "default" : "ghost"} onClick={() => setTab(key)}>{label}</Button>
        ))}
      </nav>
      {tab === "docs" && <DocumentsTab pid={pid} />}
      {tab === "cards" && <CardsTab pid={pid} />}
      {tab === "theses" && <ThesesTab pid={pid} />}
      {tab === "report" && <ReportTab pid={pid} />}
    </div>
  );
}
