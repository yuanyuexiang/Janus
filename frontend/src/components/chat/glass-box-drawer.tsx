"use client";

import { useEffect } from "react";

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
    }
  | {
      kind: "conductor";
      advisorsContributed: string[];
      streamingText: string;
      summary: CouncilSummary | null;
      model?: string | null;
    };

export type GlassBoxDrawerProps = {
  data: GlassBoxData | null;
  onClose: () => void;
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-5">
      <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-zinc-500">
        {title}
      </h3>
      <div>{children}</div>
    </section>
  );
}

function JsonBlock({ data }: { data: unknown }) {
  return (
    <pre className="overflow-x-auto rounded bg-zinc-100 p-3 font-mono text-[11px] leading-snug text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[110px_1fr] gap-2 py-1 text-sm">
      <span className="text-zinc-500">{label}</span>
      <span className="text-zinc-800 dark:text-zinc-200">{value}</span>
    </div>
  );
}

function AdvisorView({ data }: { data: Extract<GlassBoxData, { kind: "advisor" }> }) {
  return (
    <>
      <Section title="元信息">
        <MetaRow label="顾问" value={`${data.display} · ${data.role} (${data.name})`} />
        <MetaRow label="模型" value={data.model ?? <em className="text-zinc-400">未知</em>} />
        <MetaRow
          label="颜色标识"
          value={
            <span className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded"
                style={{ background: data.color }}
              />
              <code className="text-xs">{data.color}</code>
            </span>
          }
        />
      </Section>

      <Section title={`Active Skills (${data.activeSkills.length})`}>
        {data.activeSkills.length === 0 ? (
          <p className="text-sm text-zinc-400">本轮未激活任何 Skills（可能来自旧历史会话）</p>
        ) : (
          <ul className="space-y-1">
            {data.activeSkills.map((s) => (
              <li
                key={s}
                className="rounded bg-zinc-50 px-2 py-1 font-mono text-xs text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300"
              >
                {s}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title={`工具调用 (${data.toolCalls.length})`}>
        {data.toolCalls.length === 0 ? (
          <p className="text-sm text-zinc-400">本轮未调用任何工具</p>
        ) : (
          <ul className="space-y-3">
            {data.toolCalls.map((tc, i) => (
              <li
                key={tc.id || i}
                className="rounded border border-zinc-200 p-2 dark:border-zinc-800"
              >
                <div className="mb-1 font-mono text-xs text-amber-700 dark:text-amber-400">
                  {tc.tool}
                </div>
                <div className="text-[10px] uppercase tracking-wide text-zinc-400">args</div>
                <JsonBlock data={tc.args} />
                <div className="mt-2 text-[10px] uppercase tracking-wide text-zinc-400">
                  result
                </div>
                {tc.result ? (
                  <JsonBlock data={tc.result} />
                ) : (
                  <p className="text-xs text-zinc-400">(无结果或尚未返回)</p>
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
          <p className="text-sm text-zinc-400">未产出结构化观点</p>
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
        <MetaRow label="模型" value={data.model ?? <em className="text-zinc-400">未知</em>} />
      </Section>

      <Section title={`参与顾问 (${data.advisorsContributed.length})`}>
        {data.advisorsContributed.length === 0 ? (
          <p className="text-sm text-zinc-400">无</p>
        ) : (
          <ul className="flex flex-wrap gap-1">
            {data.advisorsContributed.map((n) => (
              <li
                key={n}
                className="rounded bg-amber-50 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
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
          <p className="text-sm text-zinc-400">综合中或未产出</p>
        )}
      </Section>

      {data.streamingText && (
        <Section title="原始 Prose">
          <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded bg-zinc-100 p-3 font-mono text-[11px] text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
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
      ? `Glass Box · ${data.display}`
      : "Glass Box · 执棋";

  const titleColor = data.kind === "advisor" ? data.color : "#A16207";

  return (
    <div className="fixed inset-0 z-50 flex">
      <button
        type="button"
        onClick={onClose}
        aria-label="关闭详情"
        className="flex-1 bg-zinc-900/30 backdrop-blur-[1px]"
      />
      <aside className="flex w-[480px] max-w-full flex-col border-l border-zinc-200 bg-white shadow-xl dark:border-zinc-800 dark:bg-zinc-950">
        <header
          className="flex items-center justify-between border-b border-zinc-200 px-4 py-3 dark:border-zinc-800"
          style={{ borderTopColor: titleColor, borderTopWidth: 3 }}
        >
          <div>
            <p className="text-[10px] uppercase tracking-widest text-zinc-500">
              详情 · 透明面板
            </p>
            <h2 className="text-base font-semibold" style={{ color: titleColor }}>
              {title}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
            aria-label="关闭"
          >
            ✕
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-4 py-4">
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
