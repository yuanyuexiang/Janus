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

// ---------- 设置：厂商凭据 + 角色分配 ----------

async function mutate(path: string, method: string, body?: unknown): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: authHeaders(body ? { "Content-Type": "application/json" } : {}),
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    handleUnauthorized(res.status);
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `请求失败 (${res.status})`);
  }
}

// 厂商凭据（含该账号实时拉到的模型列表）
export type LlmCredential = {
  name: string;
  provider: string;
  api_base: string | null;
  has_key: boolean;
  models: string[];
};

export function getCredentials() {
  return apiGet<{ credentials: LlmCredential[] }>("/api/settings/credentials");
}

export function putCredential(body: {
  name: string;
  provider: string;
  api_base?: string | null;
  api_key?: string | null;
  models?: string[] | null;
}) {
  return mutate("/api/settings/credentials", "PUT", body);
}

export function deleteCredential(name: string) {
  return mutate(`/api/settings/credentials/${encodeURIComponent(name)}`, "DELETE");
}

// 实时调厂商接口列出该账号可用模型（顺带验证 Key）
export async function listLiveModels(body: {
  provider: string;
  api_base?: string | null;
  api_key?: string | null;
  name?: string | null;
}): Promise<{ ok: boolean; models: string[]; message: string }> {
  const res = await fetch(`${API_BASE}/api/settings/credentials/list-models`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    handleUnauthorized(res.status);
    return { ok: false, models: [], message: `获取失败 (${res.status})` };
  }
  return res.json() as Promise<{ ok: boolean; models: string[]; message: string }>;
}

// 各厂商可选模型目录（LiteLLM 内置），离线兜底
export function getModelCatalog() {
  return apiGet<{ catalog: Record<string, string[]> }>("/api/settings/catalog");
}

// 角色分配（角色 → 凭据 + 模型）
export type LlmRoleAssign = {
  role: string;
  label: string;
  tag: string;
  credential: string | null;
  model: string | null;
};

export function getRoleAssignments() {
  return apiGet<{ roles: LlmRoleAssign[] }>("/api/settings/roles");
}

export function putRoleAssignment(
  role: string,
  credential_name: string | null,
  model: string | null,
) {
  return mutate("/api/settings/roles", "PUT", { role, credential_name, model });
}
