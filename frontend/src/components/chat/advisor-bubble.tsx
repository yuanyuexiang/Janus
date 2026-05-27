import type { AdvisorOpinion } from "@/lib/types";

const STANCE_LABEL: Record<AdvisorOpinion["stance"], string> = {
  bullish: "看多",
  neutral: "中性",
  bearish: "看空",
  conditional: "有条件",
};

const STANCE_COLOR: Record<AdvisorOpinion["stance"], string> = {
  bullish: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  neutral: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  bearish: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  conditional: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
};

export type AdvisorBubbleProps = {
  display: string;
  role: string;
  color: string;
  streamingText: string;
  opinion: AdvisorOpinion | null;
};

export function AdvisorBubble({
  display,
  role,
  color,
  streamingText,
  opinion,
}: AdvisorBubbleProps) {
  const showStream = !opinion;
  return (
    <article
      className="rounded-lg border border-l-4 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
      style={{ borderLeftColor: color }}
    >
      <header className="mb-3 flex items-baseline justify-between">
        <div>
          <span className="text-base font-semibold" style={{ color }}>
            {display}
          </span>
          <span className="ml-2 text-xs uppercase tracking-wide text-zinc-500">
            {role}
          </span>
        </div>
        {opinion && (
          <div className="flex items-center gap-2 text-xs">
            <span className={`rounded px-2 py-0.5 ${STANCE_COLOR[opinion.stance]}`}>
              {STANCE_LABEL[opinion.stance]}
            </span>
            <span className="text-zinc-500">
              置信度 {(opinion.confidence * 100).toFixed(0)}%
            </span>
          </div>
        )}
      </header>

      {showStream && (
        <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
          {streamingText}
          <span className="ml-0.5 inline-block h-3 w-1 animate-pulse bg-zinc-400 align-middle" />
        </pre>
      )}

      {opinion && (
        <div className="space-y-4">
          <p className="text-sm leading-relaxed text-zinc-800 dark:text-zinc-200">
            {opinion.summary_for_user}
          </p>

          {opinion.key_points.length > 0 && (
            <section>
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                核心观点
              </h3>
              <ul className="space-y-2">
                {opinion.key_points.map((p, i) => (
                  <li key={i} className="text-sm">
                    <div className="font-medium text-zinc-800 dark:text-zinc-200">
                      · {p.claim}
                    </div>
                    <div className="ml-2 text-zinc-600 dark:text-zinc-400">
                      {p.detail}
                    </div>
                    {p.source_tool && (
                      <code className="ml-2 text-xs text-zinc-400">
                        source: {p.source_tool}
                      </code>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {opinion.concerns.length > 0 && (
            <section>
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                主要风险
              </h3>
              <ul className="list-inside list-disc space-y-1 text-sm text-zinc-700 dark:text-zinc-300">
                {opinion.concerns.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </section>
          )}

          {opinion.what_could_change_my_mind.length > 0 && (
            <section>
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                变心条件
              </h3>
              <ul className="list-inside list-disc space-y-1 text-sm text-zinc-700 dark:text-zinc-300">
                {opinion.what_could_change_my_mind.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </article>
  );
}
