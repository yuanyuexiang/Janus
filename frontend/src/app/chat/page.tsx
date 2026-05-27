"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { AdvisorBubble } from "@/components/chat/advisor-bubble";
import { ConversationList } from "@/components/chat/conversation-list";
import { ToolTrace, type ToolCall } from "@/components/chat/tool-trace";
import {
  getConversation,
  listConversations,
  type ConversationSummary,
} from "@/lib/api";
import { streamChat } from "@/lib/sse";
import type { AdvisorOpinion } from "@/lib/types";

type UserTurn = { kind: "user"; content: string };
type AdvisorTurn = {
  kind: "advisor";
  display: string;
  role: string;
  color: string;
  streamingText: string;
  opinion: AdvisorOpinion | null;
  toolCalls: ToolCall[];
};
type Turn = UserTurn | AdvisorTurn;

const EXAMPLES = [
  "贵州茅台 (600519.SH) 当前价位你怎么看？请用工具取价后给出判断。",
  "宁德时代 (300750.SZ) 在动力电池行业的护城河如何？",
  "如果只能拿一只 A 股 5 年，AAPL 和 600519.SH 你怎么选？",
];

const ADVISOR_META = {
  ming_ge: { display: "明哥", role: "价值", color: "#7B8B5C" },
} as const;

export default function ChatPage() {
  const [convList, setConvList] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const refreshList = useCallback(async () => {
    try {
      const data = await listConversations();
      setConvList(data);
    } catch (e) {
      console.warn("list conversations failed", e);
    }
  }, []);

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  async function loadConversation(id: string) {
    if (running) return;
    setError(null);
    setActiveId(id);
    try {
      const detail = await getConversation(id);
      const loaded: Turn[] = detail.messages.map((m) => {
        if (m.role === "user") {
          return { kind: "user", content: m.content ?? "" };
        }
        const advisorName = m.agent ?? "ming_ge";
        const meta = ADVISOR_META[advisorName as keyof typeof ADVISOR_META] ?? ADVISOR_META.ming_ge;
        return {
          kind: "advisor",
          display: meta.display,
          role: meta.role,
          color: meta.color,
          streamingText: m.content ?? "",
          opinion: m.structured,
          toolCalls: m.tool_calls.map((tc) => ({
            id: tc.id ?? "",
            tool: tc.tool,
            args: tc.args,
            result: tc.result,
          })),
        };
      });
      setTurns(loaded);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  function startNew() {
    if (running) return;
    setActiveId(null);
    setTurns([]);
    setError(null);
    setQuestion("");
  }

  async function submit() {
    const q = question.trim();
    if (!q || running) return;

    setRunning(true);
    setError(null);
    setStage("starting");

    // Optimistic: push user turn + empty advisor turn
    setTurns((prev) => [
      ...prev,
      { kind: "user", content: q },
      {
        kind: "advisor",
        display: ADVISOR_META.ming_ge.display,
        role: ADVISOR_META.ming_ge.role,
        color: ADVISOR_META.ming_ge.color,
        streamingText: "",
        opinion: null,
        toolCalls: [],
      },
    ]);
    setQuestion("");

    const updateLastAdvisor = (mut: (t: AdvisorTurn) => AdvisorTurn) =>
      setTurns((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].kind === "advisor") {
            next[i] = mut(next[i] as AdvisorTurn);
            break;
          }
        }
        return next;
      });

    try {
      for await (const ev of streamChat(q, activeId)) {
        switch (ev.type) {
          case "session":
            if (!activeId) setActiveId(ev.conversation_id);
            break;
          case "advisor_start":
            updateLastAdvisor((t) => ({
              ...t,
              display: ev.display,
              role: ev.role,
              color: ev.color,
            }));
            break;
          case "stage":
            setStage(ev.stage);
            break;
          case "text":
            updateLastAdvisor((t) => ({ ...t, streamingText: t.streamingText + ev.chunk }));
            break;
          case "tool_call":
            updateLastAdvisor((t) => ({
              ...t,
              toolCalls: [...t.toolCalls, { id: ev.id, tool: ev.tool, args: ev.args }],
            }));
            break;
          case "tool_result":
            updateLastAdvisor((t) => {
              const tc = [...t.toolCalls];
              for (let i = tc.length - 1; i >= 0; i--) {
                if (tc[i].tool === ev.tool && !tc[i].result) {
                  tc[i] = { ...tc[i], result: ev.result };
                  break;
                }
              }
              return { ...t, toolCalls: tc };
            });
            break;
          case "opinion":
            updateLastAdvisor((t) => ({ ...t, opinion: ev.full }));
            break;
          case "error":
            setError(`${ev.code}: ${ev.message}`);
            break;
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
      setStage(null);
      refreshList();
    }
  }

  return (
    <main className="flex h-screen flex-col bg-zinc-50 dark:bg-zinc-950">
      <header className="flex items-center justify-between border-b border-zinc-200 bg-white px-6 py-3 dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex items-baseline gap-3">
          <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100">
            ← 返回
          </Link>
          <span className="text-xs uppercase tracking-widest text-amber-700 dark:text-amber-400">
            Atlas Council · M1
          </span>
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">圆桌投研</h1>
        </div>
        {stage && (
          <span className="text-xs text-zinc-500">
            stage: <code>{stage}</code>
          </span>
        )}
      </header>

      <div className="grid flex-1 grid-cols-[260px_1fr] overflow-hidden">
        <ConversationList
          items={convList}
          activeId={activeId}
          onSelect={loadConversation}
          onNew={startNew}
        />

        <section className="flex flex-col overflow-hidden">
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6">
            {turns.length === 0 ? (
              <div className="mx-auto max-w-2xl text-center text-sm text-zinc-500">
                <p className="mb-4">向明哥（价值派）提个问题。</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {EXAMPLES.map((ex, i) => (
                    <button
                      key={i}
                      onClick={() => setQuestion(ex)}
                      className="rounded border border-zinc-200 px-3 py-1.5 text-xs text-zinc-600 hover:border-amber-600 hover:text-amber-700 dark:border-zinc-700 dark:text-zinc-400"
                    >
                      示例 {i + 1}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mx-auto max-w-2xl space-y-4">
                {turns.map((t, i) =>
                  t.kind === "user" ? (
                    <div key={i} className="flex justify-end">
                      <div className="max-w-[85%] rounded-lg bg-amber-700 px-4 py-2 text-sm text-white">
                        {t.content}
                      </div>
                    </div>
                  ) : (
                    <div key={i}>
                      <ToolTrace calls={t.toolCalls} />
                      <AdvisorBubble
                        display={t.display}
                        role={t.role}
                        color={t.color}
                        streamingText={t.streamingText}
                        opinion={t.opinion}
                      />
                    </div>
                  ),
                )}
              </div>
            )}
          </div>

          {error && (
            <p className="mx-6 mb-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/50 dark:text-red-300">
              {error}
            </p>
          )}

          <div className="border-t border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
            <div className="mx-auto flex max-w-2xl gap-2">
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    submit();
                  }
                }}
                rows={2}
                disabled={running}
                className="flex-1 resize-none rounded border border-zinc-200 bg-white px-3 py-2 text-sm focus:border-amber-600 focus:outline-none disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-50"
                placeholder={activeId ? "继续追问…  ⌘+↵ 发送" : "问明哥点什么…  ⌘+↵ 发送"}
              />
              <button
                onClick={submit}
                disabled={running || !question.trim()}
                className="self-end rounded bg-amber-700 px-5 py-2 text-sm font-medium text-white hover:bg-amber-800 disabled:opacity-50"
              >
                {running ? "讨论中…" : "发送"}
              </button>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
