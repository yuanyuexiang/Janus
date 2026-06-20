"use client";

import { useCallback, useEffect, useState } from "react";

import {
  deleteCredential,
  getCredentials,
  getModelCatalog,
  listLiveModels,
  putCredential,
  type LlmCredential,
} from "@/lib/api";

// 厂商元信息。id 与 LiteLLM provider 一致；"__custom__" 兜底（手填完整串）。
type Provider = { id: string; label: string; base: string; needsBase: boolean; keyHint: string; abbr: string };

const PROVIDERS: Provider[] = [
  { id: "deepseek", label: "DeepSeek 深度求索", base: "", needsBase: false, keyHint: "sk-…（platform.deepseek.com）", abbr: "DS" },
  { id: "openai", label: "OpenAI", base: "", needsBase: false, keyHint: "sk-…", abbr: "AI" },
  { id: "anthropic", label: "Anthropic Claude", base: "", needsBase: false, keyHint: "sk-ant-…", abbr: "An" },
  { id: "dashscope", label: "通义千问 DashScope", base: "", needsBase: false, keyHint: "sk-…（阿里云百炼）", abbr: "Qw" },
  { id: "moonshot", label: "月之暗面 Kimi", base: "", needsBase: false, keyHint: "sk-…", abbr: "Ki" },
  { id: "gemini", label: "Google Gemini", base: "", needsBase: false, keyHint: "AIza…", abbr: "Ge" },
  { id: "openrouter", label: "OpenRouter 聚合", base: "", needsBase: false, keyHint: "sk-or-…", abbr: "OR" },
  { id: "xai", label: "xAI Grok", base: "", needsBase: false, keyHint: "xai-…", abbr: "Gr" },
  { id: "ollama", label: "Ollama 本地", base: "http://localhost:11434", needsBase: true, keyHint: "本地通常留空", abbr: "Ol" },
  { id: "openai_compatible", label: "OpenAI 兼容（自定义 Base）", base: "", needsBase: true, keyHint: "该服务的 API Key", abbr: "兼" },
  { id: "__custom__", label: "其他（手填完整串）", base: "", needsBase: false, keyHint: "该服务的 API Key", abbr: "…" },
];
const PROVIDER_BY_ID: Record<string, Provider> = Object.fromEntries(PROVIDERS.map((p) => [p.id, p]));

type EditTarget = { mode: "new" } | { mode: "edit"; cred: LlmCredential } | null;

