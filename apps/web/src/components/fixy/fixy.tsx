import type { CSSProperties } from "react";

export type Mood = "wave" | "idle" | "thinking" | "worried" | "cheer";

/** Arm angles in degrees (CSS: positive = clockwise). Matches the Figma "Robot · Fixy" set. */
const ARMS: Record<Mood, { left: number; right: number; wave?: [number, number] }> = {
  wave: { left: 18, right: -150, wave: [-150, -118] },
  idle: { left: 18, right: -18 },
  thinking: { left: 18, right: -128 },
  worried: { left: 8, right: -8 },
  cheer: { left: 158, right: -158 },
};

const TEAL = "#5EEAD4";
const RED = "#F87171";

function Face({ mood }: { mood: Mood }) {
  const stroke = { strokeWidth: 3.5, strokeLinecap: "round" as const, fill: "none" };
  switch (mood) {
    case "wave":
    case "cheer":
      return (
        <g>
          <path d="M56 67 q8 -11 16 0" stroke={TEAL} strokeWidth={5} strokeLinecap="round" fill="none" />
          <path d="M88 67 q8 -11 16 0" stroke={TEAL} strokeWidth={5} strokeLinecap="round" fill="none" />
          {mood === "cheer" ? (
            <path d="M69 75 q11 13 22 0 z" fill={TEAL} />
          ) : (
            <path d="M72 78 q8 7 16 0" stroke={TEAL} {...stroke} />
          )}
        </g>
      );
    case "thinking":
      return (
        <g>
          <g className="fixy-eyes">
            <ellipse cx="69" cy="58" rx="6" ry="8" fill={TEAL} />
            <ellipse cx="101" cy="58" rx="6" ry="8" fill={TEAL} />
          </g>
          <path d="M76 80 h10" stroke={TEAL} {...stroke} />
        </g>
      );
    case "worried":
      return (
        <g>
          <path d="M55 51 l14 5" stroke={RED} {...stroke} />
          <path d="M105 51 l-14 5" stroke={RED} {...stroke} />
          <ellipse cx="64" cy="66" rx="6" ry="7" fill={RED} />
          <ellipse cx="96" cy="66" rx="6" ry="7" fill={RED} />
          <path d="M72 84 q8 -7 16 0" stroke={RED} {...stroke} />
        </g>
      );
    default:
      return (
        <g>
          <g className="fixy-eyes">
            <ellipse cx="64" cy="63" rx="7" ry="9" fill={TEAL} />
            <ellipse cx="96" cy="63" rx="7" ry="9" fill={TEAL} />
            <circle cx="66.5" cy="59.5" r="2.4" fill="#fff" />
            <circle cx="98.5" cy="59.5" r="2.4" fill="#fff" />
          </g>
          <path d="M72 79 q8 6 16 0" stroke={TEAL} {...stroke} />
        </g>
      );
  }
}

function Arm({ side, angle, wave }: { side: "left" | "right"; angle: number; wave?: [number, number] }) {
  const x = side === "left" ? 50 : 110;
  const style = {
    transformOrigin: `${x}px 120px`,
    transform: `rotate(${angle}deg)`,
    ...(wave ? { "--wave-a": `${wave[0]}deg`, "--wave-b": `${wave[1]}deg` } : {}),
  } as CSSProperties;
  return (
    <g className={`fixy-arm${wave ? " is-waving" : ""}`} style={style}>
      <rect x={x - 8} y={117} width={16} height={38} rx={8} fill="#fff" stroke="#E2E8F0" strokeWidth={2} />
      <circle cx={x} cy={157} r={9} fill="#2DD4BF" />
    </g>
  );
}

export function Fixy({
  mood = "idle",
  size = 160,
  className,
  label = "Fixy, your repair buddy",
}: {
  mood?: Mood;
  size?: number;
  className?: string;
  label?: string;
}) {
  const arms = ARMS[mood];
  const raised = (a: number) => Math.abs(a) >= 60;
  const left = <Arm side="left" angle={arms.left} />;
  const right = <Arm side="right" angle={arms.right} wave={arms.wave} />;
  const cheeks = mood !== "worried" && mood !== "thinking";

  return (
    <svg
      viewBox="0 0 160 180"
      width={size}
      height={(size * 180) / 160}
      className={className}
      role="img"
      aria-label={label}
      overflow="visible"
    >
      <ellipse cx="80" cy="173" rx="42" ry="6" fill="#0F172A" fillOpacity={0.08} />
      <g className="fixy-body">
        {!raised(arms.left) && left}
        {!raised(arms.right) && right}
        <path d="M80 24 V10" stroke="#94A3B8" strokeWidth={4} strokeLinecap="round" />
        <circle className="fixy-antenna" cx="80" cy="9" r="7" fill="#FBBF24" />
        <rect x="70" y="100" width="20" height="12" rx="4" fill="#CBD5E1" />
        <rect x="48" y="108" width="64" height="54" rx="24" fill="#fff" stroke="#E2E8F0" strokeWidth={2} />
        <circle cx="80" cy="132" r="9" fill="#2DD4BF" />
        <circle cx="80" cy="132" r="4" fill="#fff" fillOpacity={0.7} />
        <circle cx="22" cy="64" r="9" fill="#2DD4BF" />
        <circle cx="138" cy="64" r="9" fill="#2DD4BF" />
        <rect x="24" y="22" width="112" height="84" rx="38" fill="#fff" stroke="#E2E8F0" strokeWidth={2} />
        <rect x="38" y="37" width="84" height="56" rx="26" fill="#0F172A" />
        {cheeks && (
          <g>
            <circle cx="51" cy="79" r="5" fill="#FDA4AF" fillOpacity={0.85} />
            <circle cx="109" cy="79" r="5" fill="#FDA4AF" fillOpacity={0.85} />
          </g>
        )}
        <Face mood={mood} />
        {raised(arms.left) && left}
        {raised(arms.right) && right}
      </g>
    </svg>
  );
}
