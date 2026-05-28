import { useState } from "react";

export type ToolCall = {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  result?: Record<string, unknown>;
};

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
        <ul className="mt-2 space-y-1.5 font-mono text-[11px]">
          {calls.map((c) => (
            <li
              key={c.id}
              className="rounded-sm bg-parchment-50/80 p-2 dark:bg-walnut-900/40"
            >
              <div className="text-walnut-500 dark:text-parchment-100">
                <span className="text-gilt-700 dark:text-gilt-300">{c.tool}</span>
                <span className="text-ink-400 dark:text-parchment-200/50">
                  ({JSON.stringify(c.args)})
                </span>
              </div>
              {c.result && (
                <div className="mt-0.5 truncate text-ink-400 dark:text-parchment-200/50">
                  → {JSON.stringify(c.result).slice(0, 240)}
                  {JSON.stringify(c.result).length > 240 ? "…" : ""}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
