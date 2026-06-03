import Link from "next/link";

import { HealthStatus } from "@/components/health-status";

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-hidden">
      {/* 边角装饰：两道金箔细线，议事厅入口感 */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gilt-500/40 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-gilt-500/40 to-transparent" />

      <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-8 py-20">
        {/* 标识：双圈金印 + 主副标题 */}
        <div className="mb-12 flex items-center gap-4">
          <div className="relative flex h-12 w-12 items-center justify-center">
            <div className="absolute inset-0 rounded-full border border-gilt-500/50" />
            <div className="absolute inset-1.5 rounded-full border border-gilt-500/30" />
            <span className="font-display text-xl text-gilt-700 dark:text-gilt-300">桌</span>
          </div>
          <div>
            <p className="font-display text-[11px] uppercase tracking-[0.3em] text-gilt-700 dark:text-gilt-300">
              Atlas Council
            </p>
            <h1 className="font-display text-3xl font-medium leading-tight text-walnut-500 dark:text-parchment-100">
              圆桌投研
            </h1>
          </div>
        </div>

        {/* 引语 */}
        <blockquote className="mb-16 max-w-xl border-l-2 border-gilt-500/60 pl-5 font-display text-[18px] leading-relaxed not-italic text-ink-900 dark:text-parchment-100">
          一桌专家智囊团，陪你看清每一笔投资。
          <span className="mt-3 block font-display text-[13px] italic text-ink-600 dark:text-parchment-200/70">
            把「七位风格各异的专家围坐讨论」变成你随时可用的私人智库。
          </span>
        </blockquote>

        {/* 卡组：议事入口 + 状态 */}
        <div className="grid gap-6 sm:grid-cols-[2fr_1fr]">
          <section className="relative overflow-hidden rounded-sm border border-parchment-300/70 bg-parchment-100/40 p-7 shadow-paper dark:border-walnut-300/30 dark:bg-walnut-700/40">
            <div
              className="pointer-events-none absolute inset-x-0 top-0 h-px"
              style={{
                background:
                  "linear-gradient(90deg, transparent 0%, var(--color-gilt-500) 50%, transparent 100%)",
              }}
            />
            <p className="mb-2 font-display text-[10px] uppercase tracking-[0.3em] text-gilt-700 dark:text-gilt-300">
              入席议事
            </p>
            <h2 className="mb-3 font-display text-2xl text-walnut-500 dark:text-parchment-100">
              进入圆桌
            </h2>
            <p className="mb-6 font-display text-[13px] italic leading-relaxed text-ink-600 dark:text-parchment-200/70">
              韬叔（宏观）· 岚姐（行业）· 明哥（价值）· 锐锋（趋势）· 冷川（风险）· 零度（量化），
              执棋（主持）最终综合。
            </p>
            <Link
              href="/chat"
              className="group inline-flex items-center gap-2 rounded-sm border border-walnut-500 bg-walnut-500 px-5 py-2.5 font-display text-[13px] tracking-wider text-parchment-100 no-underline shadow-paper transition-all hover:border-walnut-700 hover:bg-walnut-700 hover:shadow-paper-lg dark:border-gilt-500 dark:bg-gilt-500 dark:text-walnut-900 dark:hover:bg-gilt-300 nasdaq:border-gilt-500 nasdaq:bg-gilt-500 nasdaq:text-parchment-50 nasdaq:hover:bg-gilt-300"
            >
              进入对话
              <span className="text-base leading-none transition-transform group-hover:translate-x-0.5">
                →
              </span>
            </Link>
          </section>

          <section className="relative overflow-hidden rounded-sm border border-parchment-300/70 bg-parchment-100/30 p-6 shadow-paper dark:border-walnut-300/30 dark:bg-walnut-700/30">
            <p className="mb-3 font-display text-[10px] uppercase tracking-[0.3em] text-walnut-100 dark:text-parchment-200/70">
              服务状态
            </p>
            <HealthStatus />
          </section>
        </div>

        {/* 角注 */}
        <footer className="mt-auto pt-16 font-display text-[11px] tracking-wider text-ink-400 dark:text-parchment-200/40">
          MVP · 后端 FastAPI · 前端 Next.js · 多 Agent 编排 by Claude
        </footer>
      </div>
    </main>
  );
}
