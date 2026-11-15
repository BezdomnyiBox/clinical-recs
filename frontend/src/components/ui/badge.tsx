import { cn } from "@/lib/utils";

export type Tone = "neutral" | "ok" | "warn" | "bad";

const tones: Record<Tone, string> = {
  neutral: "bg-muted text-muted-foreground",
  ok: "bg-emerald-100 text-emerald-800",
  warn: "bg-amber-100 text-amber-900",
  bad: "bg-red-100 text-red-800",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: React.ReactNode }) {
  return <span className={cn("inline-block rounded px-2 py-0.5 text-xs font-medium", tones[tone])}>{children}</span>;
}
