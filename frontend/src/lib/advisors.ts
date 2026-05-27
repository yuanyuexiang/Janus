export type AdvisorMeta = {
  name: string;
  display: string;
  role: string;
  color: string;
};

export const ADVISOR_META: Record<string, AdvisorMeta> = {
  tao_shu:    { name: "tao_shu",    display: "韬叔",   role: "宏观", color: "#4A6FA5" },
  lan_jie:    { name: "lan_jie",    display: "岚姐",   role: "行业", color: "#B5651D" },
  ming_ge:    { name: "ming_ge",    display: "明哥",   role: "价值", color: "#7B8B5C" },
  rui_feng:   { name: "rui_feng",   display: "锐锋",   role: "趋势", color: "#5D478B" },
  leng_chuan: { name: "leng_chuan", display: "冷川",   role: "风险", color: "#8B3A3A" },
  ling_du:    { name: "ling_du",    display: "零度",   role: "量化", color: "#2F4F4F" },
};

export const MINI_COUNCIL = ["tao_shu", "lan_jie", "ming_ge"];
export const FULL_COUNCIL = [
  "tao_shu",
  "lan_jie",
  "ming_ge",
  "rui_feng",
  "leng_chuan",
  "ling_du",
];

export function getAdvisorMeta(name: string): AdvisorMeta {
  return (
    ADVISOR_META[name] ?? { name, display: name, role: "", color: "#888888" }
  );
}

const STAGE_LABEL: Record<string, string> = {
  starting:       "准备中…",
  thinking:       "推理中…",
  tool_use:       "调用工具…",
  retry_opinion:  "重整输出…",
  synthesize_start: "综合中…",
  synthesis:      "执棋综合中…",
  done:           "完成",
};

export function formatStage(stage: string | null, advisor?: string | null): string | null {
  if (!stage) return null;
  const human = STAGE_LABEL[stage] ?? stage;
  if (advisor) {
    const meta = getAdvisorMeta(advisor);
    return `${meta.display} · ${human}`;
  }
  return human;
}
