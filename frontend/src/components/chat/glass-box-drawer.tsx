"use client";

import { useEffect } from "react";

import { AdvisorSeal } from "@/components/chat/advisor-seal";
import type { ToolCall } from "@/components/chat/tool-trace";
import type { AdvisorOpinion, CouncilSummary } from "@/lib/types";

export type GlassBoxData =
  | {
      kind: "advisor";
      name: string;
      display: string;
      role: string;
      color: string;
      activeSkills: string[];
      toolCalls: ToolCall[];
      opinion: AdvisorOpinion | null;
      model?: string | null;
      tokensIn?: number | null;
      tokensOut?: number | null;
    }
  | {
      kind: "conductor";
      advisorsContributed: string[];
      streamingText: string;
      summary: CouncilSummary | null;
      model?: string | null;
      tokensIn?: number | null;
      tokensOut?: number | null;
    };

export type GlassBoxDrawerProps = {
  data: GlassBoxData | null;
  onClose: () => void;
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-6">
      <h3 className="mb-2.5 font-display text-[11px] uppercase tracking-[0.3em] text-walnut-100 dark:text-parchment-200/80">
        {title}
      </h3>
      <div>{children}</div>
    </section>
  );
}

function JsonBlock({ data }: { data: unknown }) {
  return (
    <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-sm border border-parchment-300/60 bg-parchment-50/80 p-3 font-mono text-[11px] leading-snug text-ink-600 dark:border-walnut-300/30 dark:bg-walnut-900/40 dark:text-parchment-200/80">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 py-1.5 text-[13px] sm:grid sm:grid-cols-[110px_1fr] sm:gap-2">
      <span className="font-display text-walnut-100 dark:text-parchment-200/70">{label}</span>
      <span className="text-ink-900 dark:text-parchment-100">{value}</span>
    </div>
  );
}