export function ModelPoolView() {
  const [creds, setCreds] = useState<LlmCredential[] | null>(null);
  const [catalog, setCatalog] = useState<Record<string, string[]>>({});
  const [error, setError] = useState<string | null>(null);
  const [edit, setEdit] = useState<EditTarget>(null);

  const load = useCallback(async () => {
    try {
      const r = await getCredentials();
      setCreds(r.credentials);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    getModelCatalog()
      .then((r) => setCatalog(r.catalog))
      .catch(() => setCatalog({}));
  }, [load]);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <header className="relative flex items-center justify-between border-b border-parchment-300/60 bg-parchment-50/80 px-4 py-4 backdrop-blur md:px-8 dark:border-walnut-300/20 dark:bg-walnut-900/60">
        <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-gilt-500/60 to-transparent" />
        <div className="flex items-baseline gap-3">
          <h2 className="font-display text-xl font-medium text-walnut-500 dark:text-parchment-100">模型设置</h2>
          <span className="font-display text-[10px] uppercase tracking-[0.3em] text-gilt-700 dark:text-gilt-300">Providers</span>
        </div>
        <button
          type="button"
          onClick={() => setEdit({ mode: "new" })}
          className="rounded-lg border border-walnut-500/40 px-3 py-1.5 font-display text-[12px] tracking-wider text-walnut-500 transition-colors hover:border-gilt-500 hover:bg-gilt-500/[0.08] dark:border-gilt-500/40 dark:text-gilt-100 dark:hover:border-gilt-300"
        >
          + 添加厂商
        </button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-8 md:px-8 md:py-10">
        <div className="mx-auto max-w-2xl space-y-3">
          <p className="font-display text-[13px] italic leading-relaxed text-ink-600 dark:text-parchment-200/65">
            一个厂商账号一条：填 Key 后「获取真实模型列表」（顺带验证 Key）。具体哪个角色用哪个模型，在「角色设置」里挑。
          </p>

          {error ? (
            <div className="rounded-xl border border-vermillion-500/30 bg-vermillion-500/[0.08] p-4 font-display text-[13px] text-vermillion-700 dark:border-vermillion-300/30 dark:text-vermillion-300">
              加载失败：{error}
            </div>
          ) : !creds ? (
            <p className="font-display text-[13px] italic text-walnut-50/70 dark:text-parchment-200/50">正在加载…</p>
          ) : creds.length === 0 ? (
            <button
              type="button"
              onClick={() => setEdit({ mode: "new" })}
              className="w-full rounded-xl border border-dashed border-parchment-300/70 p-8 text-center font-display text-[13px] italic text-ink-400 transition-colors hover:border-gilt-500/60 hover:text-gilt-700 dark:border-walnut-300/30 dark:text-parchment-200/50 dark:hover:text-gilt-300"
            >
              还没有厂商，点这里添加第一个
            </button>
          ) : (
            <ul className="divide-y divide-parchment-300/50 overflow-hidden rounded-2xl border border-parchment-300/60 bg-parchment-100/40 shadow-paper dark:divide-walnut-300/15 dark:border-walnut-300/25 dark:bg-walnut-700/30">
              {creds.map((c) => (
                <CredentialRow
                  key={c.name}
                  cred={c}
                  onEdit={() => setEdit({ mode: "edit", cred: c })}
                  onDeleted={load}
                />
              ))}
            </ul>
          )}
        </div>
      </div>

      {edit && (
        <CredentialModal
          key={edit.mode === "edit" ? edit.cred.name : "__new__"}
          target={edit}
          catalog={catalog}
          onClose={() => setEdit(null)}
          onSaved={() => { setEdit(null); load(); }}
        />
      )}
    </div>
  );
}

// ---------- 列表行 ----------

