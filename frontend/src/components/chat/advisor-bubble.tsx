import { Markdown } from "@/components/chat/markdown";
import type { AdvisorOpinion } from "@/lib/types";

const STANCE_LABEL: Record<AdvisorOpinion["stance"], string> = {
  bullish: "看多",
  neutral: "中性",
  bearish: "看空",
  conditional: "有条件",
};

const STANCE_STYLE: Record<AdvisorOpinion["stance"], string> = {
  bullish: "bg-sage-500/15 text-sage-700 ring-sage-500/30 dark:bg-sage-500/20 dark:text-sage-300 dark:ring-sage-300/30",
  neutral: "bg-walnut-50/10 text-walnut-500 ring-walnut-50/30 dark:bg-parchment-100/10 dark:text-parchment-200 dark:ring-parchment-300/20",
  bearish: "bg-vermillion-500/15 text-vermillion-700 ring-vermillion-500/30 dark:bg-vermillion-500/25 dark:text-vermillion-300 dark:ring-vermillion-300/30",
  conditional: "bg-gilt-500/15 text-gilt-900 ring-gilt-500/35 dark:bg-gilt-500/20 dark:text-gilt-100 dark:ring-gilt-300/30",
};

function skillShortName(path: string): string {
  return path.split("/").pop() ?? path;
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
      className="relative rounded-sm border border-parchment-300/70 bg-parchment-100/40 px-6 py-5 shadow-paper transition-shadow hover:shadow-paper-lg dark:border-walnut-300/30 dark:bg-walnut-700/40"
    >
      {/* 印章 / 顾问标识：左上角竖排，半透明衬底 */}
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex items-baseline gap-3">
          <span
            className="font-display text-xl font-medium leading-none"
            style={{ color }}
          >
            {display}
          </span>
          <span
            className="font-display text-[11px] uppercase tracking-[0.2em]"
            style={{ color }}
          >
            {role}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {opinion && (
            <>
              <span
                className={`inline-flex items-center rounded-sm px-2 py-0.5 font-display text-[11px] ring-1 ring-inset ${STANCE_STYLE[opinion.stance]}`}
              >
                {STANCE_LABEL[opinion.stance]}
              </span>
              <ConfidenceMeter value={opinion.confidence} />
            </>
          )}
          {onOpenDetails && (
            <button
              type="button"
              onClick={onOpenDetails}
              className="rounded-sm border border-parchment-300/80 px-1.5 py-0.5 font-display text-[10px] tracking-wider text-walnut-100 transition-colors hover:border-gilt-500 hover:text-gilt-700 dark:border-walnut-300/40 dark:text-parchment-200 dark:hover:border-gilt-300 dark:hover:text-gilt-100"
              title="查看顾问看到了什么"
            >
              详情
            </button>
          )}
        </div>
      </div>

      {/* 已激活的 Skills 标签 —— 安静地挂在 header 下面 */}
      {activeSkills && activeSkills.length > 0 && (
        <div className="mb-4 -mt-2 flex flex-wrap gap-1">
          {activeSkills.map((s) => (
            <span
              key={s}
              title={s}
              className="rounded-sm bg-parchment-200/60 px-1.5 py-0.5 font-mono text-[10px] tracking-wide text-walnut-50 dark:bg-walnut-300/30 dark:text-parchment-200"
            >
              {skillShortName(s)}
            </span>
          ))}
        </div>
      )}

      {showStream ? (
        <div className="text-[14px] leading-7 text-ink-900 dark:text-parchment-100">
          {streamingText ? (
            <Markdown>{streamingText}</Markdown>
          ) : (
            <p className="font-display italic text-walnut-50/60 dark:text-parchment-200/50">
              静候发言…
            </p>
          )}
          <span
            className="ml-0.5 inline-block h-3 w-[2px] animate-pulse align-middle"
            style={{ backgroundColor: color }}
          />
        </div>
      ) : (
        opinion && (
          <div className="space-y-5">
            {/* 总结：宋体引用样式 */}
            <blockquote
              className="border-l-2 border-gilt-500/60 pl-4 font-display text-[15px] leading-relaxed not-italic text-ink-900 dark:text-parchment-100"
            >
              {opinion.summary_for_user}
            </blockquote>

            {opinion.key_points.length > 0 && (
              <Section title="核心观点">
                <ul className="space-y-2.5">
                  {opinion.key_points.map((p, i) => (
                    <li key={i}>
                      <div className="font-medium text-ink-900 dark:text-parchment-100">
                        · {p.claim}
                      </div>
                      <div className="mt-0.5 ml-3 text-[13.5px] leading-relaxed text-ink-600 dark:text-parchment-200/80">
                        {p.detail}
                      </div>
                      {p.source_tool && (
                        <code className="ml-3 text-[11px] text-walnut-50 dark:text-parchment-300/70">
                          source: {p.source_tool}
                        </code>
                      )}
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {opinion.concerns.length > 0 && (
              <Section title="主要风险" tone="vermillion">
                <ul className="list-inside list-[square] marker:text-vermillion-500 space-y-1 text-[13.5px] leading-relaxed text-ink-600 dark:text-parchment-200/80">
                  {opinion.concerns.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </Section>
            )}

            {opinion.what_could_change_my_mind.length > 0 && (
              <Section title="变心条件">
                <ul className="list-inside list-[square] marker:text-gilt-500 space-y-1 text-[13.5px] leading-relaxed text-ink-600 dark:text-parchment-200/80">
                  {opinion.what_could_change_my_mind.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </Section>
            )}
          </div>
        )
      )}
    </article>
  );
}

function Section({
  title,
  tone,
  children,
}: {
  title: string;
  tone?: "vermillion";
  children: React.ReactNode;
}) {
  const titleColor =
    tone === "vermillion"
      ? "text-vermillion-700 dark:text-vermillion-300"
      : "text-walnut-100 dark:text-parchment-200/80";
  return (
    <section>
      <h3
        className={`mb-2 font-display text-[11px] uppercase tracking-[0.25em] ${titleColor}`}
      >
        {title}
      </h3>
      {children}
    </section>
  );
}

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value));
  const dots = 5;
  const filled = Math.round(pct * dots);
  return (
    <span className="flex items-center gap-1.5" title={`置信度 ${(pct * 100).toFixed(0)}%`}>
      <span className="font-display text-[10px] uppercase tracking-wider text-walnut-50 dark:text-parchment-300/70">
        信
      </span>
      <span className="flex gap-[2px]">
        {Array.from({ length: dots }).map((_, i) => (
          <span
            key={i}
            className={`h-1 w-1 rounded-full ${
              i < filled ? "bg-gilt-500" : "bg-parchment-300/80 dark:bg-walnut-300/40"
            }`}
          />
        ))}
      </span>
    </span>
  );
}
