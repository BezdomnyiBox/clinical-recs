import type { ReactNode } from "react";

export type TraceStatus = "running" | "error" | "pending" | "skipped";

type TraceProps = { children: ReactNode };

type TraceItemProps = {
  title: string;
  description?: string;
  status?: TraceStatus;
  defaultOpen?: boolean;
  children?: ReactNode;
};

export function Trace({ children }: TraceProps) {
  return <ol className="divide-y divide-black/6">{children}</ol>;
}

export function TraceItem({
  title,
  description,
  status,
  defaultOpen = false,
  children,
}: TraceItemProps) {
  const marker = (
    <span
      aria-hidden="true"
      className={`mt-0.5 inline-flex size-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
        status === "error"
          ? "bg-red-100 text-red-700"
          : status === "running"
            ? "bg-blue-100 text-blue-700"
            : status === "pending"
              ? "bg-amber-100 text-amber-700"
              : status === "skipped"
                ? "bg-black/5 text-muted-foreground"
                : "bg-emerald-100 text-emerald-700"
      }`}
    >
      {status === "running" ? <span className="size-2 animate-pulse rounded-full bg-current" /> :
        status === "error" ? "!" : status === "pending" ? "…" : status === "skipped" ? "–" : "✓"}
    </span>
  );

  return (
    <li className="py-2 first:pt-0 last:pb-0">
      {children ? (
        <details className="group" open={defaultOpen}>
          <summary className="flex cursor-pointer list-none items-start gap-3 rounded-lg py-1 text-left marker:hidden [&::-webkit-details-marker]:hidden">
            {marker}
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium">{title}</span>
              {description && <span className="mt-0.5 block text-xs text-muted-foreground">{description}</span>}
            </span>
            <svg className="mt-1 size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path d="m5 7.5 5 5 5-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </summary>
          <div className="ml-8 border-l border-black/10 py-2 pl-4">{children}</div>
        </details>
      ) : (
        <div className="flex items-start gap-3 py-1">
          {marker}
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-medium">{title}</span>
            {description && <span className="mt-0.5 block text-xs text-muted-foreground">{description}</span>}
          </span>
        </div>
      )}
    </li>
  );
}
