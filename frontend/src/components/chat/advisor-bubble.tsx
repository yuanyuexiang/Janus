import { Markdown } from "@/components/chat/markdown";
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

function skillShortName(path: string): string {
  const last = path.split("/").pop() ?? path;
  return last;
}

export type AdvisorBubbleProps = {
  display: string;
  role: string;
  color: string;
  streamingText: string;
  opinion: AdvisorOpinion | null;
  activeSkills?: string[];
  onOpenDetails?: () => void;
};

export function AdvisorBubble({
  display,
  role,
  color,
  streamingText,
  opinion,
  activeSkills,
  onOpenDetails,
}: AdvisorBubbleProps) {
  const showStream = !opinion;
  return (
    <article
      className="rounded-lg border border-l-4 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
      style={{ borderLeftColor: color }}
    >
      <header className="mb-3 flex items-baseline justify-between gap-3">
        <div className="min-w-0">
          <span className="text-base font-semibold" style={{ color }}>
            {display}
          </span>
          <span className="ml-2 text-xs uppercase tracking-wide text-zinc-500">
            {role}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-2 text-xs">
          {opinion && (
            <>
              <span className={`rounded px-2 py-0.5 ${STANCE_COLOR[opinion.stance]}`}>
                {STANCE_LABEL[opinion.stance]}
              </span>
              <span className="text-zinc-500">
                置信度 {(opinion.confidence * 100).toFixed(0)}%
              </span>
            </>
          )}
          {onOpenDetails && (
            <button
              type="button"
              onClick={onOpenDetails}
              className="rounded border border-zinc-200 px-1.5 py-0.5 text-[10px] uppercase text-zinc-500 hover:border-amber-600 hover:text-amber-700 dark:border-zinc-700"
              title="查看顾问看到了什么"
            >
              ⓘ 详情
            </button>
          )}
        </div>
      </header>

      {activeSkills && activeSkills.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1">
          {activeSkills.map((s) => (
            <span
              key={s}
              title={s}
              className="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
            >
              {skillShortName(s)}
            </span>
          ))}
        </div>
      )}

      {showStream && (
        <div className="text-sm text-zinc-700 dark:text-zinc-300">
          {streamingText ? (
            <Markdown>{streamingText}</Markdown>
          ) : (
            <p className="text-zinc-400">等待发言…</p>
          )}
          <span
            className="ml-0.5 inline-block h-3 w-1 animate-pulse align-middle"
            style={{ backgroundColor: color }}
          />
        </div>
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
