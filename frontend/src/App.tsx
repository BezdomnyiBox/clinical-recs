import { Link, Route, Routes } from "react-router-dom";
import ProjectPage from "./pages/ProjectPage";
import ProjectsPage from "./pages/ProjectsPage";
import GlossaryPage from "./pages/GlossaryPage";
import Logo from './assets/logo.svg';


export default function App() {
  return (
    <div className="min-h-screen">
      {/* <div className="h-1 bg-accent" /> */}
      <header className="sticky top-0 z-10 border-b border-black/8 bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-6 py-4">
          <img src={Logo} alt="Logo" className="size-8" />
          <div>
            <Link to="/" className="text-[20px] font-medium tracking-tight">
              Клинические рекомендации из статей
            </Link>
            <Link to="/glossary" className="text-[13px] text-muted-foreground">
              Глоссарий
            </Link>
            <p className="text-[13px] text-muted-foreground">Черновик для проверки экспертом, не для лечения пациентов</p>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Routes>
          <Route path="/" element={<ProjectsPage />} />
          <Route path="/projects/:id" element={<ProjectPage />} />
          <Route path="/glossary" element={<GlossaryPage />} />
        </Routes>
      </main>
    </div>
  );
}
