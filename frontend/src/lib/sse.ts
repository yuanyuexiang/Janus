import { API_BASE } from "@/lib/api";
import type { ChatEvent } from "@/lib/types";

export async function* streamChat(
  question: string,
  conversationId?: string | null,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(
      conversationId
        ? { question, conversation_id: conversationId }
        : { question },
    ),
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
