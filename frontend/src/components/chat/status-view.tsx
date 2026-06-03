"use client";

import { useCallback, useEffect, useState } from "react";

import { apiGet } from "@/lib/api";

type ChoiceStatus = { configured: boolean; reachable: boolean; logged_in: boolean };
type Health = {
  status: string;
  db: boolean;
  redis: boolean;
  data_source?: {
    chain: string[];
    choice: ChoiceStatus;
    tushare: { configured: boolean };
  };
};

type Tone = "ok" | "warn" | "down" | "idle";

const PROVIDER_LABEL: Record<string, string> = {
  choice: "东方财富 Choice",
  tushare: "Tushare",
  mock: "内置样例",
};

const DOT: Record<Tone, string> = {
  ok: "bg-sage-500",
  warn: "bg-gilt-500",
  down: "bg-vermillion-500",
  idle: "bg-walnut-50/40 dark:bg-parchment-200/30",
};

function choiceState(c: ChoiceStatus): { note: string; tone: Tone } {
  if (!c.configured) return { note: "未启用", tone: "idle" };
  if (!c.reachable) return { note: "网关离线", tone: "down" };
  if (!c.logged_in) return { note: "待激活", tone: "warn" };
  return { note: "已就绪", tone: "ok" };
}

export function StatusView() {
  const [data, setData] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const h = await apiGet<Health>("/api/health");
      setData(h);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 挂载拉取一次；setState 在 await 之后，非同步，规则误报
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, [refresh]);

  const ds = data?.data_source;
  const choice = ds?.choice;
  const cs = choice ? choiceState(choice) : null;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {/* 顶栏 */}
      <header className="relative flex items-center justify-between gap-3 border-b border-parchment-300/60 bg-parchment-50/80 px-4 py-4 backdrop-blur md:px-8 dark:border-walnut-300/20 dark:bg-walnut-900/60">
        <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-gilt-500/60 to-transparent" />
        <div className="flex items-baseline gap-3">
          <h1 className="font-display text-xl font-medium text-walnut-500 dark:text-parchment-100">
            服务状态
          </h1>
          <span className="font-display text-[10px] uppercase tracking-[0.3em] text-gilt-700 dark:text-gilt-300">
            System Health
          </span>
        </div>
        <button
          type="button"
          onClick={refresh}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-parchment-300/70 px-3 py-1.5 font-display text-[12px] tracking-wider text-walnut-100 transition-colors hover:border-gilt-500 hover:text-gilt-700 disabled:opacity-50 dark:border-walnut-300/30 dark:text-parchment-200/70 dark:hover:border-gilt-300 dark:hover:text-gilt-300"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            className={`h-3.5 w-3.5 ${loading ? "motion-safe:animate-spin" : ""}`}
          >
            <path d="M21 12a9 9 0 1 1-2.64-6.36M21 4v4h-4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          刷新
        </button>
      </header>

      {/* 内容 */}
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-8 md:px-8 md:py-10">
        <div className="mx-auto max-w-4xl space-y-8">
          {error ? (
            <div className="rounded-xl border border-vermillion-500/30 bg-vermillion-500/[0.08] p-4 font-display text-[13px] text-vermillion-700 dark:border-vermillion-300/30 dark:text-vermillion-300">
              后端无响应：{error}
            </div>
          ) : !data ? (
            <p className="font-display text-[13px] italic text-walnut-50/70 dark:text-parchment-200/50">
              正在确认…
            </p>
          ) : (
            <>
              {/* 核心服务 */}
              <Section title="核心服务">
                <div className="grid gap-3 sm:grid-cols-3">
                  <StatusCard label="API 服务" tone={data.status === "ok" ? "ok" : "down"} note={data.status === "ok" ? "正常" : "异常"} mono="api" />
                  <StatusCard label="PostgreSQL" tone={data.db ? "ok" : "down"} note={data.db ? "已连接" : "断开"} mono="postgres" />
                  <StatusCard label="Redis 缓存" tone={data.redis ? "ok" : "down"} note={data.redis ? "已连接" : "断开"} mono="redis" />
                </div>
              </Section>

              {/* 数据源 */}
              <Section title="数据源">
                <div className="grid gap-3 sm:grid-cols-3">
                  <StatusCard
                    label="东方财富 Choice"
                    tone={cs?.tone ?? "idle"}
                    note={cs?.note ?? "—"}
                    mono="choice · 行情/K线/宏观/行业"
                  />
                  <StatusCard
                    label="Tushare"
                    tone={ds?.tushare.configured ? "ok" : "idle"}
                    note={ds?.tushare.configured ? "已配置" : "未配置"}
                    mono="tushare · 行情/宏观/申万行业"
                  />
                  <StatusCard label="内置样例" tone="ok" note="始终可用" mono="mock · 兜底" />
                </div>
              </Section>

              {/* 数据链路 */}
              {ds && ds.chain.length > 0 && (
                <Section title="数据链路（按优先级）">
                  <div className="flex flex-wrap items-center gap-2 rounded-xl border border-parchment-300/60 bg-parchment-100/30 p-4 dark:border-walnut-300/25 dark:bg-walnut-700/25">
                    {ds.chain.map((p, i) => (
                      <span key={p} className="flex items-center gap-2">
                        {i > 0 && (
                          <span className="font-mono text-gilt-700/70 dark:text-gilt-300/60">→</span>
                        )}
                        <span
                          className={`rounded-lg px-3 py-1.5 font-display text-[13px] ${
                            i === 0
                              ? "bg-gilt-500/15 text-gilt-700 ring-1 ring-inset ring-gilt-500/35 dark:text-gilt-200 dark:ring-gilt-300/30"
                              : "text-walnut-100 dark:text-parchment-200/60"
                          }`}
                        >
                          {PROVIDER_LABEL[p] ?? p}
                        </span>
                      </span>
                    ))}
                  </div>
                  <p className="mt-3 px-1 font-display text-[12px] italic leading-relaxed text-ink-600 dark:text-parchment-200/60">
                    上游不可用时自动降级到下一级，顾问始终能拿到可用数据；首选源会优先返回真实行情。
                  </p>
                </Section>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-3 font-display text-[11px] uppercase tracking-[0.25em] text-gilt-700 dark:text-gilt-300">
        {title}
      </h2>
      {children}
    </section>
  );
}

function StatusCard({
  label,
  tone,
  note,
  mono,
}: {
  label: string;
  tone: Tone;
  note: string;
  mono: string;
}) {
  return (
    <div className="rounded-xl border border-parchment-300/60 bg-parchment-100/40 px-4 py-3.5 shadow-paper dark:border-walnut-300/25 dark:bg-walnut-700/30">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            {tone === "ok" && (
              <span className={`absolute inset-0 rounded-full ${DOT[tone]} opacity-50 motion-safe:animate-ping`} />
            )}
            <span className={`relative inline-block h-2 w-2 rounded-full ${DOT[tone]}`} />
          </span>
          <span className="font-display text-[14px] text-walnut-500 dark:text-parchment-100">{label}</span>
        </span>
        <span
          className={`font-display text-[12px] ${
            tone === "down"
              ? "text-vermillion-700 dark:text-vermillion-300"
              : tone === "warn"
                ? "text-gilt-700 dark:text-gilt-300"
                : tone === "idle"
                  ? "text-walnut-50/70 dark:text-parchment-200/50"
                  : "text-sage-700 dark:text-sage-300"
          }`}
        >
          {note}
        </span>
      </div>
      <p className="mt-1.5 font-mono text-[10px] text-ink-400 dark:text-parchment-200/40">{mono}</p>
    </div>
  );
}
