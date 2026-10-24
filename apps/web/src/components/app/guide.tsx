"use client";

import { useEffect, useState } from "react";
import { Fixy } from "@/components/fixy/fixy";
import { Icon } from "@/components/ui/icons";
import { Badge, Chip, FixySays, PrimaryButton, TopBar } from "@/components/ui/parts";
import { type Procedure, type SourceRef, getProcedure } from "@/lib/api";
import { type Lang, t } from "@/lib/i18n";

function Sources({ sources, lang }: { sources: SourceRef[]; lang: Lang }) {
  if (!sources.length) return null;
  return (
    <details className="text-xs text-muted">
      <summary className="cursor-pointer select-none py-1">{t("sources", lang)} ({sources.length})</summary>
      <ul className="mt-1 space-y-1">
        {sources.map((s) => (
          <li key={s.url}>
            <a href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 underline">
              {s.title}
              <Icon name="link" size={12} />
            </a>
          </li>
        ))}
      </ul>
    </details>
  );
}

function TierBadge({ tier, lang }: { tier: Procedure["tier"]; lang: Lang }) {
  return tier === "verified" ? (
    <Badge tone="verified">
      <Icon name="check" size={14} /> Verified
    </Badge>
  ) : (
    <Badge tone="curated" title={t("curatedHint", lang)}>
      <Icon name="shield" size={14} /> {t("curated", lang)}
    </Badge>
  );
}

export function Guide({
  lang,
  procedureId,
  onBack,
  onDone,
}: {
  lang: Lang;
  procedureId: string;
  onBack: () => void;
  onDone: (resolved: boolean | null) => void;
}) {
  const [proc, setProc] = useState<Procedure | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [page, setPage] = useState(-1); // -1 = overview, 0..n-1 = steps, n = check

  useEffect(() => {
    let alive = true;
    getProcedure(procedureId, lang)
      .then((p) => alive && setProc(p))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [procedureId, lang, attempt]);

  if (!proc) {
    return (
      <div className="flex flex-1 flex-col">
        <TopBar onBack={onBack} backLabel={t("back", lang)} />
        <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6">
          <Fixy mood={failed ? "worried" : "thinking"} size={120} />
          {failed && (
            <>
              <p className="text-center text-muted">{t("offline", lang)}</p>
              <Chip onClick={() => { setFailed(false); setAttempt((a) => a + 1); }}>{t("retry", lang)}</Chip>
            </>
          )}
        </div>
      </div>
    );
  }

  // Professional-only (safety level 3): no DIY steps, just who to call and why.
  if (proc.safety_level >= 3) {
    return (
      <div className="flex flex-1 flex-col">
        <TopBar onBack={onBack} backLabel={t("back", lang)} />
        <div className="flex flex-1 flex-col gap-5 px-6 pt-4">
          <Fixy mood="worried" size={120} className="self-center" />
          <h1 className="text-2xl font-semibold">{proc.title}</h1>
          <p className="text-[17px] text-muted">{proc.reason}</p>
          <div className="flex flex-wrap gap-2">
            <Badge tone="caution">
              <Icon name="wrench" size={14} /> {proc.professional}
            </Badge>
            <TierBadge tier={proc.tier} lang={lang} />
          </div>
          <Sources sources={proc.sources} lang={lang} />
        </div>
        <div className="p-4">
          <PrimaryButton className="w-full" onClick={() => onDone(null)}>
            {t("fixAnother", lang)}
          </PrimaryButton>
        </div>
      </div>
    );
  }

  const n = proc.steps.length;
  const dots = (
    <div className="flex flex-1 justify-center gap-1.5" aria-hidden="true">
      {proc.steps.map((_, i) => (
        <span
          key={i}
          className={`h-2 rounded-full transition-all ${i === page ? "w-6 bg-brand" : i < page || page >= n ? "w-2 bg-brand" : "w-2 bg-line-strong"}`}
        />
      ))}
    </div>
  );

  return (
    <div className="flex flex-1 flex-col">
      <TopBar onBack={page < 0 ? onBack : () => setPage((p) => p - 1)} backLabel={t("back", lang)}>
        {page >= 0 && dots}
        {page >= 0 && <span className="w-11" />}
      </TopBar>

      {page < 0 && (
        <div className="flex flex-1 flex-col gap-5 overflow-y-auto px-6 pt-2">
          <h1 className="text-[28px] font-bold leading-tight">{proc.title}</h1>
          <div className="flex flex-wrap gap-2">
            <TierBadge tier={proc.tier} lang={lang} />
            {proc.minutes && <Badge tone="ai">≈ {proc.minutes} {t("min", lang)}</Badge>}
            {proc.difficulty && <Badge tone="ai">{proc.difficulty}</Badge>}
            {proc.cost_inr && (
              <Badge tone="ai">
                {proc.cost_inr.max === 0
                  ? t("free", lang)
                  : `₹${proc.cost_inr.min}–${proc.cost_inr.max} (${t("estimate", lang)})`}
              </Badge>
            )}
          </div>
          {proc.safety_level >= 2 && (
            <Badge tone="caution">
              <Icon name="power" size={14} /> {t("powerOffFirst", lang)}
            </Badge>
          )}
          {proc.tools.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">{t("youNeed", lang)}</p>
              <ul className="flex flex-wrap gap-2">
                {proc.tools.map((tool) => (
                  <li key={tool} className="rounded-full border border-line bg-surface px-3 py-1.5 text-sm">
                    {tool}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <Sources sources={proc.sources} lang={lang} />
        </div>
      )}

      {page >= 0 && page < n && (
        <div key={page} className="rise-in flex flex-1 flex-col gap-5 overflow-y-auto px-6 pt-2">
          <div className="grid aspect-[4/3] place-items-center rounded-3xl bg-brand-subtle">
            <span className="text-7xl font-bold text-brand" aria-hidden="true">
              {page + 1}
            </span>
          </div>
          <p className="text-[22px] font-semibold leading-snug">{proc.steps[page].text}</p>
          {proc.steps[page].caution && (
            <Badge tone="caution">
              <Icon name="alert" size={14} /> {proc.steps[page].caution}
            </Badge>
          )}
          <Sources sources={proc.steps[page].sources} lang={lang} />
        </div>
      )}

      {page >= n && (
        <div className="flex flex-1 flex-col justify-center gap-5 px-6">
          <FixySays mood="idle">
            <p className="text-[17px] font-semibold">{t("didItWork", lang)}</p>
            {proc.verify && <p className="mt-1 text-sm text-muted">{proc.verify}</p>}
          </FixySays>
          <div className="flex justify-end gap-2">
            <Chip onClick={() => onDone(true)}>{t("yes", lang)}</Chip>
            <Chip onClick={() => onDone(false)}>{t("no", lang)}</Chip>
          </div>
        </div>
      )}

      {page < n && (
        <div className="flex items-center gap-3 p-4">
          <Fixy mood="idle" size={44} label="Fixy" />
          <PrimaryButton className="flex-1" onClick={() => setPage((p) => p + 1)}>
            {page < 0 ? t("start", lang) : t("next", lang)}
          </PrimaryButton>
        </div>
      )}
    </div>
  );
}
