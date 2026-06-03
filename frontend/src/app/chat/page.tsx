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
  tokensIn?: number | null;
  tokensOut?: number | null;
};

type ConductorState = {
  streamingText: string;
  summary: CouncilSummary | null;
  model?: string | null;
  tokensIn?: number | null;
  tokensOut?: number | null;
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
        tokensIn: m.tokens_in,
        tokensOut: m.tokens_out,
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
        tokensIn: m.tokens_in,
        tokensOut: m.tokens_out,
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
  // 窄屏侧栏开关；md 以上侧栏常驻
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // 用户离底超过阈值时显示"↓ 新消息"浮按钮
  const [showJumpToBottom, setShowJumpToBottom] = useState(false);
  // 用于失败重试 / 回填输入；与 question 解耦（question 在 submit 时已清空）
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  // 用 ref 避免 onScroll 每次都触发 React 重渲（仅 showJumpToBottom 翻转时才 set）
  const isAtBottomRef = useRef(true);

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

  // ESC 关闭移动端 Drawer（仅在打开时绑定监听）
  useEffect(() => {
    if (!sidebarOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setSidebarOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sidebarOpen]);

  // 流式期间用户可能往上滚看历史 —— 仅当贴底时才自动跟随，否则不打扰
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (!isAtBottomRef.current) return;
    // 用 auto 而非 smooth：流式增量每个 token 都触发，smooth 会持续卡顿
    el.scrollTo({ top: el.scrollHeight });
  }, [turns]);

  function handleScroll() {
    const el = scrollRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    const atBottom = distance < 80;
    const wasAtBottom = isAtBottomRef.current;
    isAtBottomRef.current = atBottom;
    if (wasAtBottom !== atBottom) setShowJumpToBottom(!atBottom);
  }

  function jumpToBottom() {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    isAtBottomRef.current = true;
    setShowJumpToBottom(false);
  }

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
    setQuestion("");
    await runChat(q);
  }

  function retry() {
    if (!lastQuestion || running) return;
    runChat(lastQuestion);
  }

  function dismissError() {
    setError(null);
  }

  function refillError() {
    if (lastQuestion) setQuestion(lastQuestion);
    setError(null);
  }

  async function runChat(q: string) {
    if (running) return;
    setRunning(true);
    setError(null);
    setLastQuestion(q);
    setStage("starting");
    setStageAdvisor(null);
    // 新一轮发起 —— 用户语义上"想看新内容"，强制贴底
    isAtBottomRef.current = true;
    setShowJumpToBottom(false);

    const { order, advisors } = initialAdvisors(mode);
    const initialCouncil: CouncilTurn = {
      kind: "council",
      mode,
      advisorOrder: order,
      advisors,
      conductor: mode === "solo" ? null : { streamingText: "", summary: null },
    };

    setTurns((prev) => [...prev, { kind: "user", content: q }, initialCouncil]);

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
          case "usage": {
            const name = ev.advisor ?? "ming_ge";
            patchCouncil((c) => {
              const a = c.advisors[name];
              if (a) {
                c.advisors[name] = {
                  ...a,
                  tokensIn: ev.tokens_in,
                  tokensOut: ev.tokens_out,
                };
              }
            });
            break;
          }
          case "synthesis_usage":
            patchCouncil((c) => {
              const cur = c.conductor ?? { streamingText: "", summary: null };
              c.conductor = {
                ...cur,
                tokensIn: ev.tokens_in,
                tokensOut: ev.tokens_out,
              };
            });
            break;
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

  function ModeToggle({
    mode,
    setMode,
    running,
  }: {
    mode: Mode;
    setMode: (m: Mode) => void;
    running: boolean;
  }) {
    return (
      <div className="inline-flex items-center divide-x divide-parchment-300/70 rounded-sm border border-parchment-300/70 bg-parchment-50/60 font-display text-[11px] tracking-wider dark:divide-walnut-300/30 dark:border-walnut-300/30 dark:bg-walnut-700/40">
        {MODE_OPTIONS.map((opt) => {
          const on = mode === opt.value;
          return (
            <button
              key={opt.value}
              onClick={() => !running && setMode(opt.value)}
              disabled={running}
              title={opt.hint}
              className={`px-3 py-1.5 transition-colors disabled:opacity-50 ${
                on
                  ? "bg-walnut-500 text-parchment-100 dark:bg-gilt-500 dark:text-walnut-900"
                  : "text-walnut-100 hover:text-walnut-500 dark:text-parchment-200/70 dark:hover:text-gilt-300"
              }`}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <main className="flex h-screen flex-col">
      {/* 顶栏：羊皮纸底 + 金箔分隔线 */}
      <header className="relative border-b border-parchment-300/60 bg-parchment-50/80 px-4 py-4 backdrop-blur md:px-8 dark:border-walnut-300/20 dark:bg-walnut-900/60">
        <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-gilt-500/60 to-transparent" />
        <div className="flex items-center justify-between gap-4 md:gap-6">
          <div className="flex items-center gap-3 md:items-baseline md:gap-4">
            {/* 汉堡按钮：仅窄屏显示，唤出会话列表 Drawer */}
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              aria-label="打开会话列表"
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-sm border border-parchment-300/70 text-walnut-100 transition-colors hover:border-gilt-500 hover:text-walnut-500 md:hidden dark:border-walnut-300/30 dark:text-parchment-200/70 dark:hover:border-gilt-300 dark:hover:text-gilt-300"
            >
              <span className="text-base leading-none">≡</span>
            </button>
            <Link
              href="/"
              className="hidden font-display text-[12px] tracking-[0.2em] text-walnut-100 no-underline hover:text-gilt-700 md:inline dark:text-parchment-200/70 dark:hover:text-gilt-300"
            >
              ← 返回
            </Link>
            <div className="flex items-baseline gap-3">
              <h1 className="font-display text-xl font-medium text-walnut-500 dark:text-parchment-100">
                圆桌投研
              </h1>
              <span className="font-display text-[10px] uppercase tracking-[0.3em] text-gilt-700 dark:text-gilt-300">
                Atlas Council
              </span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <ModeToggle mode={mode} setMode={setMode} running={running} />
            {stageLabel && (
              <span className="flex items-center gap-2 font-display text-[11px] tracking-wider text-walnut-100 dark:text-parchment-200/70">
                <span className="relative inline-flex h-1.5 w-1.5">
                  <span className="absolute inset-0 rounded-full bg-gilt-500/60 motion-safe:animate-ping" />
                  <span className="absolute inset-0 rounded-full bg-gilt-500" />
                </span>
                {stageLabel}
              </span>
            )}
          </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* 桌面侧栏：md 以上常驻 */}
        <div className="hidden w-[260px] shrink-0 md:block">
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
        </div>

        {/* 移动端 Drawer：sidebarOpen 时遮罩 + 抽屉浮起 */}
        {sidebarOpen && (
          <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true">
            <div
              className="absolute inset-0 bg-walnut-900/40 backdrop-blur-sm"
              onClick={() => setSidebarOpen(false)}
              aria-hidden="true"
            />
            <div className="absolute inset-y-0 left-0 w-[280px] max-w-[85vw] bg-parchment-50 shadow-paper-lg dark:bg-walnut-900">
              <ConversationList
                items={convList}
                activeId={activeId}
                onSelect={(id) => {
                  loadConversation(id);
                  setSidebarOpen(false);
                }}
                onNew={() => {
                  startNew();
                  setSidebarOpen(false);
                }}
                onMutated={({ deletedId }) => {
                  if (deletedId && deletedId === activeId) {
                    setActiveId(null);
                    setTurns([]);
                  }
                  refreshList();
                }}
              />
            </div>
          </div>
        )}

        <section className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-10"
          >
            {turns.length === 0 ? (
              <div className="mx-auto flex max-w-2xl flex-col items-center text-center">
                {/* 印章 / 引文徽标 */}
                <div className="relative mb-8 flex h-20 w-20 items-center justify-center">
                  <div className="absolute inset-0 rounded-full border border-gilt-500/40" />
                  <div className="absolute inset-2 rounded-full border border-gilt-500/30" />
                  <span className="font-display text-3xl text-gilt-700 dark:text-gilt-300">桌</span>
                </div>
                <p className="mb-3 font-display text-xl text-walnut-500 dark:text-parchment-100">
                  {mode === "full"
                    ? "全员议事 · 六位顾问"
                    : mode === "mini"
                      ? "圆桌精简 · 三位顾问"
                      : "单聊 · 明哥（价值派）"}
                </p>
                <p className="mb-10 max-w-md font-display text-[13px] italic leading-relaxed text-ink-600 dark:text-parchment-200/70">
                  {mode === "full"
                    ? "六位顾问并行思考，主持人执棋综合共识、分歧与风险。"
                    : mode === "mini"
                      ? "韬叔看宏观、岚姐看行业、明哥看价值；执棋最后综合。"
                      : "向明哥提一个估值或基本面问题。"}
                </p>
                <div className="flex w-full max-w-xl flex-col gap-2">
                  {EXAMPLES.map((ex, i) => (
                    <button
                      key={i}
                      onClick={() => setQuestion(ex)}
                      className="group flex w-full items-start gap-3 rounded-sm border border-parchment-300/70 bg-parchment-100/40 px-4 py-3 text-left font-display text-[13px] leading-relaxed text-ink-600 transition-colors hover:border-gilt-500 hover:bg-gilt-500/[0.08] hover:text-walnut-500 dark:border-walnut-300/30 dark:bg-walnut-700/30 dark:text-parchment-200/80 dark:hover:border-gilt-300 dark:hover:text-gilt-100"
                    >
                      <span className="mt-0.5 shrink-0 font-display text-[10px] uppercase tracking-[0.2em] text-gilt-700 dark:text-gilt-300">
                        示例
                      </span>
                      <span className="flex-1">{ex}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mx-auto max-w-3xl space-y-5">
                {turns.map((t, i) => {
                  if (t.kind === "user") {
                    return (
                      <div key={i} className="flex justify-end">
                        <div
                          className="max-w-[85%] rounded-sm border border-walnut-500/30 bg-walnut-500/[0.06] px-5 py-3 font-display text-[14px] leading-relaxed text-walnut-500 dark:border-gilt-500/30 dark:bg-gilt-500/[0.08] dark:text-parchment-100"
                        >
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
                                    tokensIn: a.tokensIn,
                                    tokensOut: a.tokensOut,
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
                              tokensIn: cond.tokensIn,
                              tokensOut: cond.tokensOut,
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

          {/* "↓ 新消息"浮按钮：用户向上脱离底部时显示 */}
          {showJumpToBottom && (
            <button
              type="button"
              onClick={jumpToBottom}
              aria-label="跳转到最新消息"
              className="absolute bottom-24 right-4 z-10 inline-flex items-center gap-1.5 rounded-full border border-walnut-500/30 bg-parchment-50 px-3 py-1.5 font-display text-[12px] text-walnut-500 shadow-paper-lg transition-colors hover:border-gilt-500 hover:bg-gilt-500/10 md:right-8 dark:border-gilt-500/40 dark:bg-walnut-700 dark:text-gilt-100 dark:hover:bg-gilt-500/20"
            >
              <span className="text-base leading-none">↓</span>
              新消息
            </button>
          )}

          {error && (
            <div
              role="alert"
              className="mx-4 mb-3 flex shrink-0 items-start gap-3 rounded-sm border border-vermillion-500/30 bg-vermillion-500/[0.08] p-3 text-[13px] text-vermillion-700 md:mx-8 dark:border-vermillion-300/30 dark:bg-vermillion-500/[0.15] dark:text-vermillion-300"
            >
              <span className="flex-1 leading-relaxed">{error}</span>
              {lastQuestion && (
                <>
                  <button
                    type="button"
                    onClick={retry}
                    disabled={running}
                    className="shrink-0 rounded-sm border border-vermillion-500/40 px-2 py-1 font-display text-[11px] tracking-wider transition-colors hover:bg-vermillion-500/10 disabled:cursor-not-allowed disabled:opacity-40 dark:border-vermillion-300/40 dark:hover:bg-vermillion-300/10"
                  >
                    重试
                  </button>
                  <button
                    type="button"
                    onClick={refillError}
                    className="shrink-0 rounded-sm border border-vermillion-500/40 px-2 py-1 font-display text-[11px] tracking-wider transition-colors hover:bg-vermillion-500/10 dark:border-vermillion-300/40 dark:hover:bg-vermillion-300/10"
                  >
                    回填
                  </button>
                </>
              )}
              <button
                type="button"
                onClick={dismissError}
                aria-label="关闭错误提示"
                className="shrink-0 rounded-sm px-1.5 py-1 font-display text-[12px] opacity-70 transition-opacity hover:opacity-100"
              >
                ✕
              </button>
            </div>
          )}

          <div className="relative shrink-0 border-t border-parchment-300 bg-parchment-100/60 px-4 py-3 shadow-[0_-8px_24px_-12px_rgba(61,40,23,0.1)] md:px-8 dark:border-walnut-300/30 dark:bg-walnut-900/70">
            <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gilt-500/70 to-transparent" />
            <div className="mx-auto max-w-3xl">
              {/* 单行卡：textarea 左 + 圆角发送 icon 按钮右 */}
              <div className="flex items-end gap-2 rounded-md border border-walnut-50/30 bg-parchment-50 py-2 pl-4 pr-2 shadow-paper transition focus-within:border-gilt-500 focus-within:shadow-paper-lg focus-within:ring-1 focus-within:ring-gilt-500/30 dark:border-walnut-300/40 dark:bg-walnut-700/50 dark:focus-within:border-gilt-300 dark:focus-within:ring-gilt-300/30">
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                      e.preventDefault();
                      submit();
                    }
                  }}
                  rows={1}
                  disabled={running}
                  placeholder={placeholder}
                  className="block max-h-40 min-h-[28px] flex-1 resize-none bg-transparent py-1 font-display text-[14px] leading-7 text-ink-900 placeholder:font-display placeholder:italic placeholder:text-walnut-50/55 focus:outline-none disabled:opacity-50 dark:text-parchment-100 dark:placeholder:text-parchment-200/40"
                />
                <button
                  onClick={submit}
                  disabled={running || !question.trim()}
                  title={running ? "讨论中…" : "发送 (↵)"}
                  aria-label="发送"
                  className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-sm border transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                    running || !question.trim()
                      ? "border-walnut-50/30 bg-transparent text-walnut-100 dark:border-walnut-300/30 dark:text-parchment-200/60"
                      : "border-walnut-500 bg-walnut-500 text-parchment-100 hover:border-walnut-700 hover:bg-walnut-700 dark:border-gilt-500 dark:bg-gilt-500 dark:text-walnut-900 dark:hover:bg-gilt-300"
                  }`}
                >
                  {running ? (
                    <span className="relative inline-flex h-2 w-2">
                      <span className="absolute inset-0 rounded-full bg-current opacity-60 motion-safe:animate-ping" />
                      <span className="absolute inset-0 rounded-full bg-current" />
                    </span>
                  ) : (
                    <span className="text-lg leading-none">↵</span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>

      <GlassBoxDrawer data={glassBox} onClose={() => setGlassBox(null)} />
    </main>
  );
}
