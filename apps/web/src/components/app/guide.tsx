"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import { Fixy } from "@/components/fixy/fixy";
import { Icon } from "@/components/ui/icons";
import { Badge, Chip, FixySays, PrimaryButton, TopBar } from "@/components/ui/parts";
import { type Procedure, type SourceRef, type StepResponse, getProcedure, mapsSearch, stepHelp } from "@/lib/api";
import { listen, preparePhoto, speechSupported } from "@/lib/media";
import { speak, stopSpeaking, voiceCommand } from "@/lib/voice";
import { StepVisual } from "./step-visual";
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

function BuyPart({ spec, lang }: { spec: NonNullable<Procedure["part_spec"]>; lang: Lang }) {
  const q = encodeURIComponent(spec.kind);
  const stores = [
    { name: "Amazon", href: `https://www.amazon.in/s?k=${q}` },
    { name: "Flipkart", href: `https://www.flipkart.com/search?q=${q}` },
  ];
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted">{t("buyPart", lang)}</p>
      <p className="text-[15px]">
        <span className="font-semibold">{spec.kind}</span> · {spec.match}
      </p>
      <div className="flex gap-2">
        {stores.map((s) => (
          <a
            key={s.name}
            href={s.href}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-11 items-center rounded-full border border-line bg-surface px-4 text-sm font-medium"
          >
            {s.name} ↗
          </a>
        ))}
      </div>
      <p className="text-xs text-muted">{t("buyNote", lang)}</p>
    </div>
  );
}

