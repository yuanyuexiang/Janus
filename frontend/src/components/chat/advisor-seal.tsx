/**
 * 顾问 / 执棋的「姓名印章」头像。
 *
 * 不从外部拉头像 —— 古典调性下卡通头像会破坏整体观感。
 * 改用本地生成的方形印：签名色描边 + 淡色衬底 + 宋体名字首字，
 * 呼应首页"桌"字金印的视觉语言。
 */

type SealSize = "sm" | "md" | "lg";

const SIZE_MAP: Record<SealSize, { box: string; text: string }> = {
  sm: { box: "h-8 w-8", text: "text-base" },
  md: { box: "h-10 w-10", text: "text-xl" },
  lg: { box: "h-12 w-12", text: "text-2xl" },
};

export type AdvisorSealProps = {
  /** 名字首字（韬/岚/明/锐/冷/零/执），取 display 第一个字符即可 */
  char: string;
  /** 顾问签名色（执棋传 gilt） */
  color: string;
  size?: SealSize;
  /** 执棋用：金箔双线印 + 鎏金调，区别于六位顾问 */
  conductor?: boolean;
};

export function AdvisorSeal({
  char,
  color,
  size = "md",
  conductor = false,
}: AdvisorSealProps) {
  const s = SIZE_MAP[size];

  if (conductor) {
    // 执棋：金箔双线方印，更"主位"
    return (
      <span
        className={`relative inline-flex ${s.box} shrink-0 items-center justify-center rounded-sm`}
        style={{ backgroundColor: "color-mix(in srgb, var(--color-gilt-500) 14%, transparent)" }}
      >
        <span className="absolute inset-0 rounded-sm border border-gilt-500/60" />
        <span className="absolute inset-[3px] rounded-[2px] border border-gilt-500/30" />
        <span className={`font-display ${s.text} font-medium leading-none text-gilt-700 dark:text-gilt-200`}>
          {char}
        </span>
      </span>
    );
  }

  // 顾问：单线方印，衬底 + 描边 + 文字都用签名色
  return (
    <span
      className={`relative inline-flex ${s.box} shrink-0 items-center justify-center rounded-sm`}
      style={{
        backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)`,
        boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${color} 55%, transparent)`,
      }}
    >
      <span
        className={`font-display ${s.text} font-medium leading-none`}
        style={{ color }}
      >
        {char}
      </span>
    </span>
  );
}
