"use client";

import { useEffect, useRef, useState } from "react";

import {
  deleteConversation,
  exportConversationUrl,
  renameConversation,
  type ConversationSummary,
} from "@/lib/api";

export type ConversationListProps = {
  items: ConversationSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onMutated: (info: { renamedId?: string; deletedId?: string }) => void;
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function downloadUrl(url: string, filename: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

type RowProps = {
  item: ConversationSummary;
  active: boolean;
  onSelect: () => void;
  onAfterMutate: (info: { renamedId?: string; deletedId?: string }) => void;
};

function ConversationRow({ item, active, onSelect, onAfterMutate }: RowProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(item.title ?? "");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  useEffect(() => {
    setDraft(item.title ?? "");
  }, [item.title]);

  async function commitRename() {
    const trimmed = draft.trim();
    if (!trimmed || trimmed === (item.title ?? "")) {
      setEditing(false);
      setDraft(item.title ?? "");
      return;
    }
    setBusy(true);
    try {
      await renameConversation(item.id, trimmed);
      onAfterMutate({ renamedId: item.id });
    } catch (e) {
      console.error("rename failed", e);
      setDraft(item.title ?? "");
    } finally {
      setBusy(false);
      setEditing(false);
    }
  }

  async function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    const ok = window.confirm(`删除会话「${item.title ?? "(无标题)"}」？此操作不可恢复。`);
    if (!ok) return;
    setBusy(true);
    try {
      await deleteConversation(item.id);
      onAfterMutate({ deletedId: item.id });
    } catch (err) {
      console.error("delete failed", err);
      alert("删除失败");
    } finally {
      setBusy(false);
    }
  }

  function handleExport(e: React.MouseEvent) {
    e.stopPropagation();
    const safeTitle = (item.title ?? "conversation").replace(/[/\\?%*:|"<>]/g, "-").slice(0, 60);
    downloadUrl(exportConversationUrl(item.id, "md"), `${safeTitle}.md`);
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => !editing && !busy && onSelect()}
      onKeyDown={(e) => {
        if (!editing && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onSelect();
        }
      }}
      className={`group block w-full cursor-pointer px-3 py-2 text-left text-sm transition-colors ${
        active
          ? "bg-amber-50 text-amber-900 dark:bg-amber-950/30 dark:text-amber-200"
          : "text-zinc-700 hover:bg-zinc-50 dark:text-zinc-300 dark:hover:bg-zinc-900"
      } ${busy ? "opacity-50" : ""}`}
    >
      {editing ? (
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onClick={(e) => e.stopPropagation()}
          onBlur={commitRename}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              commitRename();
            } else if (e.key === "Escape") {
              setEditing(false);
              setDraft(item.title ?? "");
            }
          }}
          maxLength={128}
          className="w-full rounded border border-amber-600 bg-white px-1 py-0.5 text-sm text-zinc-900 focus:outline-none dark:bg-zinc-950 dark:text-zinc-100"
        />
      ) : (
        <div className="line-clamp-2 font-medium leading-snug">
          {item.title ?? "(无标题)"}
        </div>
      )}

      <div className="mt-1 flex items-center justify-between">
        <div className="flex items-center gap-2 text-[10px] text-zinc-500">
          <span>{formatDate(item.updated_at)}</span>
          {item.mode && (
            <span className="rounded bg-zinc-100 px-1 dark:bg-zinc-800">{item.mode}</span>
          )}
        </div>
        <div className="flex items-center gap-2 text-[10px] text-zinc-400 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setEditing(true);
            }}
            className="hover:text-amber-700 dark:hover:text-amber-400"
            title="改名"
          >
            改名
          </button>
          <button
            type="button"
            onClick={handleExport}
            className="hover:text-amber-700 dark:hover:text-amber-400"
            title="导出 Markdown"
          >
            导出
          </button>
          <button
            type="button"
            onClick={handleDelete}
            className="hover:text-red-600 dark:hover:text-red-400"
            title="删除"
          >
            删除
          </button>
        </div>
      </div>
    </div>
  );
}

export function ConversationList({
  items,
  activeId,
  onSelect,
  onNew,
  onMutated,
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
            {items.map((c) => (
              <li key={c.id}>
                <ConversationRow
                  item={c}
                  active={c.id === activeId}
                  onSelect={() => onSelect(c.id)}
                  onAfterMutate={onMutated}
                />
              </li>
            ))}
          </ul>
        )}
      </nav>
    </aside>
  );
}
