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
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 py-20 text-center">
      {/* 边角金箔细线 */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gilt-500/40 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-gilt-500/40 to-transparent" />

      <div className="flex w-full max-w-xl flex-col items-center">
        {/* 金印 */}
        <div className="relative mb-6 flex h-[68px] w-[68px] items-center justify-center">
          <div className="absolute inset-0 rounded-full border border-gilt-500/50" />
          <div className="absolute inset-[6px] rounded-full border border-gilt-500/25" />
          <span className="font-display text-[26px] text-gilt-700 dark:text-gilt-300">桌</span>
        </div>

        {/* 标题 */}
        <p className="mb-2 font-display text-[11px] uppercase tracking-[0.4em] text-gilt-700 dark:text-gilt-300">
          Atlas Council
        </p>
        <h1 className="font-display text-[38px] font-medium leading-none text-walnut-500 dark:text-parchment-100">
          圆桌投研
        </h1>

        {/* 引语 */}
        <p className="mt-5 font-display text-[16px] italic leading-relaxed text-ink-900 dark:text-parchment-100">
          一桌专家智囊团，陪你看清每一笔投资。
        </p>
        <p className="mt-1.5 max-w-md font-display text-[13px] italic leading-relaxed text-ink-600 dark:text-parchment-200/60">
          把「七位风格各异的专家围坐讨论」变成你随时可用的私人智库。
        </p>

        {/* 分隔 */}
        <div className="my-8 h-px w-14 bg-gilt-500/40" />

        {/* 七位顾问名牌 */}
        <div className="mb-9 flex flex-wrap justify-center gap-2">
          {ADVISORS.map((a) => (
            <span
              key={a.name}
              className="inline-flex items-baseline gap-1.5 rounded-lg border border-parchment-300/60 bg-parchment-100/40 px-2.5 py-1 font-display text-[12px] text-walnut-500 dark:border-walnut-300/25 dark:bg-walnut-700/30 dark:text-parchment-100"
            >
              {a.name}
              <span className="text-[10px] text-ink-400 dark:text-parchment-200/50">{a.role}</span>
            </span>
          ))}
          <span className="inline-flex items-center rounded-lg border border-gilt-500/40 bg-gilt-500/10 px-2.5 py-1 font-display text-[12px] text-gilt-700 dark:text-gilt-200">
            执棋 · 主持综合
          </span>
        </div>

        {/* 进入 / 解锁 */}
        <EntryGate />
      </div>

      {/* 角注 */}
      <footer className="absolute inset-x-0 bottom-6 text-center font-display text-[11px] tracking-wider text-ink-400 dark:text-parchment-200/40">
        MVP · 后端 FastAPI · 前端 Next.js · 多 Agent 编排 by Claude
      </footer>
    </main>
  );
}
