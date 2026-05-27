import { Markdown } from "@/components/chat/markdown";
import type { CouncilSummary } from "@/lib/types";

const VERDICT_LABEL: Record<CouncilSummary["verdict"], string> = {
  strong_consensus: "强共识",
  weak_consensus: "弱共识",
  split: "明显分歧",
};

const VERDICT_COLOR: Record<CouncilSummary["verdict"], string> = {
  strong_consensus: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  weak_consensus: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  split: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
};

function SeverityBar({ level }: { level: number }) {
  const blocks = [1, 2, 3, 4, 5].map((n) => (
    <span
      key={n}
      className={`inline-block h-1.5 w-3 ${
        n <= level
          ? n >= 4
            ? "bg-red-500"
            : n === 3
              ? "bg-amber-500"
              : "bg-emerald-500"
          : "bg-zinc-200 dark:bg-zinc-700"
      }`}
    />
  ));
  return <span className="inline-flex gap-0.5">{blocks}</span>;
}

export type ConductorSummaryProps = {
  streamingText: string;
  summary: CouncilSummary | null;
  onOpenDetails?: () => void;
};

export function ConductorSummary({ streamingText, summary, onOpenDetails }: ConductorSummaryProps) {
  const showStream = !summary;

  return (
    <article
      className="rounded-lg border-2 border-amber-700/40 bg-amber-50/40 p-5 shadow-sm dark:border-amber-600/40 dark:bg-amber-950/20"
    >
      <header className="mb-3 flex items-baseline justify-between">
        <div>
          <span className="text-base font-semibold text-amber-900 dark:text-amber-200">
            执棋
          </span>
          <span className="ml-2 text-xs uppercase tracking-wide text-amber-700/70 dark:text-amber-400/70">
            主持人 · 综合
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {summary && (
            <span className={`rounded px-2 py-0.5 text-xs ${VERDICT_COLOR[summary.verdict]}`}>
              {VERDICT_LABEL[summary.verdict]}
            </span>
          )}
          {onOpenDetails && (
            <button
              type="button"
              onClick={onOpenDetails}
              className="rounded border border-amber-700/40 px-1.5 py-0.5 text-[10px] uppercase text-amber-700 hover:border-amber-700 hover:bg-amber-100 dark:border-amber-600/40 dark:text-amber-400 dark:hover:bg-amber-950/40"
              title="查看执棋看到了什么"
            >
              ⓘ 详情
            </button>
          )}
        </div>
      </header>

      {showStream && (
        <div>
          {streamingText ? (
            <Markdown>{streamingText}</Markdown>
          ) : (
            <p className="text-sm text-zinc-400">执棋整理中…</p>
          )}
          <span className="ml-0.5 inline-block h-3 w-1 animate-pulse bg-amber-600 align-middle" />
        </div>
      )}

      {summary && (
        <div className="space-y-5">
          <p className="text-sm leading-relaxed text-zinc-800 dark:text-zinc-200">
            {summary.final_summary}
          </p>

          {summary.consensus.length > 0 && (
            <section>
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                共识
              </h3>
              <ul className="list-inside list-disc space-y-1 text-sm text-zinc-700 dark:text-zinc-300">
                {summary.consensus.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </section>
          )}

          {summary.disagreements.length > 0 && (
            <section>
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                分歧
              </h3>
              <ul className="space-y-3">
                {summary.disagreements.map((d, i) => (
                  <li key={i} className="rounded border border-zinc-200 bg-white p-3 text-sm dark:border-zinc-800 dark:bg-zinc-900">
                    <div className="mb-2 font-medium text-zinc-800 dark:text-zinc-200">
                      {d.point}
                    </div>
                    <div className="space-y-1.5">
                      {Object.entries(d.sides).map(([stance, args]) => (
                        <div key={stance} className="flex gap-2">
                          <span className="shrink-0 rounded bg-zinc-100 px-1.5 py-0.5 text-xs uppercase text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                            {stance}
                          </span>
                          <div className="text-zinc-700 dark:text-zinc-300">
                            <ul className="list-inside list-disc space-y-0.5">
                              {args.map((a, j) => (
                                <li key={j}>{a}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {summary.key_variables.length > 0 && (
            <section>
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                关键变量
              </h3>
              <ul className="list-inside list-decimal space-y-1 text-sm text-zinc-700 dark:text-zinc-300">
                {summary.key_variables.map((v, i) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            </section>
          )}

          {summary.risk_map.length > 0 && (
            <section>
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                风险地图
              </h3>
              <ul className="space-y-2">
                {summary.risk_map.map((r, i) => (
                  <li key={i} className="rounded border border-zinc-200 bg-white p-3 text-sm dark:border-zinc-800 dark:bg-zinc-900">
                    <div className="mb-1 flex items-center gap-2">
                      <SeverityBar level={r.severity} />
                      <span className="text-xs text-zinc-500">严重度 {r.severity}/5</span>
                    </div>
                    <div className="text-zinc-800 dark:text-zinc-200">{r.risk}</div>
                    {r.mitigation && (
                      <div className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">
                        缓释：{r.mitigation}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </article>
  );
}
