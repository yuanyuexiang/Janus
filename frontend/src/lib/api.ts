import { authHeaders, clearAccessKey } from "@/lib/auth";

declare global {
  interface Window {
    __API_BASE__?: string;
  }
}

// 浏览器端 API 地址来源优先级：
//  1) 运行时注入：layout 从容器环境变量 API_BASE 写进 window.__API_BASE__
//     —— 这样部署时在 docker-compose 的 environment 里配即可，不用重新构建
//  2) 构建时 NEXT_PUBLIC_API_BASE（pnpm dev 时用 .env.local 设）
//  3) 相对路径 ""（同源 Traefik 部署：浏览器走 /api，反代转后端，任何域名都对）
function resolveApiBase(): string {
  if (typeof window !== "undefined" && typeof window.__API_BASE__ === "string") {
    return window.__API_BASE__;
  }
  return process.env.NEXT_PUBLIC_API_BASE ?? "";
}

export const API_BASE = resolveApiBase();

/** 401 → 清掉失效密钥并退回首页解锁。 */
export function handleUnauthorized(status: number): boolean {
  if (status === 401 && typeof window !== "undefined") {
    clearAccessKey();
    if (window.location.pathname !== "/") window.location.href = "/";
    return true;
  }
  return false;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (!res.ok) {
    handleUnauthorized(res.status);
    throw new Error(`API ${path} -> ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export type ConversationSummary = {
  id: string;
  title: string | null;
  mode: string | null;
  created_at: string;
  updated_at: string;
};

export type StoredMessage = {
  id: number;
  role: string;
  agent: string | null;
  content: string | null;
  structured: import("@/lib/types").AdvisorOpinion | null;
  tool_calls: Array<{
    id?: string;
    tool: string;
    args: Record<string, unknown>;
    result?: Record<string, unknown>;
  }>;
  active_skills: string[];
  model: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  created_at: string;
};

export type ConversationDetail = ConversationSummary & {
  messages: StoredMessage[];
};

export function listConversations() {
  return apiGet<ConversationSummary[]>("/api/conversations");
}

export function getConversation(id: string) {
  return apiGet<ConversationDetail>(`/api/conversations/${id}`);
}

export async function renameConversation(id: string, title: string): Promise<ConversationSummary> {
  const res = await fetch(`${API_BASE}/api/conversations/${id}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ title }),
  });
  if (!res.ok) {
    handleUnauthorized(res.status);
    throw new Error(`Rename failed: ${res.status}`);
  }
  return res.json() as Promise<ConversationSummary>;
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/conversations/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok && res.status !== 204) {
    handleUnauthorized(res.status);
    throw new Error(`Delete failed: ${res.status}`);
  }
}

export function exportConversationUrl(id: string, format: "md" | "json" = "md"): string {
  return `${API_BASE}/api/conversations/${id}/export?format=${format}`;
}

// ---------- 模型配置（LLM settings）----------

export type LlmRoleSetting = {
  role: "conductor" | "advisor" | "router";
  label: string;
  model: string | null;
  api_base: string | null;
  has_key: boolean;
};

export type LlmSettingsResp = { roles: LlmRoleSetting[] };

export function getLlmSettings() {
  return apiGet<LlmSettingsResp>("/api/settings/llm");
}

export async function putLlmSetting(body: {
  role: string;
  model: string;
  api_base?: string | null;
  api_key?: string | null;
}): Promise<void> {
  const res = await fetch(`${API_BASE}/api/settings/llm`, {
    method: "PUT",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    handleUnauthorized(res.status);
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `保存失败 (${res.status})`);
  }
}

export async function testLlmSetting(body: {
  role: string;
  model: string;
  api_base?: string | null;
  api_key?: string | null;
}): Promise<{ ok: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/api/settings/llm/test`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    handleUnauthorized(res.status);
    return { ok: false, message: `测试请求失败 (${res.status})` };
  }
  return res.json() as Promise<{ ok: boolean; message: string }>;
}
