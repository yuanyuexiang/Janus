"use client";

import { useEffect, useRef, useState } from "react";

import {
  deleteConversation,
  exportConversationUrl,
  renameConversation,
  type ConversationSummary,
} from "@/lib/api";
import { getAdvisorMeta } from "@/lib/advisors";

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

// 把后端 mode tag 翻译成短中文徽章；solo:ming_ge → "单聊·明哥"
function formatMode(mode: string | null | undefined): string | null {
  if (!mode) return null;
  if (mode === "full") return "全员";
  if (mode === "mini") return "精简";
  if (mode.startsWith("solo:")) {
    const advisor = mode.slice(5);
    return `单聊·${getAdvisorMeta(advisor).display}`;
  }
  return mode;
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

  const modeLabel = formatMode(item.mode);

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
      className={`group relative block w-full cursor-pointer px-4 py-3 text-left text-sm transition-colors ${
        active
          ? "bg-parchment-200/60 dark:bg-walnut-300/20"
          : "hover:bg-parchment-100/60 dark:hover:bg-walnut-700/40"
      } ${busy ? "opacity-50" : ""}`}
    >
      {/* 选中：左侧金箔细条 */}
      {active && (
        <span className="absolute left-0 top-3 bottom-3 w-[2px] bg-gilt-500" />
      )}

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
          className="w-full rounded-sm border border-gilt-500/60 bg-parchment-50 px-1.5 py-0.5 font-display text-[14px] text-ink-900 focus:outline-none focus:border-gilt-500 dark:border-gilt-500/40 dark:bg-walnut-900/60 dark:text-parchment-100"
        />
      ) : (
        <div className="line-clamp-2 font-display text-[14px] leading-snug text-ink-900 dark:text-parchment-100">
          {item.title ?? "(无标题)"}
        </div>
      )}

      {/* 元数据行：日期左，右侧 mode 徽章 ↔ 操作按钮 hover 互换 */}
      <div className="relative mt-1.5 flex items-center justify-between gap-2">
        <span className="whitespace-nowrap font-mono text-[10px] text-ink-400 dark:text-parchment-200/50">
          {formatDate(item.updated_at)}
        </span>
        {modeLabel && (
          <span className="truncate font-display text-[10px] text-walnut-100 transition-opacity group-hover:opacity-0 dark:text-parchment-200/60">
            {modeLabel}
          </span>
        )}
        {/* 操作按钮：仅 hover 显示，覆盖在 mode 标签之上 */}
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center gap-3 font-display text-[10px] tracking-wider text-ink-400 opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:opacity-100 dark:text-parchment-200/70">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setEditing(true);
            }}
            className="hover:text-gilt-700 dark:hover:text-gilt-300"
            title="改名"
          >
            改名
          </button>
          <button
            type="button"
            onClick={handleExport}
            className="hover:text-gilt-700 dark:hover:text-gilt-300"
            title="导出 Markdown"
          >
            导出
          </button>
          <button
            type="button"
            onClick={handleDelete}
            className="hover:text-vermillion-500 dark:hover:text-vermillion-300"
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
    <aside className="flex h-full flex-col border-r border-parchment-300/60 bg-parchment-50/60 dark:border-walnut-300/20 dark:bg-walnut-900/40">
      <div className="border-b border-parchment-300/60 px-4 py-3 dark:border-walnut-300/20">
        <button
          onClick={onNew}
          className="group flex w-full items-center justify-center gap-2 rounded-sm border border-walnut-500/40 bg-transparent px-3 py-2 font-display text-[13px] tracking-wider text-walnut-500 transition-colors hover:border-gilt-500 hover:bg-gilt-500/[0.08] hover:text-walnut-700 dark:border-gilt-500/40 dark:text-gilt-100 dark:hover:border-gilt-300 dark:hover:bg-gilt-500/15"
        >
          <span className="text-base leading-none text-gilt-700 group-hover:text-walnut-700 dark:text-gilt-300 dark:group-hover:text-gilt-100">+</span>
          <span>新对话</span>
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto">
        {items.length === 0 ? (
          <p className="p-5 font-display italic text-xs text-ink-400 dark:text-parchment-200/50">
            还没有历史会话
          </p>
        ) : (
          <ul className="divide-y divide-parchment-300/40 dark:divide-walnut-300/15">
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
