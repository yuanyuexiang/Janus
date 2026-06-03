import { EntryGate } from "@/components/entry-gate";

const ADVISORS = [
  { name: "韬叔", role: "宏观" },
  { name: "岚姐", role: "行业" },
  { name: "明哥", role: "价值" },
  { name: "锐锋", role: "趋势" },
  { name: "冷川", role: "风险" },
  { name: "零度", role: "量化" },
];

export default function Home() {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-6 py-16">
      {/* 边角装饰：金箔细线 + 柔光 */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gilt-500/40 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-gilt-500/40 to-transparent" />

      <div className="w-full max-w-2xl">
        {/* 标识：双圈金印 + 主副标题 */}
        <div className="mb-10 flex items-center gap-4">
          <div className="relative flex h-14 w-14 shrink-0 items-center justify-center">
            <div className="absolute inset-0 rounded-full border border-gilt-500/50" />
            <div className="absolute inset-[6px] rounded-full border border-gilt-500/30" />
            <span className="font-display text-2xl text-gilt-700 dark:text-gilt-300">桌</span>
          </div>
          <div>
            <p className="font-display text-[11px] uppercase tracking-[0.35em] text-gilt-700 dark:text-gilt-300">
              Atlas Council
            </p>
            <h1 className="font-display text-[34px] font-medium leading-tight text-walnut-500 dark:text-parchment-100">
              圆桌投研
            </h1>
          </div>
        </div>

        {/* 引语 */}
        <blockquote className="mb-10 border-l-2 border-gilt-500/60 pl-5 font-display text-[19px] leading-relaxed not-italic text-ink-900 dark:text-parchment-100">
          一桌专家智囊团，陪你看清每一笔投资。
          <span className="mt-2.5 block font-display text-[13px] italic text-ink-600 dark:text-parchment-200/70">
            把「七位风格各异的专家围坐讨论」变成你随时可用的私人智库。
          </span>
        </blockquote>

        {/* 议事入口卡 */}
        <section className="relative overflow-hidden rounded-2xl border border-parchment-300/70 bg-parchment-100/40 p-7 shadow-paper-lg dark:border-walnut-300/30 dark:bg-walnut-700/40">
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
          <h2 className="mb-5 font-display text-2xl text-walnut-500 dark:text-parchment-100">
            进入圆桌
          </h2>

          {/* 顾问名牌 */}
          <div className="mb-6 flex flex-wrap gap-2">
            {ADVISORS.map((a) => (
              <span
                key={a.name}
                className="inline-flex items-baseline gap-1.5 rounded-lg border border-parchment-300/60 bg-parchment-50/60 px-2.5 py-1 font-display text-[12px] text-walnut-500 dark:border-walnut-300/25 dark:bg-walnut-900/30 dark:text-parchment-100"
              >
                {a.name}
                <span className="text-[10px] text-ink-400 dark:text-parchment-200/50">{a.role}</span>
              </span>
            ))}
            <span className="inline-flex items-center rounded-lg border border-gilt-500/40 bg-gilt-500/10 px-2.5 py-1 font-display text-[12px] text-gilt-700 dark:text-gilt-200">
              执棋 · 主持综合
            </span>
          </div>

          <EntryGate />
        </section>

        {/* 角注 */}
        <footer className="mt-12 font-display text-[11px] tracking-wider text-ink-400 dark:text-parchment-200/40">
          MVP · 后端 FastAPI · 前端 Next.js · 多 Agent 编排 by Claude
        </footer>
      </div>
    </main>
  );
}
