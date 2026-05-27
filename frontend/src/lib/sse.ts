import { API_BASE } from "@/lib/api";
import type { ChatEvent } from "@/lib/types";

export type ChatRequestOpts = {
  conversationId?: string | null;
  mode?: "solo" | "mini" | "full";
  advisor?: string;
};

export async function* streamChat(
  question: string,
  opts: ChatRequestOpts = {},
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const body: Record<string, unknown> = { question };
  if (opts.conversationId) body.conversation_id = opts.conversationId;
  if (opts.mode) body.mode = opts.mode;
  if (opts.advisor) body.advisor = opts.advisor;

  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`Chat API ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    // SSE events are separated by blank lines
    let sep: number;
    while ((sep = buf.indexOf("\n\n")) !== -1) {
      const frame = buf.slice(0, sep);
      buf = buf.slice(sep + 2);

      const dataLines = frame
        .split("\n")
        .filter((l) => l.startsWith("data: "))
        .map((l) => l.slice(6));
      if (dataLines.length === 0) continue;

      try {
        const parsed = JSON.parse(dataLines.join("\n")) as ChatEvent;
        yield parsed;
      } catch (e) {
        console.warn("SSE parse error", e, dataLines);
      }
    }
  }
}
