"use client";

import { HealthStatus } from "@/components/health-status";

/**
 * 「服务状态」页 —— 三栏布局中点开导航栏第二项时显示。
 * 此页没有会话列表，所以实际是两栏（导航栏 + 本内容）。
 */
export function StatusView() {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {/* 顶栏：与对话页风格统一 */}
      <header className="relative border-b border-parchment-300/60 bg-parchment-50/80 px-4 py-4 backdrop-blur md:px-8 dark:border-walnut-300/20 dark:bg-walnut-900/60">
        <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-gilt-500/60 to-transparent" />
        <div className="flex items-baseline gap-3">
          <h1 className="font-display text-xl font-medium text-walnut-500 dark:text-parchment-100">
            服务状态
          </h1>
          <span className="font-display text-[10px] uppercase tracking-[0.3em] text-gilt-700 dark:text-gilt-300">
            System Health
          </span>
        </div>
      </header>

      {/* 内容 */}
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-8 md:px-8 md:py-10">
        <div className="mx-auto max-w-xl">
          <section className="relative overflow-hidden rounded-sm border border-parchment-300/70 bg-parchment-100/40 p-7 shadow-paper dark:border-walnut-300/30 dark:bg-walnut-700/40">
            <div
              className="pointer-events-none absolute inset-x-0 top-0 h-px"
              style={{
                background:
                  "linear-gradient(90deg, transparent 0%, var(--color-gilt-500) 50%, transparent 100%)",
              }}
            />
            <p className="mb-5 font-display text-[10px] uppercase tracking-[0.3em] text-gilt-700 dark:text-gilt-300">
              运行状况
            </p>
            <HealthStatus />
          </section>

          <p className="mt-5 px-1 font-display text-[12px] italic leading-relaxed text-ink-600 dark:text-parchment-200/60">
            数据链路按优先级自动选择来源：Choice 不可用时无缝降级到 Tushare，再到内置样例，
            顾问始终能拿到可用数据。
          </p>
        </div>
      </div>
    </div>
  );
}
