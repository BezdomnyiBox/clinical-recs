import { Link, Route, Routes } from "react-router-dom";
import ProjectPage from "./pages/ProjectPage";
import ProjectsPage from "./pages/ProjectsPage";

export default function App() {
  return (
    <div className="min-h-screen">
      <div className="h-1 bg-accent" />
      <header className="sticky top-0 z-10 border-b border-black/8 bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-6 py-4">
          <span className="size-8 shrink-0 rounded-[10px] bg-accent" aria-hidden />
          <div>
            <Link to="/" className="text-[20px] font-medium tracking-tight">
              Клинические рекомендации из статей
            </Link>
            <p className="text-[13px] text-muted-foreground">Черновик для проверки экспертом, не для лечения пациентов</p>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Routes>
          <Route path="/" element={<ProjectsPage />} />
          <Route path="/projects/:id" element={<ProjectPage />} />
        </Routes>
      </main>
    </div>
  );
}
