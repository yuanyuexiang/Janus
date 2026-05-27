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
    <div className="my-3 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-xs dark:border-zinc-800 dark:bg-zinc-900/50">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between text-left text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200"
      >
        <span>
          🔧 工具调用 ({calls.length})
        </span>
        <span>{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <ul className="mt-2 space-y-2 font-mono">
          {calls.map((c) => (
            <li key={c.id} className="rounded bg-white p-2 dark:bg-zinc-950">
              <div className="text-zinc-800 dark:text-zinc-200">
                <span className="text-amber-700 dark:text-amber-400">{c.tool}</span>
                ({JSON.stringify(c.args)})
              </div>
              {c.result && (
                <div className="mt-1 text-zinc-500">
                  → {JSON.stringify(c.result)}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
