import { AdvisorSeal } from "@/components/chat/advisor-seal";
import { Markdown } from "@/components/chat/markdown";
import type { CouncilSummary } from "@/lib/types";

const VERDICT_LABEL: Record<CouncilSummary["verdict"], string> = {
  strong_consensus: "强共识",
  weak_consensus: "弱共识",
  split: "明显分歧",
};

// 分歧块中各方立场标签 —— 跟 AdvisorBubble 的 STANCE_LABEL 保持一致
// 后端可能传 "bullish" / "bearish" / "neutral" 等，也可能是 "看多方" 这种自由文本，
// 命中映射时翻译，未命中时回退原文展示
const STANCE_LABEL: Record<string, string> = {
  bullish: "看多",
  bearish: "看空",
  neutral: "中性",
  conditional: "有条件",
};

const STANCE_TONE: Record<string, string> = {
  bullish: "border-sage-500/40 text-sage-700 dark:border-sage-300/40 dark:text-sage-300",
  bearish: "border-vermillion-500/40 text-vermillion-700 dark:border-vermillion-300/40 dark:text-vermillion-300",
  neutral: "border-parchment-300/70 text-walnut-100 dark:border-walnut-300/40 dark:text-parchment-200/80",
  conditional: "border-gilt-500/40 text-gilt-900 dark:border-gilt-300/40 dark:text-gilt-100",
};

function formatStance(raw: string): { label: string; tone: string } {
  const key = raw.toLowerCase().trim();
  return {
    label: STANCE_LABEL[key] ?? raw,
    tone: STANCE_TONE[key] ?? STANCE_TONE.neutral,
  };
}

const VERDICT_TONE: Record<CouncilSummary["verdict"], string> = {
  strong_consensus: "bg-sage-500/15 text-sage-700 ring-sage-500/40 dark:bg-sage-500/20 dark:text-sage-300 dark:ring-sage-300/40",
  weak_consensus: "bg-gilt-500/15 text-gilt-900 ring-gilt-500/40 dark:bg-gilt-500/20 dark:text-gilt-100 dark:ring-gilt-300/40",
  split: "bg-vermillion-500/15 text-vermillion-700 ring-vermillion-500/40 dark:bg-vermillion-500/25 dark:text-vermillion-300 dark:ring-vermillion-300/40",
};

// 检测流式文本是否是结构化 JSON 输出（与 advisor-bubble 同款，含已知 key 兜底）
const STRUCTURED_KEY_PATTERN =
  /"(stance|confidence|summary_for_user|key_points|concerns|what_could_change_my_mind|final_summary|consensus|disagreements|key_variables|risk_map|verdict)"\s*:/;

function looksLikeStructuredJson(text: string): boolean {
  const t = text.trimStart();
  if (t.startsWith("{") || t.startsWith("[")) return true;
  return STRUCTURED_KEY_PATTERN.test(text);
}

// 执棋的流式骨架：比 advisor 多一段（模拟最终输出的 summary + consensus + disagreements）
function ConductorStreamingSkeleton() {
  const barColor = "bg-parchment-300/60 dark:bg-walnut-300/25";
  return (
    <div className="space-y-5">
      <p className="font-display text-[13px] italic text-gilt-700 dark:text-gilt-300/80">
        执棋整理中…
      </p>
      {/* 模拟 final_summary 引用块 */}
      <div className="space-y-2.5 border-l-2 border-gilt-500/40 pl-4 motion-safe:animate-pulse">
        <div className={`h-3 w-[95%] rounded-sm ${barColor}`} />
        <div className={`h-3 w-[88%] rounded-sm ${barColor}`} />
        <div className={`h-3 w-[64%] rounded-sm ${barColor}`} />
      </div>
      {/* 模拟 共识 / 分歧 两段 */}
      <div className="space-y-3 motion-safe:animate-pulse">
        <div className={`h-2.5 w-[26%] rounded-sm ${barColor}`} />
        <div className="space-y-2 pl-3">
          <div className={`h-3 w-[80%] rounded-sm ${barColor}`} />
          <div className={`h-3 w-[70%] rounded-sm ${barColor}`} />
        </div>
        <div className={`h-2.5 w-[26%] rounded-sm ${barColor} mt-3`} />
        <div className="space-y-2 pl-3">
          <div className={`h-3 w-[85%] rounded-sm ${barColor}`} />
          <div className={`h-3 w-[55%] rounded-sm ${barColor}`} />
        </div>
      </div>
    </div>
  );
}

function SeverityBar({ level }: { level: number }) {
  return (
    <span className="inline-flex items-center gap-[2px]">
      {[1, 2, 3, 4, 5].map((n) => (
        <span
          key={n}
          className={`h-1 w-2.5 ${
            n <= level
              ? n >= 4
                ? "bg-vermillion-500"
                : n === 3
                  ? "bg-gilt-500"
                  : "bg-sage-500"
              : "bg-parchment-300/80 dark:bg-walnut-300/40"
          }`}
        />
      ))}
    </span>
  );
}

export type ConductorSummaryProps = {
  streamingText: string;
  summary: CouncilSummary | null;
  onOpenDetails?: () => void;
};

