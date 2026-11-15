import { cn } from "@/lib/utils";

export type Tone = "neutral" | "ok" | "warn" | "bad";

const tones: Record<Tone, string> = {
  neutral: "bg-black/6 text-black/70",
  ok: "bg-[#e7f7e8] text-[#0d7a1a]",
  warn: "bg-accent text-black",
  bad: "bg-[#ffe8e6] text-[#c40000]",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: React.ReactNode }) {
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-[13px] font-medium leading-none", tones[tone])}>
      {children}
    </span>
  );
}
