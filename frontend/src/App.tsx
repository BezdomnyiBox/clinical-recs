import { Link, Route, Routes } from "react-router-dom";
import ProjectPage from "./pages/ProjectPage";
import ProjectsPage from "./pages/ProjectsPage";

export default function App() {
  return (
    <div className="mx-auto max-w-5xl p-6">
      <header className="mb-6 border-b pb-3">
        <Link to="/" className="text-lg font-semibold">Клинические рекомендации из статей</Link>
        <p className="text-sm text-muted-foreground">Черновик для проверки экспертом, не для лечения пациентов</p>
      </header>
      <Routes>
        <Route path="/" element={<ProjectsPage />} />
        <Route path="/projects/:id" element={<ProjectPage />} />
      </Routes>
    </div>
  );
}