function AdvisorView({ data }: { data: Extract<GlassBoxData, { kind: "advisor" }> }) {
  return (
    <>
      <Section title="元信息">
        <MetaRow label="顾问" value={`${data.display} · ${data.role} (${data.name})`} />
        <MetaRow
          label="模型"
          value={
            data.model ? (
              <code className="font-mono text-[12px]">{data.model}</code>
            ) : (
              <em className="font-display text-walnut-50/60 dark:text-parchment-200/50">未知</em>
            )
          }
        />
        {(data.tokensIn || data.tokensOut) && (
          <MetaRow
            label="Token 用量"
            value={
              <span className="font-mono text-[12px]">
                in {data.tokensIn ?? 0} · out {data.tokensOut ?? 0} · total{" "}
                {(data.tokensIn ?? 0) + (data.tokensOut ?? 0)}
              </span>
            }
          />
        )}
        <MetaRow
          label="颜色"
          value={
            <span className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-sm"
                style={{ background: data.color }}
              />
              <code className="font-mono text-[11px]">{data.color}</code>
            </span>
          }
        />
      </Section>

      <Section title={`Active Skills (${data.activeSkills.length})`}>
        {data.activeSkills.length === 0 ? (
          <p className="font-display text-[12px] italic text-walnut-50/60 dark:text-parchment-200/50">
            本轮未激活任何 Skills（可能来自旧历史会话）
          </p>
        ) : (
          <ul className="space-y-1">
            {data.activeSkills.map((s) => (
              <li
                key={s}
                className="rounded-sm bg-parchment-50/80 px-2 py-1 font-mono text-[11px] text-walnut-500 dark:bg-walnut-900/40 dark:text-parchment-200"
              >
                {s}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title={`工具调用 (${data.toolCalls.length})`}>
        {data.toolCalls.length === 0 ? (
          <p className="font-display text-[12px] italic text-walnut-50/60 dark:text-parchment-200/50">
            本轮未调用任何工具
          </p>
        ) : (
          <ul className="space-y-3">
            {data.toolCalls.map((tc, i) => (
              <li
                key={tc.id || i}
                className="rounded-sm border border-parchment-300/60 bg-parchment-50/40 p-2.5 dark:border-walnut-300/30 dark:bg-walnut-900/30"
              >
                <div className="mb-1.5 font-mono text-[12px] text-gilt-700 dark:text-gilt-300">
                  {tc.tool}
                </div>
                <div className="font-display text-[10px] uppercase tracking-wider text-walnut-100 dark:text-parchment-200/60">
                  args
                </div>
                <JsonBlock data={tc.args} />
                <div className="mt-2 font-display text-[10px] uppercase tracking-wider text-walnut-100 dark:text-parchment-200/60">
                  result
                </div>
                {tc.result ? (
                  <JsonBlock data={tc.result} />
                ) : (
                  <p className="font-display text-[11px] italic text-walnut-50/60 dark:text-parchment-200/50">
                    (无结果或尚未返回)
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="结构化观点 (AdvisorOpinion)">
        {data.opinion ? (
          <JsonBlock data={data.opinion} />
        ) : (
          <p className="font-display text-[12px] italic text-walnut-50/60 dark:text-parchment-200/50">
            未产出结构化观点
          </p>
        )}
      </Section>
    </>
  );
}

function ConductorView({
  data,
}: {
  data: Extract<GlassBoxData, { kind: "conductor" }>;
}) {
  return (
    <>
      <Section title="元信息">
        <MetaRow label="角色" value="执棋 · 主持人 / 综合者" />
        <MetaRow
          label="模型"
          value={
            data.model ? (
              <code className="font-mono text-[12px]">{data.model}</code>
            ) : (
              <em className="font-display text-walnut-50/60 dark:text-parchment-200/50">未知</em>
            )
          }
        />
        {(data.tokensIn || data.tokensOut) && (
          <MetaRow
            label="Token 用量"
            value={
              <span className="font-mono text-[12px]">
                in {data.tokensIn ?? 0} · out {data.tokensOut ?? 0} · total{" "}
                {(data.tokensIn ?? 0) + (data.tokensOut ?? 0)}
              </span>
            }
          />
        )}
      </Section>

      <Section title={`参与顾问 (${data.advisorsContributed.length})`}>
        {data.advisorsContributed.length === 0 ? (
          <p className="font-display text-[12px] italic text-walnut-50/60 dark:text-parchment-200/50">
            无
          </p>
        ) : (
          <ul className="flex flex-wrap gap-1.5">
            {data.advisorsContributed.map((n) => (
              <li
                key={n}
                className="rounded-sm border border-gilt-500/40 bg-gilt-500/10 px-2 py-0.5 font-mono text-[11px] text-gilt-900 dark:border-gilt-300/40 dark:bg-gilt-500/15 dark:text-gilt-100"
              >
                {n}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="结构化综合 (CouncilSummary)">
        {data.summary ? (
          <JsonBlock data={data.summary} />
        ) : (
          <p className="font-display text-[12px] italic text-walnut-50/60 dark:text-parchment-200/50">
            综合中或未产出
          </p>
        )}
      </Section>

      {data.streamingText && (
        <Section title="原始 Prose">
          <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-sm border border-parchment-300/60 bg-parchment-50/80 p-3 font-mono text-[11px] text-ink-600 dark:border-walnut-300/30 dark:bg-walnut-900/40 dark:text-parchment-200/80">
            {data.streamingText}
          </pre>
        </Section>
      )}
    </>
  );
}

export function GlassBoxDrawer({ data, onClose }: GlassBoxDrawerProps) {
  useEffect(() => {
    if (!data) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [data, onClose]);

  if (!data) return null;

  const title =
    data.kind === "advisor"
      ? `${data.display}`
      : "执棋";
  const subtitle =
    data.kind === "advisor"
      ? `透明面板 · ${data.role}`
      : "透明面板 · 主持人 / 综合者";

  const titleColor = data.kind === "advisor" ? data.color : "var(--color-gilt-700)";

  return (
    <div className="fixed inset-0 z-50 flex">
      <button
        type="button"
        onClick={onClose}
        aria-label="关闭详情"
        className="flex-1 bg-walnut-900/30 backdrop-blur-[2px]"
      />
      <aside className="relative flex w-[520px] max-w-full flex-col border-l border-gilt-500/30 bg-parchment-50 shadow-paper-lg dark:border-gilt-500/20 dark:bg-walnut-900">
        <div className="pointer-events-none absolute inset-y-0 left-0 w-px bg-gradient-to-b from-transparent via-gilt-500/60 to-transparent" />

        <header className="border-b border-parchment-300/60 px-4 py-4 md:px-6 md:py-5 dark:border-walnut-300/20">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <AdvisorSeal
                char={title.charAt(0)}
                color={data.kind === "advisor" ? data.color : "var(--color-gilt-500)"}
                size="md"
                conductor={data.kind === "conductor"}
              />
              <div>
                <p className="font-display text-[10px] uppercase tracking-[0.3em] text-gilt-700 dark:text-gilt-300">
                  {subtitle}
                </p>
                <h2
                  className="mt-1 font-display text-2xl"
                  style={{ color: titleColor }}
                >
                  {title}
                </h2>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-sm border border-parchment-300/70 px-2 py-1 font-display text-sm text-walnut-100 transition-colors hover:border-gilt-500 hover:text-gilt-700 dark:border-walnut-300/40 dark:text-parchment-200 dark:hover:border-gilt-300 dark:hover:text-gilt-100"
              aria-label="关闭"
            >
              ✕
            </button>
          </div>
        </header>
        <div className="flex-1 overflow-y-auto px-4 py-5 md:px-6 md:py-6">
          {data.kind === "advisor" ? (
            <AdvisorView data={data} />
          ) : (
            <ConductorView data={data} />
          )}
        </div>
      </aside>
    </div>
  );
}
