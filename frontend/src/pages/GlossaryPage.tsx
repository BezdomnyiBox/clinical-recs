import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

type Term = {
    term: string;
    abbr?: string;
    en?: string;
    category: string;
    definition: string;
};
type Glossary = { categories: Record<string, string>; terms: Term[] };

export default function GlossaryPage() {
    const { data } = useQuery({
        queryKey: ["glossary"],
        queryFn: async (): Promise<Glossary> =>
            (await fetch("/api/glossary")).json(),
    });
    const [q, setQ] = useState("");
    const [cat, setCat] = useState("all");
    if (!data) return null;

    const needle = q.trim().toLowerCase();
    const match = (t: Term) =>
        [t.term, t.abbr, t.en, t.definition].some((v) =>
            v?.toLowerCase().includes(needle),
        );
    const groups = Object.entries(data.categories)
        .filter(([key]) => cat === "all" || cat === key)
        .map(([key, title]) => ({
            title,
            terms: data.terms
                .filter((t) => t.category === key && (!needle || match(t)))
                .sort((a, b) => a.term.localeCompare(b.term, "ru")),
        }))
        .filter((g) => g.terms.length);

    return (
        <div className="space-y-6">
            <h2 className="text-2xl">Глоссарий</h2>
            <div className="grid gap-3 md:grid-cols-2">
                <input
                    className="field"
                    placeholder="Поиск по термину, аббревиатуре или определению"
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                />
                <select
                    className="field"
                    value={cat}
                    onChange={(e) => setCat(e.target.value)}
                >
                    <option value="all">Все разделы</option>
                    {Object.entries(data.categories).map(([k, title]) => (
                        <option key={k} value={k}>
                            {title}
                        </option>
                    ))}
                </select>
            </div>
            {!groups.length && (
                <p className="text-sm text-muted-foreground">
                    Ничего не найдено. Попробуйте другое слово.
                </p>
            )}
            {groups.map((g) => (
                <section key={g.title} className="space-y-2">
                    <h3 className="text-xl">
                        {g.title}{" "}
                        <span className="text-sm text-muted-foreground">
                            {g.terms.length}
                        </span>
                    </h3>
                    {g.terms.map((t) => (
                        <Card key={t.term}>
                            <div className="flex flex-wrap items-center gap-2">
                                <span className="font-medium">{t.term}</span>
                                {t.abbr && <Badge>{t.abbr}</Badge>}
                                {t.en && (
                                    <span className="text-sm text-muted-foreground">{t.en}</span>
                                )}
                            </div>
                            <p className="mt-1 text-sm">{t.definition}</p>
                        </Card>
                    ))}
                </section>
            ))}
        </div>
    );
}