export function Guide({
  lang,
  item,
  procedureId,
  onBack,
  onDone,
  onStop,
  voice,
  onVoice,
}: {
  lang: Lang;
  item: string;
  procedureId: string;
  onBack: () => void;
  onDone: (resolved: boolean | null) => void;
  onStop: (stop: NonNullable<StepResponse["stop"]>) => void;
  voice: boolean;
  onVoice: (on: boolean) => void;
}) {
  const [proc, setProc] = useState<Procedure | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [page, setPage] = useState(-1); // -1 = overview, 0..n-1 = steps, n = check
  const [stuck, setStuck] = useState(false);
  const [help, setHelp] = useState<{ from: "user" | "fixy"; text: string }[]>([]);
  const [helpText, setHelpText] = useState("");
  const [helpBusy, setHelpBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const stopListen = useRef<(() => void) | null>(null);
  const photoRef = useRef<HTMLInputElement>(null);
  const n = proc?.steps.length ?? 0;

  function stepLine(i: number): string {
    const s = proc?.steps[i];
    return s ? [s.text, s.caution].filter(Boolean).join(". ") : "";
  }

  function go(to: number) {
    stopSpeaking();
    stopListen.current?.();
    setStuck(false);
    setHelp([]);
    setPage(to);
  }

  async function ask(question: string, image?: string) {
    if (!proc || helpBusy) return;
    setStuck(true);
    setHelpBusy(true);
    setHelp((h) => [...h, { from: "user", text: question || t("photo", lang) }]);
    try {
      const r = await stepHelp({ item, procedure_id: procedureId, step: Math.max(page, 0), question, image, lang });
      if (r.state === "stop" && r.stop) {
        stopSpeaking();
        onStop(r.stop);
        return;
      }
      setHelp((h) => [...h, { from: "fixy", text: r.say }]);
      if (voice) void speak(r.say, lang).then(() => startListening());
    } catch {
      setHelp((h) => [...h, { from: "fixy", text: t("offline", lang) }]);
    } finally {
      setHelpBusy(false);
    }
  }

  function heard(text: string) {
    const cmd = voiceCommand(text);
    if (page >= n && (cmd === "yes" || cmd === "no")) return onDone(cmd === "yes");
    if (cmd === "next") return go(Math.min(page + 1, n));
    if (cmd === "back") return go(Math.max(page - 1, -1));
    if (cmd === "repeat") return void speak(page < 0 ? (proc?.title ?? "") : stepLine(page), lang).then(() => startListening());
    void ask(text);
  }

  function startListening() {
    if (!speechSupported()) return;
    stopListen.current?.();
    setListening(true);
    stopListen.current = listen(lang, heard, () => setListening(false));
  }

  function toggleMic() {
    if (listening) stopListen.current?.();
    else startListening();
  }

  async function sendPhoto(file: File) {
    const photo = await preparePhoto(file).catch(() => null);
    if (photo) void ask(helpText.trim(), photo.base64);
    setHelpText("");
  }

  function submitHelp(e: FormEvent) {
    e.preventDefault();
    const q = helpText.trim();
    if (!q) return;
    setHelpText("");
    void ask(q);
  }

  // Voice mode: read each step aloud, then listen for "next", "repeat" or a question.
  useEffect(() => {
    if (!voice || !proc) return;
    const line = page < 0 ? proc.title : page < n ? stepLine(page) : t("didItWork", lang);
    void speak(line, lang).then(() => startListening());
    return () => {
      stopSpeaking();
      stopListen.current?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [voice, page, proc]);

  useEffect(() => {
    let alive = true;
    getProcedure(item, procedureId, lang)
      .then((p) => alive && setProc(p))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [item, procedureId, lang, attempt]);

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
          <a
            href={mapsSearch(t("shopQuery", lang))}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[15px] font-semibold text-brand underline"
          >
            {t("findShop", lang)}
          </a>
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
      <TopBar onBack={page < 0 ? onBack : () => go(page - 1)} backLabel={t("back", lang)}>
        {page >= 0 ? dots : <span className="flex-1" />}
        <button
          type="button"
          onClick={() => onVoice(!voice)}
          aria-pressed={voice}
          aria-label={voice ? t("voiceOn", lang) : t("voiceOff", lang)}
          className={`grid size-11 place-items-center rounded-full ${voice ? "bg-brand-subtle text-brand" : "text-muted"}`}
        >
          <Icon name={voice ? "volume" : "volumeOff"} size={22} />
        </button>
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
          {proc.part_spec && <BuyPart spec={proc.part_spec} lang={lang} />}
          <Sources sources={proc.sources} lang={lang} />
        </div>
      )}

      {page >= 0 && page < n && (
        <div key={page} className="rise-in flex flex-1 flex-col gap-4 overflow-y-auto px-6 pt-2">
          <StepVisual text={proc.steps[page].text} n={page + 1} caution={Boolean(proc.steps[page].caution)} />
          <div className="flex items-start gap-2">
            <p className="flex-1 text-[22px] font-semibold leading-snug">{proc.steps[page].text}</p>
            <button
              type="button"
              onClick={() => void speak(stepLine(page), lang)}
              aria-label={t("readAloud", lang)}
              className="grid size-11 shrink-0 place-items-center rounded-full border border-line bg-surface text-brand"
            >
              <Icon name="volume" size={20} />
            </button>
          </div>
          {proc.steps[page].caution && (
            <Badge tone="caution">
              <Icon name="alert" size={14} /> {proc.steps[page].caution}
            </Badge>
          )}
          {voice && <p className="text-xs text-muted">{listening ? t("listening", lang) : t("sayNext", lang)}</p>}

          {!stuck ? (
            <button
              type="button"
              onClick={() => setStuck(true)}
              className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-line bg-surface text-[15px] font-semibold"
            >
              <Icon name="help" size={18} /> {t("stuck", lang)}
            </button>
          ) : (
            <div className="space-y-3 rounded-2xl border border-line bg-surface p-3">
              <p className="text-sm font-semibold">{t("askStep", lang)}</p>
              {help.length === 0 && <p className="text-xs text-muted">{t("stuckHint", lang)}</p>}
              {help.map((m, i) => (
                <p
                  key={i}
                  className={`rounded-2xl px-3 py-2 text-[15px] ${m.from === "user" ? "ml-8 bg-brand text-on-brand" : "mr-8 bg-subtle"}`}
                >
                  {m.text}
                </p>
              ))}
              {helpBusy && <p className="text-xs text-muted">{t("thinking", lang)}…</p>}
              <form onSubmit={submitHelp} className="flex items-center gap-2">
                <input
                  value={helpText}
                  onChange={(e) => setHelpText(e.target.value)}
                  maxLength={500}
                  placeholder={t("message", lang)}
                  aria-label={t("askStep", lang)}
                  className="min-h-11 min-w-0 flex-1 rounded-full border border-line px-4 text-[15px] outline-none focus:border-brand"
                />
                <button type="button" onClick={toggleMic} aria-label={t("speak", lang)} aria-pressed={listening}
                  className={`grid size-11 shrink-0 place-items-center rounded-full border ${listening ? "animate-pulse border-brand text-brand" : "border-line"}`}>
                  <Icon name="mic" size={18} />
                </button>
                <button type="button" onClick={() => photoRef.current?.click()} aria-label={t("sendPhoto", lang)}
                  className="grid size-11 shrink-0 place-items-center rounded-full border border-line">
                  <Icon name="camera" size={18} />
                </button>
                <button type="submit" disabled={!helpText.trim() || helpBusy} aria-label={t("send", lang)}
                  className="grid size-11 shrink-0 place-items-center rounded-full bg-brand text-on-brand disabled:opacity-40">
                  <Icon name="send" size={18} />
                </button>
              </form>
              <input ref={photoRef} type="file" accept="image/*" capture="environment" className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  e.target.value = "";
                  if (file) void sendPhoto(file);
                }}
              />
            </div>
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
          <PrimaryButton className="flex-1" onClick={() => go(page + 1)}>
            {page < 0 ? t("start", lang) : t("next", lang)}
          </PrimaryButton>
        </div>
      )}
    </div>
  );
}
