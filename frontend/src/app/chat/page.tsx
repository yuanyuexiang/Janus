"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { AdvisorBubble } from "@/components/chat/advisor-bubble";
import { ConductorSummary } from "@/components/chat/conductor-summary";
import { ConversationList } from "@/components/chat/conversation-list";
import {
  GlassBoxDrawer,
  type GlassBoxData,
} from "@/components/chat/glass-box-drawer";
import { ToolTrace, type ToolCall } from "@/components/chat/tool-trace";
import {
  formatStage,
  FULL_COUNCIL,
  getAdvisorMeta,
  MINI_COUNCIL,
} from "@/lib/advisors";
import {
  getConversation,
  listConversations,
  type ConversationSummary,
  type StoredMessage,
} from "@/lib/api";
import { streamChat } from "@/lib/sse";
import type { AdvisorOpinion, CouncilSummary } from "@/lib/types";

type Mode = "mini" | "full" | "solo";

const MODE_OPTIONS: { value: Mode; label: string; hint: string }[] = [
  { value: "mini", label: "圆桌 · 3 顾问", hint: "韬叔 / 岚姐 / 明哥" },
  { value: "full", label: "全员 · 6 顾问", hint: "+ 锐锋 / 冷川 / 零度" },
  { value: "solo", label: "单聊 · 明哥", hint: "只问价值派" },
];

type AdvisorState = {
  display: string;
  role: string;
  color: string;
  streamingText: string;
  toolCalls: ToolCall[];
  opinion: AdvisorOpinion | null;
  activeSkills: string[];
  model?: string | null;
};

type ConductorState = {
  streamingText: string;
  summary: CouncilSummary | null;
  model?: string | null;
};

type CouncilTurn = {
  kind: "council";
  mode: Mode;
  advisorOrder: string[];
  advisors: Record<string, AdvisorState>;
  conductor: ConductorState | null;
};

type Turn = { kind: "user"; content: string } | CouncilTurn;

const EXAMPLES = [
  "贵州茅台 (600519.SH) 当前价位还能拿吗？请用工具取价。",
  "宁德时代 (300750.SZ) 的行业护城河与下行风险？",
  "如果在 AAPL 和 600519.SH 二选一持有 5 年，怎么选？",
];

function makeAdvisorState(name: string): AdvisorState {
  const meta = getAdvisorMeta(name);
  return {
    display: meta.display,
    role: meta.role,
    color: meta.color,
    streamingText: "",
    toolCalls: [],
    opinion: null,
    activeSkills: [],
  };
}

function initialAdvisors(mode: Mode): {
  order: string[];
  advisors: Record<string, AdvisorState>;
} {
  if (mode === "mini") {
    return {
      order: [...MINI_COUNCIL],
      advisors: Object.fromEntries(MINI_COUNCIL.map((n) => [n, makeAdvisorState(n)])),
    };
  }
  if (mode === "full") {
    return {
      order: [...FULL_COUNCIL],
      advisors: Object.fromEntries(FULL_COUNCIL.map((n) => [n, makeAdvisorState(n)])),
    };
  }
  return {
    order: ["ming_ge"],
    advisors: { ming_ge: makeAdvisorState("ming_ge") },
  };
}

function modeFromTag(tag: string | null | undefined): Mode {
  if (!tag) return "mini";
  if (tag === "full") return "full";
  if (tag === "mini") return "mini";
  if (tag.startsWith("solo:")) return "solo";
  return "mini";
}

function reconstructTurns(messages: StoredMessage[]): Turn[] {
  const turns: Turn[] = [];
  let current: CouncilTurn | null = null;

  for (const m of messages) {
    if (m.role === "user") {
      current = null;
      turns.push({ kind: "user", content: m.content ?? "" });
    } else if (m.role.startsWith("advisor:")) {
      const name = m.agent ?? m.role.slice("advisor:".length);
      if (!current) {
        current = {
          kind: "council",
          mode: "mini",
          advisorOrder: [],
          advisors: {},
          conductor: null,
        };
        turns.push(current);
      }
      if (!current.advisorOrder.includes(name)) current.advisorOrder.push(name);
      const meta = getAdvisorMeta(name);
      current.advisors[name] = {
        display: meta.display,
        role: meta.role,
        color: meta.color,
        streamingText: m.content ?? "",
        toolCalls: (m.tool_calls ?? []).map((tc) => ({
          id: tc.id ?? "",
          tool: tc.tool,
          args: tc.args,
          result: tc.result,
        })),
        opinion: m.structured as AdvisorOpinion | null,
        activeSkills: m.active_skills ?? [],
        model: m.model,
      };
    } else if (m.role === "conductor") {
      if (!current) {
        current = {
          kind: "council",
          mode: "mini",
          advisorOrder: [],
          advisors: {},
          conductor: null,
        };
        turns.push(current);
      }
      current.conductor = {
        streamingText: m.content ?? "",
        summary: (m.structured as CouncilSummary | null) ?? null,
        model: m.model,
      };
    }
  }
  for (const t of turns) {
    if (t.kind === "council") {
      if (t.advisorOrder.length >= 6) t.mode = "full";
      else if (t.advisorOrder.length > 1) t.mode = "mini";
      else t.mode = "solo";
    }
  }
  return turns;
}

