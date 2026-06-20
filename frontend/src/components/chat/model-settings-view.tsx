"use client";

import { useCallback, useEffect, useState } from "react";

import {
  getLlmSettings,
  putLlmSetting,
  testLlmSetting,
  type LlmRoleSetting,
} from "@/lib/api";

const MODEL_HINTS = "如 openai/gpt-4o · anthropic/claude-opus-4-6 · deepseek/deepseek-chat · dashscope/qwen-max · ollama/llama3";

export function ModelSettingsView() {
  const [roles, setRoles] = useState<LlmRoleSetting[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await getLlmSettings();
      setRoles(r.roles);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <header className="relative border-b border-parchment-300/60 bg-parchment-50/80 px-4 py-4 backdrop-blur md:px-8 dark:border-walnut-300/20 dark:bg-walnut-900/60">
        <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-gilt-500/60 to-transparent" />
        <div className="flex items-baseline gap-3">
          <h1 className="font-display text-xl font-medium text-walnut-500 dark:text-parchment-100">
            模型配置
          </h1>
          <span className="font-display text-[10px] uppercase tracking-[0.3em] text-gilt-700 dark:text-gilt-300">
            Model Routing
          </span>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-8 md:px-8 md:py-10">
        <div className="mx-auto max-w-3xl space-y-6">
          <p className="font-display text-[13px] italic leading-relaxed text-ink-600 dark:text-parchment-200/65">
            为三个角色分别接入模型。底层经 LiteLLM 统一调用，支持 OpenAI / Anthropic / 通义 /
            DeepSeek / 文心 / Ollama 本地模型等。模型名用 <code className="font-mono text-[12px]">厂商/模型</code> 形式。
            三个角色都需配置后对话才能正常运行。
          </p>

          {error ? (
            <div className="rounded-xl border border-vermillion-500/30 bg-vermillion-500/[0.08] p-4 font-display text-[13px] text-vermillion-700 dark:border-vermillion-300/30 dark:text-vermillion-300">
              加载失败：{error}
            </div>
          ) : !roles ? (
            <p className="font-display text-[13px] italic text-walnut-50/70 dark:text-parchment-200/50">
              正在加载…
            </p>
          ) : (
            roles.map((r) => <RoleCard key={r.role} setting={r} onSaved={load} />)
          )}
        </div>
      </div>
    </div>
  );
}

type Status = { kind: "idle" | "ok" | "err"; msg?: string };

function RoleCard({ setting, onSaved }: { setting: LlmRoleSetting; onSaved: () => void }) {
  const [model, setModel] = useState(setting.model ?? "");
  const [apiBase, setApiBase] = useState(setting.api_base ?? "");
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  async function save() {
    if (!model.trim() || saving) return;
    setSaving(true);
    setStatus({ kind: "idle" });
    try {
      await putLlmSetting({
        role: setting.role,
        model: model.trim(),
        api_base: apiBase.trim() || null,
        api_key: apiKey || null, // 空=不改
      });
      setApiKey("");
      setStatus({ kind: "ok", msg: "已保存" });
      onSaved();
    } catch (e) {
      setStatus({ kind: "err", msg: e instanceof Error ? e.message : String(e) });
    } finally {
      setSaving(false);
    }
  }

  async function test() {
    if (!model.trim() || testing) return;
    setTesting(true);
    setStatus({ kind: "idle" });
    const r = await testLlmSetting({
      role: setting.role,
      model: model.trim(),
      api_base: apiBase.trim() || null,
      api_key: apiKey || null,
    });
    setStatus({ kind: r.ok ? "ok" : "err", msg: r.message });
    setTesting(false);
  }

  const inputCls =
    "w-full rounded-lg border border-parchment-300/70 bg-parchment-50 px-3 py-2 font-display text-[13.5px] text-ink-900 placeholder:text-walnut-50/45 focus:border-gilt-500/70 focus:outline-none focus:ring-2 focus:ring-gilt-500/20 dark:border-walnut-300/35 dark:bg-walnut-700/50 dark:text-parchment-100 dark:placeholder:text-parchment-200/35";
  const labelCls = "mb-1.5 block font-display text-[11px] uppercase tracking-[0.18em] text-walnut-100 dark:text-parchment-200/70";

  return (
    <section className="rounded-2xl border border-parchment-300/60 bg-parchment-100/40 p-6 shadow-paper dark:border-walnut-300/25 dark:bg-walnut-700/30">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-display text-[15px] font-medium text-walnut-500 dark:text-parchment-100">
          {setting.label}
        </h2>
        <span className="font-mono text-[10px] text-ink-400 dark:text-parchment-200/40">{setting.role}</span>
      </div>

      <div className="space-y-3">
        <div>
          <label className={labelCls}>模型</label>
          <input
            value={model}
            onChange={(e) => { setModel(e.target.value); setStatus({ kind: "idle" }); }}
            placeholder="openai/gpt-4o"
            className={`${inputCls} font-mono`}
          />
          <p className="mt-1 font-display text-[11px] text-ink-400 dark:text-parchment-200/40">{MODEL_HINTS}</p>
        </div>
        <div>
          <label className={labelCls}>API Base（可选，自建/代理/本地填）</label>
          <input
            value={apiBase}
            onChange={(e) => { setApiBase(e.target.value); setStatus({ kind: "idle" }); }}
            placeholder="留空用厂商默认；如 https://api.deepseek.com"
            className={`${inputCls} font-mono`}
          />
        </div>
        <div>
          <label className={labelCls}>API Key</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => { setApiKey(e.target.value); setStatus({ kind: "idle" }); }}
            placeholder={setting.has_key ? "已配置 —— 留空不修改" : "填入该厂商的 API Key"}
            className={inputCls}
          />
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2">
        <button
          type="button"
          onClick={save}
          disabled={saving || !model.trim()}
          className="rounded-lg bg-walnut-500 px-4 py-2 font-display text-[13px] tracking-wider text-parchment-100 transition-colors hover:bg-walnut-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-gilt-500 dark:text-walnut-900 dark:hover:bg-gilt-300 nasdaq:bg-gilt-500 nasdaq:text-parchment-50 nasdaq:hover:bg-gilt-300"
        >
          {saving ? "保存中…" : "保存"}
        </button>
        <button
          type="button"
          onClick={test}
          disabled={testing || !model.trim()}
          className="rounded-lg border border-parchment-300/70 px-4 py-2 font-display text-[13px] tracking-wider text-walnut-100 transition-colors hover:border-gilt-500 hover:text-gilt-700 disabled:opacity-40 dark:border-walnut-300/30 dark:text-parchment-200/70 dark:hover:border-gilt-300 dark:hover:text-gilt-300"
        >
          {testing ? "测试中…" : "测试连接"}
        </button>
        {status.kind !== "idle" && (
          <span
            className={`font-display text-[12px] ${
              status.kind === "ok"
                ? "text-sage-700 dark:text-sage-300"
                : "text-vermillion-700 dark:text-vermillion-300"
            }`}
          >
            {status.kind === "ok" ? "✓ " : "✕ "}
            {status.msg}
          </span>
        )}
      </div>
    </section>
  );
}
