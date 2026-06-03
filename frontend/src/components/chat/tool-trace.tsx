import { useState } from "react";

export type ToolCall = {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  result?: Record<string, unknown>;
};

// 把 args 压成单行精简形式：{symbol: "600519.SH", days: 30}
// 单行可读时直接展示；过长则在 details 里 pretty-print
function formatArgsInline(args: Record<string, unknown>): string {
  const parts = Object.entries(args).map(([k, v]) => {
    const val = typeof v === "string" ? `"${v}"` : JSON.stringify(v);
    return `${k}: ${val}`;
  });
  return parts.join(", ");
}

export function ToolTrace({ calls }: { calls: ToolCall[] }) {
  const [open, setOpen] = useState(false);
  if (calls.length === 0) return null;
  return (
    <div className="mb-2 rounded-sm border border-parchment-300/60 bg-parchment-100/30 px-3 py-2 text-xs dark:border-walnut-300/20 dark:bg-walnut-700/30">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between font-display tracking-wide text-walnut-100 hover:text-gilt-700 dark:text-parchment-200/70 dark:hover:text-gilt-300"
      >
        <span className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.2em] text-gilt-700 dark:text-gilt-300">
            工具调用
          </span>
          <span className="font-mono text-[10px]">× {calls.length}</span>
        </span>
        <span className="text-[10px]">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <ul className="mt-2 space-y-2 text-[11px]">
          {calls.map((c) => (
            <li
              key={c.id}
              className="rounded-sm bg-parchment-50/80 p-2 dark:bg-walnut-900/40"
            >
              {/* 工具名 + 行内 args */}
              <div className="font-mono text-walnut-500 dark:text-parchment-100">
                <span className="text-gilt-700 dark:text-gilt-300">{c.tool}</span>
                <span className="text-ink-400 dark:text-parchment-200/50">
                  ({formatArgsInline(c.args)})
                </span>
              </div>
              {/* result：pretty-print 但限高，溢出可滚 */}
              {c.result && (
                <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-sm bg-parchment-100/60 p-1.5 font-mono text-[10.5px] leading-snug text-ink-600 dark:bg-walnut-700/40 dark:text-parchment-200/70">
                  {JSON.stringify(c.result, null, 2)}
                </pre>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
