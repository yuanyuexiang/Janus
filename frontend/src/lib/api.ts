export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

import { authHeaders, clearAccessKey } from "@/lib/auth";

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