export function ConductorSummary({
  streamingText,
  summary,
  onOpenDetails,
}: ConductorSummaryProps) {
  const showStream = !summary;

  return (
    <article className="relative overflow-hidden rounded-2xl border border-gilt-500/40 bg-parchment-100/60 px-6 py-6 shadow-paper-lg dark:border-gilt-500/30 dark:bg-walnut-700/60">
      {/* 金箔细线装饰 (顶 + 底) */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, var(--color-gilt-500) 50%, transparent 100%)",
        }}
      />
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-px"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, var(--color-gilt-500) 50%, transparent 100%)",
        }}
      />

      <header className="mb-5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <AdvisorSeal char="执" color="var(--color-gilt-500)" size="lg" conductor />
          <div className="flex items-baseline gap-3">
            <span className="font-display text-2xl font-medium leading-none text-gilt-900 dark:text-gilt-100">
              执棋
            </span>
            <span className="font-display text-[11px] uppercase tracking-[0.3em] text-gilt-700/80 dark:text-gilt-300/70">
              主持人 · 综合
            </span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {summary && (
            <span
              className={`inline-flex items-center rounded-sm px-2 py-0.5 font-display text-[11px] ring-1 ring-inset ${VERDICT_TONE[summary.verdict]}`}
            >
              {VERDICT_LABEL[summary.verdict]}
            </span>
          )}
          {onOpenDetails && (
            <button
              type="button"
              onClick={onOpenDetails}
              className="rounded-sm border border-gilt-500/50 px-1.5 py-0.5 font-display text-[10px] tracking-wider text-gilt-700 transition-colors hover:border-gilt-500 hover:bg-gilt-500/10 dark:border-gilt-300/40 dark:text-gilt-100 dark:hover:bg-gilt-500/15"
              title="查看执棋看到了什么"
            >
              详情
            </button>
          )}
        </div>
      </header>

      {showStream ? (
        <div className="text-[14px] leading-7 text-ink-900 dark:text-parchment-100">
          {streamingText ? (
            looksLikeStructuredJson(streamingText) ? (
              // 结构化综合输出 —— 屏蔽原 JSON，骨架占位
              <ConductorStreamingSkeleton />
            ) : (
              // 自然语言铺垫，正常 Markdown 渲染
              <>
                <Markdown>{streamingText}</Markdown>
                <span className="ml-0.5 inline-block h-3 w-[2px] bg-gilt-500 align-middle motion-safe:animate-pulse" />
              </>
            )
          ) : (
            <p className="font-display italic text-walnut-50/60 dark:text-parchment-200/50">
              执棋整理中…
            </p>
          )}
        </div>
      ) : (
        summary && (
          <div className="space-y-6">
            {/* 总结：金箔边竖条 + 宋体大字 */}
            <blockquote className="border-l-2 border-gilt-500 pl-4 font-display text-[15.5px] leading-relaxed not-italic text-ink-900 dark:text-parchment-100">
              {summary.final_summary}
            </blockquote>

            {summary.consensus.length > 0 && (
              <Section title="共识">
                <ul className="list-inside list-[square] marker:text-sage-500 space-y-1 text-[13.5px] leading-relaxed text-ink-600 dark:text-parchment-200/80">
                  {summary.consensus.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </Section>
            )}

            {summary.disagreements.length > 0 && (
              <Section title="分歧">
                <ul className="space-y-3">
                  {summary.disagreements.map((d, i) => (
                    <li
                      key={i}
                      className="rounded-sm border border-parchment-300/70 bg-parchment-50/80 p-4 text-[13.5px] dark:border-walnut-300/30 dark:bg-walnut-900/40"
                    >
                      <div className="mb-2 font-display font-medium text-ink-900 dark:text-parchment-100">
                        {d.point}
                      </div>
                      <div className="space-y-2">
                        {Object.entries(d.sides).map(([stance, args]) => {
                          const { label, tone } = formatStance(stance);
                          return (
                            <div key={stance} className="flex gap-3">
                              <span
                                className={`mt-0.5 shrink-0 rounded-sm border px-1.5 py-0.5 font-display text-[10px] tracking-wider ${tone}`}
                              >
                                {label}
                              </span>
                              <ul className="list-inside list-[square] marker:text-walnut-50/60 space-y-0.5 text-ink-600 dark:text-parchment-200/80">
                                {args.map((a, j) => (
                                  <li key={j}>{a}</li>
                                ))}
                              </ul>
                            </div>
                          );
                        })}
                      </div>
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {summary.key_variables.length > 0 && (
              <Section title="关键变量">
                <ol className="list-inside list-decimal marker:font-display marker:text-gilt-700 space-y-1 text-[13.5px] leading-relaxed text-ink-600 dark:text-parchment-200/80">
                  {summary.key_variables.map((v, i) => (
                    <li key={i}>{v}</li>
                  ))}
                </ol>
              </Section>
            )}

            {summary.risk_map.length > 0 && (
              <Section title="风险地图">
                <ul className="space-y-2.5">
                  {summary.risk_map.map((r, i) => (
                    <li
                      key={i}
                      className="rounded-sm border border-parchment-300/70 bg-parchment-50/80 p-3 text-[13.5px] dark:border-walnut-300/30 dark:bg-walnut-900/40"
                    >
                      <div className="mb-1.5 flex items-center gap-2">
                        <SeverityBar level={r.severity} />
                      </div>
                      <div className="text-ink-900 dark:text-parchment-100">
                        {r.risk}
                      </div>
                      {r.mitigation && (
                        <div className="mt-1 text-[12px] text-ink-600 dark:text-parchment-200/70">
                          缓释：{r.mitigation}
                        </div>
                      )}
                    </li>
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
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h3 className="mb-2.5 font-display text-[11px] uppercase tracking-[0.3em] text-walnut-100 dark:text-parchment-200/80">
        {title}
      </h3>
      {children}
    </section>
  );
}
