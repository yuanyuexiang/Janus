export type Evidence = {
  claim: string;
  detail: string;
  source_tool?: string | null;
};

export type AdvisorOpinion = {
  agent: string;
  stance: "bullish" | "neutral" | "bearish" | "conditional";
  confidence: number;
  summary_for_user: string;
  key_points: Evidence[];
  concerns: string[];
  what_could_change_my_mind: string[];
};

export type ChatEvent =
  | { type: "session"; conversation_id: string; title: string | null }
  | {
      type: "advisor_start";
      advisor: string;
      display: string;
      role: string;
      color: string;
      active_skills?: string[];
    }
  | { type: "stage"; stage: string }
  | { type: "text"; chunk: string }
  | { type: "tool_call"; tool: string; args: Record<string, unknown>; id: string }
  | { type: "tool_result"; tool: string; result: Record<string, unknown> }
  | { type: "opinion"; full: AdvisorOpinion }
  | { type: "error"; code: string; message: string };
