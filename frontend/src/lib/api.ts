export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
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
  model: string | null;
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
