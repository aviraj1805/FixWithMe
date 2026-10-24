import type { ReactNode } from "react";
import { Fixy, type Mood } from "@/components/fixy/fixy";
import { Icon } from "@/components/ui/icons";

export type Tone = "verified" | "curated" | "likely" | "ai" | "caution" | "stop";

const TONES: Record<Tone, string> = {
  verified: "bg-[var(--color-status-verified-bg)] text-[var(--color-status-verified-fg)]",
  curated: "bg-brand-subtle text-brand",
  likely: "bg-[var(--color-status-likely-bg)] text-[var(--color-status-likely-fg)]",
  ai: "bg-[var(--color-status-ai-bg)] text-[var(--color-status-ai-fg)]",
  caution: "bg-[var(--color-status-caution-bg)] text-[var(--color-status-caution-fg)]",
  stop: "bg-[var(--color-status-stop-bg)] text-[var(--color-status-stop-fg)]",
};

export function Badge({ tone, children, title }: { tone: Tone; children: ReactNode; title?: string }) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

export function Bubble({ children, tail = "none" }: { children: ReactNode; tail?: "left" | "none" }) {
  return (
    <div
      className={`rise-in rounded-[22px] bg-surface px-5 py-3 shadow-soft ${tail === "left" ? "rounded-bl-md" : ""}`}
    >
      {children}
    </div>
  );
}

export function FixySays({ mood = "idle", children }: { mood?: Mood; children: ReactNode }) {
  return (
    <div className="flex items-end gap-2">
      <Fixy mood={mood} size={40} className="shrink-0" label="Fixy" />
      <div className="max-w-[80%]">
        <Bubble tail="left">{children}</Bubble>
      </div>
    </div>
  );
}

export function Chip({
  children,
  onClick,
  selected,
  disabled,
}: {
  children: ReactNode;
  onClick?: () => void;
  selected?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`min-h-11 rounded-full border px-4 text-sm font-medium transition-colors disabled:opacity-50 ${
        selected
          ? "border-brand bg-brand-subtle text-brand"
          : "border-line bg-surface text-ink hover:border-brand"
      }`}
    >
      {children}
    </button>
  );
}

export function PrimaryButton({
  children,
  onClick,
  className = "",
  tone = "brand",
}: {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
  tone?: "brand" | "light";
}) {
  const look =
    tone === "light"
      ? "bg-surface text-ink border border-line"
      : "bg-brand text-on-brand hover:bg-brand-pressed";
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-13 rounded-xl px-6 text-[15px] font-semibold transition-colors ${look} ${className}`}
    >
      {children}
    </button>
  );
}

export function TopBar({ onBack, backLabel, children }: { onBack: () => void; backLabel: string; children?: ReactNode }) {
  return (
    <header className="flex min-h-14 items-center gap-2 px-2">
      <button
        type="button"
        onClick={onBack}
        aria-label={backLabel}
        className="grid size-11 place-items-center rounded-full text-[var(--color-icon-default)] hover:bg-subtle"
      >
        <Icon name="back" />
      </button>
      {children}
    </header>
  );
}
