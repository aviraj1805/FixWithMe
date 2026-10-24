"use client";

import { Fixy } from "@/components/fixy/fixy";
import { Icon, type IconName } from "@/components/ui/icons";
import { Badge, PrimaryButton } from "@/components/ui/parts";
import type { Cause, StepResponse } from "@/lib/api";
import { type Lang, t } from "@/lib/i18n";

const ACTION_ICONS: Record<string, IconName[]> = {
  button_cell: ["phone", "alert", "shield"],
  gas: ["x", "shield", "phone"],
};
const DEFAULT_ICONS: IconName[] = ["power", "x", "phone"];

export function Stop({
  lang,
  stop,
  onBack,
}: {
  lang: Lang;
  stop: NonNullable<StepResponse["stop"]>;
  onBack: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center gap-6 bg-stop px-6 pb-8 pt-10 text-white" role="alert">
      <Fixy mood="worried" size={150} />
      <h1 className="text-center text-[32px] font-bold leading-tight">{stop.title}</h1>
      <ul className="w-full space-y-3 rounded-3xl bg-surface p-5 text-ink">
        {stop.actions.map((a, i) => (
          <li key={a} className="flex items-center gap-3">
            <span className="grid size-9 shrink-0 place-items-center rounded-full bg-[var(--color-status-stop-bg)] text-[var(--color-status-stop-fg)]">
              <Icon name={(ACTION_ICONS[stop.hazard] ?? DEFAULT_ICONS)[i] ?? "alert"} size={18} />
            </span>
            <span className="text-[15px] font-semibold">{a}</span>
          </li>
        ))}
      </ul>
      <div className="mt-auto flex w-full flex-col items-center gap-3">
        <a
          href={`tel:${stop.call}`}
          className="flex min-h-13 w-full items-center justify-center gap-2 rounded-xl bg-white text-[15px] font-semibold text-[#B91C1C]"
        >
          <Icon name="phone" size={18} /> {t("call112", lang)}
        </a>
        <button type="button" onClick={onBack} className="min-h-11 px-4 text-sm font-medium underline">
          {t("goBack", lang)}
        </button>
      </div>
    </div>
  );
}

export function Done({
  lang,
  resolved,
  tip,
  nextCause,
  onRestart,
}: {
  lang: Lang;
  resolved: boolean;
  tip: string | null;
  nextCause: Cause | null;
  onRestart: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 px-6 text-center">
      <Fixy mood={resolved ? "cheer" : "worried"} size={170} />
      <h1 className="text-[28px] font-bold">{resolved ? t("yay", lang) : t("sorry", lang)}</h1>
      {resolved && tip && (
        <p className="max-w-xs text-muted">
          <span className="font-semibold text-ink">{t("tip", lang)}: </span>
          {tip}
        </p>
      )}
      {!resolved && (
        <div className="space-y-2 text-muted">
          {nextCause && (
            <p>
              {t("tryNext", lang)} <Badge tone="likely">{nextCause.short}</Badge>
            </p>
          )}
          <p>{t("askPro", lang)}</p>
        </div>
      )}
      <PrimaryButton className="w-full max-w-xs" onClick={onRestart}>
        {t("fixAnother", lang)}
      </PrimaryButton>
    </div>
  );
}
