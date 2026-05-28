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

export type DisagreementItem = {
  point: string;
  sides: Record<string, string[]>;
};

export type RiskItem = {
  risk: string;
  severity: number; // 1-5
  mitigation?: string | null;
};

export type CouncilSummary = {
  verdict: "strong_consensus" | "weak_consensus" | "split";
  consensus: string[];
  disagreements: DisagreementItem[];
  key_variables: string[];
  risk_map: RiskItem[];
  final_summary: string;
};

export type ChatEvent =
  | { type: "session"; conversation_id: string; title: string | null; mode?: string | null }
  | { type: "council_start"; advisors: string[] }
  | {
      type: "advisor_start";
      advisor: string;
      display: string;
      role: string;
      color: string;
      active_skills?: string[];
    }
  | { type: "stage"; stage: string; advisor?: string }
  | { type: "text"; chunk: string; advisor?: string }
  | {
      type: "tool_call";
      tool: string;
      args: Record<string, unknown>;
      id: string;
      advisor?: string;
    }
  | {
      type: "tool_result";
      tool: string;
      result: Record<string, unknown>;
      advisor?: string;
    }
  | { type: "opinion"; full: AdvisorOpinion; advisor?: string }
  | { type: "advisor_done"; advisor: string }
  | { type: "usage"; tokens_in: number; tokens_out: number; advisor?: string }
  | { type: "synthesis_start"; opinion_count: number }
  | { type: "synthesis_text"; chunk: string }
  | { type: "synthesis"; full: CouncilSummary }
  | { type: "synthesis_usage"; tokens_in: number; tokens_out: number }
  | { type: "council_done" }
  | { type: "error"; code: string; message: string; advisor?: string };
