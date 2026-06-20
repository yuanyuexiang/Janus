"use client";

import { useCallback, useEffect, useState } from "react";

import Link from "next/link";

import {
  getCredentials,
  getModelCatalog,
  getRoleAssignments,
  putRoleAssignment,
  type LlmCredential,
  type LlmRoleAssign,
} from "@/lib/api";

const ADVISOR_ROLES = (r: LlmRoleAssign) => r.role !== "conductor" && r.role !== "router";

export function RoleAssignView() {
  const [roles, setRoles] = useState<LlmRoleAssign[] | null>(null);
  const [creds, setCreds] = useState<LlmCredential[]>([]);
  const [catalog, setCatalog] = useState<Record<string, string[]>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [bulkCred, setBulkCred] = useState("");
  const [bulkModel, setBulkModel] = useState("");

  const load = useCallback(async () => {
    try {
      const [r, c] = await Promise.all([getRoleAssignments(), getCredentials()]);
      setRoles(r.roles);
      setCreds(c.credentials);
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

  const credByName: Record<string, LlmCredential> = Object.fromEntries(creds.map((c) => [c.name, c]));

  // 某凭据下可选模型：优先用它实时拉到的列表，空则用 LiteLLM 离线目录兜底
  function modelsOf(credName: string | null): string[] {
    if (!credName) return [];
    const c = credByName[credName];
    if (!c) return [];
    return c.models.length ? c.models : (catalog[c.provider] ?? []);
  }

  function flash(role: string) {
    setSaved(role);
    setTimeout(() => setSaved((s) => (s === role ? null : s)), 1400);
  }

  async function persist(role: string, credential: string | null, model: string | null) {
    setRoles((prev) => prev?.map((r) => (r.role === role ? { ...r, credential, model } : r)) ?? prev);
    try {
      await putRoleAssignment(role, credential, model);
      flash(role);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  // 换凭据 → 模型清空（不同凭据模型不同）
  const onCredChange = (role: string, cred: string) => persist(role, cred || null, null);
  const onModelChange = (role: string, model: string, cred: string | null) =>
    persist(role, cred, model || null);

  async function applyToAdvisors() {
    if (!bulkCred || !bulkModel || !roles) return;
    const advisors = roles.filter(ADVISOR_ROLES);
    setRoles((prev) =>
      prev?.map((r) => (ADVISOR_ROLES(r) ? { ...r, credential: bulkCred, model: bulkModel } : r)) ?? prev,
    );
    try {
      await Promise.all(advisors.map((r) => putRoleAssignment(r.role, bulkCred, bulkModel)));
      flash("__bulk__");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const configured = roles?.filter((r) => r.credential && r.model).length ?? 0;
  const total = roles?.length ?? 0;

  const selectCls =
    "rounded-lg border border-parchment-300/70 bg-parchment-50 px-2.5 py-1.5 font-display text-[13px] text-ink-900 focus:border-gilt-500/70 focus:outline-none focus:ring-2 focus:ring-gilt-500/20 disabled:opacity-40 dark:border-walnut-300/35 dark:bg-walnut-700/60 dark:text-parchment-100";

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <header className="relative flex items-center justify-between border-b border-parchment-300/60 bg-parchment-50/80 px-4 py-4 backdrop-blur md:px-8 dark:border-walnut-300/20 dark:bg-walnut-900/60">
        <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-gilt-500/60 to-transparent" />
        <div className="flex items-baseline gap-3">
          <h2 className="font-display text-xl font-medium text-walnut-500 dark:text-parchment-100">角色设置</h2>
          <span className="font-display text-[10px] uppercase tracking-[0.3em] text-gilt-700 dark:text-gilt-300">
            Role Routing
          </span>
        </div>
        {roles && (
          <span
            className={`rounded-full px-2.5 py-1 font-display text-[11px] ${
              configured === total
                ? "bg-sage-500/15 text-sage-700 dark:text-sage-300"
                : "bg-gilt-500/15 text-gilt-700 dark:text-gilt-300"
            }`}
          >
            {configured}/{total} 已配置
          </span>
        )}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-8 md:px-8 md:py-10">
        <div className="mx-auto max-w-2xl space-y-3">
          <p className="font-display text-[13px] italic leading-relaxed text-ink-600 dark:text-parchment-200/65">
            每个角色：先选厂商凭据，再从该凭据的模型列表里选具体模型。未配置的角色轮到时会清晰报错、不发言。
          </p>

          {error && (
            <div className="rounded-xl border border-vermillion-500/30 bg-vermillion-500/[0.08] p-4 font-display text-[13px] text-vermillion-700 dark:border-vermillion-300/30 dark:text-vermillion-300">
              {error}
            </div>
          )}

          {!roles ? (
            <p className="font-display text-[13px] italic text-walnut-50/70 dark:text-parchment-200/50">正在加载…</p>
          ) : creds.length === 0 ? (
            <div className="rounded-xl border border-dashed border-parchment-300/70 p-6 text-center font-display text-[13px] italic text-ink-400 dark:border-walnut-300/30 dark:text-parchment-200/50">
              还没有厂商，先去{" "}
              <Link href="/settings/models" className="text-gilt-700 dark:text-gilt-300">模型设置</Link>{" "}
              添加。
            </div>
          ) : (
            <>
              {/* 批量套用到 6 位顾问 */}
              <div className="flex flex-wrap items-center gap-2 rounded-xl border border-parchment-300/50 bg-parchment-50/50 px-4 py-3 dark:border-walnut-300/20 dark:bg-walnut-900/30">
                <span className="font-display text-[12px] text-walnut-100 dark:text-parchment-200/70">批量设顾问：</span>
                <select
                  value={bulkCred}
                  onChange={(e) => { setBulkCred(e.target.value); setBulkModel(""); }}
                  className={selectCls}
                >
                  <option value="">选凭据</option>
                  {creds.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
                </select>
                <select
                  value={bulkModel}
                  onChange={(e) => setBulkModel(e.target.value)}
                  disabled={!bulkCred}
                  className={selectCls}
                >
                  <option value="">选模型</option>
                  {modelsOf(bulkCred || null).map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
                <button
                  type="button"
                  onClick={applyToAdvisors}
                  disabled={!bulkCred || !bulkModel}
                  className="rounded-lg border border-walnut-500/40 px-3 py-1.5 font-display text-[12px] text-walnut-500 transition-colors hover:border-gilt-500 hover:bg-gilt-500/[0.08] disabled:opacity-40 dark:border-gilt-500/40 dark:text-gilt-100"
                >
                  套用到全部顾问
                </button>
                {saved === "__bulk__" && (
                  <span className="font-display text-[12px] text-sage-700 dark:text-sage-300">✓ 已套用</span>
                )}
              </div>

              {roles.map((r) => {
                const opts = modelsOf(r.credential);
                const modelOpts = r.model && !opts.includes(r.model) ? [r.model, ...opts] : opts;
                const incomplete = !r.credential || !r.model;
                return (
                  <section
                    key={r.role}
                    className={`flex flex-wrap items-center justify-between gap-3 rounded-2xl border px-5 py-4 shadow-paper ${
                      incomplete
                        ? "border-gilt-500/50 bg-gilt-500/[0.06] dark:border-gilt-500/40 dark:bg-gilt-500/[0.08]"
                        : "border-parchment-300/60 bg-parchment-100/40 dark:border-walnut-300/25 dark:bg-walnut-700/30"
                    }`}
                  >
                    <div className="min-w-[96px]">
                      <h3 className="font-display text-[15px] font-medium text-walnut-500 dark:text-parchment-100">
                        {r.label}
                        <span className="ml-2 font-display text-[11px] font-normal text-ink-400 dark:text-parchment-200/45">{r.tag}</span>
                      </h3>
                      <span className="font-mono text-[10px] text-ink-400 dark:text-parchment-200/40">{r.role}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {saved === r.role && (
                        <span className="font-display text-[12px] text-sage-700 dark:text-sage-300">✓</span>
                      )}
                      {incomplete && (
                        <span className="font-display text-[11px] text-gilt-700 dark:text-gilt-300">未配</span>
                      )}
                      <select
                        value={r.credential ?? ""}
                        onChange={(e) => onCredChange(r.role, e.target.value)}
                        className={selectCls}
                      >
                        <option value="">未分配</option>
                        {creds.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
                      </select>
                      <select
                        value={r.model ?? ""}
                        onChange={(e) => onModelChange(r.role, e.target.value, r.credential)}
                        disabled={!r.credential}
                        className={selectCls}
                      >
                        <option value="">{r.credential ? "选模型" : "先选凭据"}</option>
                        {modelOpts.map((m) => <option key={m} value={m}>{m}</option>)}
                      </select>
                    </div>
                  </section>
                );
              })}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