export default function ChatPage() {
  const [convList, setConvList] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<Mode>("mini");
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState<string | null>(null);
  const [stageAdvisor, setStageAdvisor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [glassBox, setGlassBox] = useState<GlassBoxData | null>(null);
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
      setTurns(reconstructTurns(detail.messages));
      setMode(modeFromTag(detail.mode));
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

  function patchCouncil(mut: (c: CouncilTurn) => void) {
    setTurns((prev) => {
      const next = [...prev];
      for (let i = next.length - 1; i >= 0; i--) {
        if (next[i].kind === "council") {
          const c = { ...(next[i] as CouncilTurn) };
          mut(c);
          next[i] = c;
          return next;
        }
      }
      return next;
    });
  }

  async function submit() {
    const q = question.trim();
    if (!q || running) return;
    setRunning(true);
    setError(null);
    setStage("starting");
    setStageAdvisor(null);

    const { order, advisors } = initialAdvisors(mode);
    const initialCouncil: CouncilTurn = {
      kind: "council",
      mode,
      advisorOrder: order,
      advisors,
      conductor: mode === "solo" ? null : { streamingText: "", summary: null },
    };

    setTurns((prev) => [...prev, { kind: "user", content: q }, initialCouncil]);
    setQuestion("");

    try {
      for await (const ev of streamChat(q, { conversationId: activeId, mode })) {
        switch (ev.type) {
          case "session":
            if (!activeId) setActiveId(ev.conversation_id);
            break;
          case "council_start":
            patchCouncil((c) => {
              c.advisorOrder = ev.advisors;
              for (const n of ev.advisors) {
                if (!c.advisors[n]) c.advisors[n] = makeAdvisorState(n);
              }
            });
            break;
          case "advisor_start":
            patchCouncil((c) => {
              const a = c.advisors[ev.advisor] ?? makeAdvisorState(ev.advisor);
              a.display = ev.display;
              a.role = ev.role;
              a.color = ev.color;
              a.activeSkills = ev.active_skills ?? [];
              c.advisors[ev.advisor] = { ...a };
            });
            break;
          case "stage":
            setStage(ev.stage);
            setStageAdvisor(ev.advisor ?? null);
            break;
          case "text": {
            const name = ev.advisor ?? "ming_ge";
            patchCouncil((c) => {
              const a = c.advisors[name];
              if (a) c.advisors[name] = { ...a, streamingText: a.streamingText + ev.chunk };
            });
            break;
          }
          case "tool_call": {
            const name = ev.advisor ?? "ming_ge";
            patchCouncil((c) => {
              const a = c.advisors[name];
              if (a) {
                c.advisors[name] = {
                  ...a,
                  toolCalls: [...a.toolCalls, { id: ev.id, tool: ev.tool, args: ev.args }],
                };
              }
            });
            break;
          }
          case "tool_result": {
            const name = ev.advisor ?? "ming_ge";
            patchCouncil((c) => {
              const a = c.advisors[name];
              if (!a) return;
              const tc = [...a.toolCalls];
              for (let i = tc.length - 1; i >= 0; i--) {
                if (tc[i].tool === ev.tool && !tc[i].result) {
                  tc[i] = { ...tc[i], result: ev.result };
                  break;
                }
              }
              c.advisors[name] = { ...a, toolCalls: tc };
            });
            break;
          }
          case "opinion": {
            const name = ev.advisor ?? "ming_ge";
            patchCouncil((c) => {
              const a = c.advisors[name];
              if (a) c.advisors[name] = { ...a, opinion: ev.full };
            });
            break;
          }
          case "synthesis_start":
            setStage("synthesis");
            setStageAdvisor(null);
            patchCouncil((c) => {
              c.conductor = { streamingText: "", summary: null };
            });
            break;
          case "synthesis_text":
            patchCouncil((c) => {
              const cur = c.conductor ?? { streamingText: "", summary: null };
              c.conductor = { ...cur, streamingText: cur.streamingText + ev.chunk };
            });
            break;
          case "synthesis":
            patchCouncil((c) => {
              const cur = c.conductor ?? { streamingText: "", summary: null };
              c.conductor = { ...cur, summary: ev.full };
            });
            break;
          case "error":
            setError(`${ev.code}: ${ev.message}${ev.advisor ? ` (${ev.advisor})` : ""}`);
            break;
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
      setStage(null);
      setStageAdvisor(null);
      refreshList();
    }
  }

  const stageLabel = formatStage(stage, stageAdvisor);
  const placeholder = activeId ? "继续追问…  ⌘+↵ 发送" : "向圆桌提个问题…  ⌘+↵ 发送";

  return (
    <main className="flex h-screen flex-col bg-zinc-50 dark:bg-zinc-950">
      <header className="flex items-center justify-between border-b border-zinc-200 bg-white px-6 py-3 dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex items-baseline gap-3">
          <Link
            href="/"
            className="text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
          >
            ← 返回
          </Link>
          <span className="text-xs uppercase tracking-widest text-amber-700 dark:text-amber-400">
            Atlas Council · M2.5
          </span>
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">圆桌投研</h1>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 rounded border border-zinc-200 p-0.5 text-xs dark:border-zinc-700">
            {MODE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => !running && setMode(opt.value)}
                disabled={running}
                title={opt.hint}
                className={`rounded px-2 py-1 transition-colors ${
                  mode === opt.value
                    ? "bg-amber-700 text-white"
                    : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400"
                } disabled:opacity-50`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {stageLabel && (
            <span className="flex items-center gap-1.5 text-xs text-zinc-600 dark:text-zinc-400">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-600" />
              {stageLabel}
            </span>
          )}
        </div>
      </header>

      <div className="grid flex-1 grid-cols-[260px_1fr] overflow-hidden">
        <ConversationList
          items={convList}
          activeId={activeId}
          onSelect={loadConversation}
          onNew={startNew}
          onMutated={({ deletedId }) => {
            if (deletedId && deletedId === activeId) {
              setActiveId(null);
              setTurns([]);
            }
            refreshList();
          }}
        />

        <section className="flex flex-col overflow-hidden">
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6">
            {turns.length === 0 ? (
              <div className="mx-auto max-w-3xl text-center text-sm text-zinc-500">
                <p className="mb-4">
                  {mode === "full"
                    ? "向全员圆桌（6 位顾问）提个问题。6 路并行 + 主持人综合。"
                    : mode === "mini"
                      ? "向圆桌（韬叔/岚姐/明哥）提个问题，3 位顾问并行，主持人最后综合。"
                      : "向明哥（价值派）单独提个问题。"}
                </p>
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
              <div className="mx-auto max-w-3xl space-y-4">
                {turns.map((t, i) => {
                  if (t.kind === "user") {
                    return (
                      <div key={i} className="flex justify-end">
                        <div className="max-w-[85%] rounded-lg bg-amber-700 px-4 py-2 text-sm text-white">
                          {t.content}
                        </div>
                      </div>
                    );
                  }
                  const contributedAdvisors = t.advisorOrder.filter(
                    (n) => t.advisors[n]?.opinion,
                  );
                  return (
                    <div key={i} className="space-y-3">
                      <div className="grid gap-3">
                        {t.advisorOrder.map((name) => {
                          const a = t.advisors[name];
                          if (!a) return null;
                          return (
                            <div key={name}>
                              <ToolTrace calls={a.toolCalls} />
                              <AdvisorBubble
                                display={a.display}
                                role={a.role}
                                color={a.color}
                                streamingText={a.streamingText}
                                opinion={a.opinion}
                                activeSkills={a.activeSkills}
                                onOpenDetails={() =>
                                  setGlassBox({
                                    kind: "advisor",
                                    name,
                                    display: a.display,
                                    role: a.role,
                                    color: a.color,
                                    activeSkills: a.activeSkills,
                                    toolCalls: a.toolCalls,
                                    opinion: a.opinion,
                                    model: a.model,
                                  })
                                }
                              />
                            </div>
                          );
                        })}
                      </div>
                      {t.conductor && (
                        <ConductorSummary
                          streamingText={t.conductor.streamingText}
                          summary={t.conductor.summary}
                          onOpenDetails={() => {
                            const cond = t.conductor;
                            if (!cond) return;
                            setGlassBox({
                              kind: "conductor",
                              advisorsContributed: contributedAdvisors,
                              streamingText: cond.streamingText,
                              summary: cond.summary,
                              model: cond.model,
                            });
                          }}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {error && (
            <p className="mx-6 mb-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/50 dark:text-red-300">
              {error}
            </p>
          )}

          <div className="border-t border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
            <div className="mx-auto flex max-w-3xl gap-2">
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
                placeholder={placeholder}
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

      <GlassBoxDrawer data={glassBox} onClose={() => setGlassBox(null)} />
    </main>
  );
}
