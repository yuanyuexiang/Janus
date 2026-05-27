"use client";

import type { ConversationSummary } from "@/lib/api";

export type ConversationListProps = {
  items: ConversationSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function ConversationList({
  items,
  activeId,
  onSelect,
  onNew,
}: ConversationListProps) {
  return (
    <aside className="flex h-full flex-col border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="border-b border-zinc-200 p-3 dark:border-zinc-800">
        <button
          onClick={onNew}
          className="w-full rounded bg-amber-700 px-3 py-2 text-sm font-medium text-white hover:bg-amber-800"
        >
          + 新对话
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto">
        {items.length === 0 ? (
          <p className="p-4 text-xs text-zinc-500">还没有历史会话</p>
        ) : (
          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {items.map((c) => {
              const active = c.id === activeId;
              return (
                <li key={c.id}>
                  <button
                    onClick={() => onSelect(c.id)}
                    className={`block w-full px-3 py-2 text-left text-sm transition-colors ${
                      active
                        ? "bg-amber-50 text-amber-900 dark:bg-amber-950/30 dark:text-amber-200"
                        : "text-zinc-700 hover:bg-zinc-50 dark:text-zinc-300 dark:hover:bg-zinc-900"
                    }`}
                  >
                    <div className="line-clamp-2 font-medium leading-snug">
                      {c.title ?? "(无标题)"}
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-[10px] text-zinc-500">
                      <span>{formatDate(c.updated_at)}</span>
                      {c.mode && (
                        <span className="rounded bg-zinc-100 px-1 dark:bg-zinc-800">
                          {c.mode}
                        </span>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </nav>
    </aside>
  );
}