function CredentialRow({
  cred,
  onEdit,
  onDeleted,
}: {
  cred: LlmCredential;
  onEdit: () => void;
  onDeleted: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const prov = PROVIDER_BY_ID[cred.provider];
  const nModels = cred.models?.length ?? 0;

  async function doDelete() {
    setBusy(true);
    try {
      await deleteCredential(cred.name);
      onDeleted();
    } catch {
      setBusy(false);
      setConfirming(false);
    }
  }

  return (
    <li className="flex items-center gap-3 px-4 py-3 md:px-5">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gilt-500/15 font-display text-[12px] font-medium text-gilt-700 dark:text-gilt-300">
        {prov?.abbr ?? "?"}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-display text-[14px] font-medium text-walnut-500 dark:text-parchment-100">{cred.name}</p>
        <p className="mt-0.5 flex flex-wrap items-center gap-x-2 font-display text-[11.5px] text-ink-400 dark:text-parchment-200/45">
          <span>{prov?.label ?? cred.provider}</span>
          <span className="text-parchment-300 dark:text-walnut-300/40">·</span>
          <span className={nModels ? "" : "text-gilt-700 dark:text-gilt-300"}>
            {nModels ? `${nModels} 个模型` : "未获取模型"}
          </span>
          <span className="text-parchment-300 dark:text-walnut-300/40">·</span>
          <span className={cred.has_key ? "text-sage-700 dark:text-sage-300" : "text-ink-400 dark:text-parchment-200/40"}>
            {cred.has_key ? "● 已配 Key" : "○ 无 Key"}
          </span>
        </p>
      </div>

      {confirming ? (
        <div className="flex shrink-0 items-center gap-1">
          <span className="hidden font-display text-[11px] text-ink-400 sm:inline dark:text-parchment-200/45">删除？</span>
          <button
            type="button"
            onClick={doDelete}
            disabled={busy}
            className="rounded-md px-2.5 py-1 font-display text-[12px] text-vermillion-700 hover:bg-vermillion-500/10 disabled:opacity-40 dark:text-vermillion-300"
          >
            {busy ? "…" : "确认"}
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            className="rounded-md px-2.5 py-1 font-display text-[12px] text-walnut-100 hover:text-walnut-500 dark:text-parchment-200/60"
          >
            取消
          </button>
        </div>
      ) : (
        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={onEdit}
            className="rounded-md px-2.5 py-1 font-display text-[12px] text-walnut-500 transition-colors hover:bg-gilt-500/10 hover:text-gilt-700 dark:text-parchment-200/70 dark:hover:text-gilt-300"
          >
            编辑
          </button>
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="rounded-md px-2.5 py-1 font-display text-[12px] text-ink-400 transition-colors hover:bg-vermillion-500/10 hover:text-vermillion-700 dark:text-parchment-200/40 dark:hover:text-vermillion-300"
          >
            删除
          </button>
        </div>
      )}
    </li>
  );
}

// ---------- 编辑弹窗 ----------

type Status = { kind: "idle" | "ok" | "err"; msg?: string };

function CredentialModal({
  target,
  catalog,
  onClose,
  onSaved,
}: {
  target: { mode: "new" } | { mode: "edit"; cred: LlmCredential };
  catalog: Record<string, string[]>;
  onClose: () => void;
  onSaved: () => void;
}) {
  const initial = target.mode === "edit" ? target.cred : undefined;
  const [name, setName] = useState(initial?.name ?? "");
  const [provider, setProvider] = useState(initial?.provider ?? "deepseek");
  const [apiBase, setApiBase] = useState(initial?.api_base ?? "");
  const [apiKey, setApiKey] = useState("");
  const [models, setModels] = useState<string[]>(initial?.models ?? []);
  const [fetching, setFetching] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  // Esc 关闭
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const cur = PROVIDER_BY_ID[provider] ?? PROVIDER_BY_ID.deepseek;
  const hasKey = initial?.has_key ?? false;
  const baseMissing = cur.needsBase && !apiBase.trim();
  const canFetch = !baseMissing && (provider === "ollama" || !!apiKey || hasKey) && !fetching;
  const canSave = !!name.trim() && !!provider && !baseMissing && !busy;
  const offlineCount = (catalog[provider] ?? []).length;

  function pickProvider(id: string) {
    setProvider(id);
    setApiBase(PROVIDER_BY_ID[id]?.base ?? "");
    setModels([]);
    setStatus({ kind: "idle" });
  }

  async function fetchModels() {
    if (!canFetch) return;
    setFetching(true);
    setStatus({ kind: "idle" });
    const r = await listLiveModels({
      provider,
      api_base: apiBase.trim() || null,
      api_key: apiKey || null,
      name: target.mode === "edit" ? name : null,
    });
    if (r.ok) setModels(r.models);
    setStatus({ kind: r.ok ? "ok" : "err", msg: r.message });
    setFetching(false);
  }

  function useOffline() {
    setModels(catalog[provider] ?? []);
    setStatus({ kind: "ok", msg: `已载入 ${offlineCount} 个（离线目录，未验证 Key）` });
  }

  async function save() {
    if (!canSave) return;
    setBusy(true);
    setStatus({ kind: "idle" });
    try {
      await putCredential({
        name: name.trim(),
        provider,
        api_base: apiBase.trim() || null,
        api_key: apiKey || null,
        models,
        original_name: target.mode === "edit" ? initial?.name : undefined,
      });
      onSaved();
    } catch (e) {
      setStatus({ kind: "err", msg: e instanceof Error ? e.message : String(e) });
      setBusy(false);
    }
  }

  const inputCls =
    "w-full rounded-lg border border-parchment-300/70 bg-parchment-50 px-3 py-2 font-display text-[13.5px] text-ink-900 placeholder:text-walnut-50/45 focus:border-gilt-500/70 focus:outline-none focus:ring-2 focus:ring-gilt-500/20 dark:border-walnut-300/35 dark:bg-walnut-700/50 dark:text-parchment-100 dark:placeholder:text-parchment-200/35";
  const labelCls = "mb-1.5 block font-display text-[11px] uppercase tracking-[0.18em] text-walnut-100 dark:text-parchment-200/70";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button type="button" aria-label="关闭" onClick={onClose} className="absolute inset-0 cursor-default bg-black/50 backdrop-blur-sm" />
      <div
        role="dialog"
        aria-modal="true"
        className="relative z-10 max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-parchment-300/70 bg-parchment-50 p-6 shadow-paper-lg dark:border-walnut-300/25 dark:bg-walnut-900"
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-display text-lg font-medium text-walnut-500 dark:text-parchment-100">
            {target.mode === "edit" ? `编辑「${initial?.name}」` : "添加厂商"}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 font-display text-[16px] leading-none text-ink-400 hover:text-walnut-500 dark:text-parchment-200/50 dark:hover:text-parchment-100"
          >
            ×
          </button>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className={labelCls}>名称</label>
              <input
                value={name}
                onChange={(e) => { setName(e.target.value); setStatus({ kind: "idle" }); }}
                placeholder="如 我的 DeepSeek"
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>厂商</label>
              <select value={provider} onChange={(e) => pickProvider(e.target.value)} className={inputCls}>
                {PROVIDERS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className={labelCls}>API Base{cur.needsBase ? "" : "（可选）"}</label>
            <input
              value={apiBase}
              onChange={(e) => { setApiBase(e.target.value); setStatus({ kind: "idle" }); }}
              placeholder={cur.needsBase ? (cur.base || "如 https://your-endpoint/v1") : "留空用厂商默认端点"}
              className={`${inputCls} font-mono ${baseMissing ? "border-vermillion-500/60" : ""}`}
            />
          </div>

          <div>
            <label className={labelCls}>API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => { setApiKey(e.target.value); setStatus({ kind: "idle" }); }}
              placeholder={hasKey ? "已配置 —— 留空不修改" : cur.keyHint}
              className={inputCls}
            />
          </div>

          <div className="rounded-xl border border-parchment-300/50 bg-parchment-100/50 p-3 dark:border-walnut-300/20 dark:bg-walnut-700/30">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              <button
                type="button"
                onClick={fetchModels}
                disabled={!canFetch}
                className="font-display text-[12px] text-gilt-700 underline-offset-2 hover:underline disabled:cursor-not-allowed disabled:text-ink-400 disabled:no-underline dark:text-gilt-300 dark:disabled:text-parchment-200/40"
              >
                {fetching ? "获取中…" : models.length ? "↻ 重新获取模型列表" : "↓ 获取真实模型列表"}
              </button>
              {provider !== "__custom__" && offlineCount > 0 && (
                <button type="button" onClick={useOffline} className="font-display text-[12px] text-ink-400 underline-offset-2 hover:underline dark:text-parchment-200/50">
                  用离线目录（{offlineCount}）
                </button>
              )}
              {!canFetch && !hasKey && !apiKey && provider !== "ollama" && !fetching && (
                <span className="font-display text-[11px] italic text-ink-400 dark:text-parchment-200/40">填好 Key 后可获取</span>
              )}
            </div>
            <p className="mt-2 font-display text-[12px] text-ink-600 dark:text-parchment-200/60">
              {models.length
                ? <>已就绪 <span className="text-sage-700 dark:text-sage-300">{models.length}</span> 个：<span className="font-mono text-[11px] text-ink-400 dark:text-parchment-200/45">{models.slice(0, 8).join("、")}{models.length > 8 ? " …" : ""}</span></>
                : "还没有模型列表 —— 角色设置里就没法给角色挑模型"}
            </p>
          </div>

          {status.kind !== "idle" && (
            <p className={`font-display text-[12px] ${status.kind === "ok" ? "text-sage-700 dark:text-sage-300" : "text-vermillion-700 dark:text-vermillion-300"}`}>
              {status.kind === "ok" ? "✓ " : "✕ "}{status.msg}
            </p>
          )}
        </div>

        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 font-display text-[13px] text-walnut-100 hover:text-walnut-500 dark:text-parchment-200/60 dark:hover:text-parchment-100"
          >
            取消
          </button>
          <button
            type="button"
            onClick={save}
            disabled={!canSave}
            className="rounded-lg bg-walnut-500 px-5 py-2 font-display text-[13px] tracking-wider text-parchment-100 transition-colors hover:bg-walnut-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-gilt-500 dark:text-walnut-900 dark:hover:bg-gilt-300 nasdaq:bg-gilt-500 nasdaq:text-parchment-50 nasdaq:hover:bg-gilt-300"
          >
            {busy ? "保存中…" : "保存"}
          </button>
        </div>
      </div>
    </div>
  );
}
