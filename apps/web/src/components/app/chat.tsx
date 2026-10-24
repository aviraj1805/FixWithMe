"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import { Fixy } from "@/components/fixy/fixy";
import { Icon } from "@/components/ui/icons";
import { Badge, Chip, FixySays, PrimaryButton, TopBar } from "@/components/ui/parts";
import { type Answer, type Answers, type AskResponse, type StepResponse, ask, step } from "@/lib/api";
import { type Lang, t } from "@/lib/i18n";
import { listen } from "@/lib/media";

export type Msg =
  | { id: number; from: "user"; text: string }
  | {
      id: number;
      from: "fixy";
      text: string;
      kind: "intro" | "question" | "confirm" | "clarify" | "unsupported" | "diagnosis" | "answer" | "abstain" | "error";
      via?: "ask";
      web?: boolean;
      qid?: string;
      hazard?: string;
      sourceText?: string;
      options?: StepResponse["options"];
      diagnosis?: NonNullable<StepResponse["diagnosis"]>;
      answer?: AskResponse;
    };

export type Session = {
  messages: Msg[];
  answers: Answers;
  item: string | null;
  causes: StepResponse["causes"];
  tier: StepResponse["tier"];
  mode: "diagnose" | "ask"; // after a diagnosis (or "Ask anyway"), typed text becomes a question
  listenNow?: boolean; // opened with "Talk": start the mic once
  photoPending?: boolean; // a photo is being identified
  start?: { text: string; item: string | null }; // first message from a photo, sent once
};

type Body = {
  text?: string;
  answers: Answers;
  item: string | null;
  safety_checked?: boolean;
  confirm_hazard?: string;
};

type AskBody = {
  question: string;
  item: string | null;
  web?: boolean; // "Ask anyway" for an unsupported item: allow a web-grounded suggestion
  safety_checked?: boolean;
  confirm_hazard?: string;
};

let nextId = 1;
export const newId = () => nextId++;

export function Chat({
  lang,
  session,
  setSession,
  onBack,
  onStop,
  onGuide,
  onOpenGuide,
}: {
  lang: Lang;
  session: Session;
  setSession: (update: (s: Session) => Session) => void;
  onBack: () => void;
  onStop: (stop: NonNullable<StepResponse["stop"]>) => void;
  onGuide: (diagnosis: NonNullable<StepResponse["diagnosis"]>) => void;
  onOpenGuide: (item: string, procedureId: string) => void;
}) {
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [slow, setSlow] = useState<string | null>(null);
  const [lastBody, setLastBody] = useState<Body | null>(null);
  const [lastAsk, setLastAsk] = useState<AskBody | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const [listening, setListening] = useState(false);
  const stopRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [session.messages.length, pending]);

  const push = (msg: Msg) => setSession((s) => ({ ...s, messages: [...s.messages, msg] }));

  async function run(body: Body) {
    setPending(true);
    setLastBody(body);
    const slowTimer = setTimeout(() => setSlow(t("wakingUp", lang)), 4000);
    try {
      const r = await step({ ...body, lang });
      setSession((s) => ({
        ...s,
        answers: r.answers,
        item: r.item ?? s.item,
        causes: r.causes.length ? r.causes : s.causes,
        tier: r.tier ?? s.tier,
        mode: r.state === "diagnosis" ? "ask" : s.mode,
      }));
      if (r.state === "stop") {
        if (r.stop) onStop(r.stop);
        return;
      }
      push({
        id: newId(),
        from: "fixy",
        text: r.say,
        kind: r.state,
        qid: r.question?.id,
        hazard: r.confirm?.hazard,
        sourceText: body.text,
        options: r.options,
        diagnosis: r.diagnosis ?? undefined,
      });
    } catch {
      push({ id: newId(), from: "fixy", text: t("offline", lang), kind: "error" });
    } finally {
      clearTimeout(slowTimer);
      setPending(false);
      setSlow(null);
    }
  }

  async function runAsk(body: AskBody) {
    setPending(true);
    setLastAsk(body);
    const slowTimer = setTimeout(() => setSlow(t(body.web ? "searchingWeb" : "wakingUp", lang)), 4000);
    try {
      const r = await ask({ ...body, lang });
      if (r.state === "stop") {
        if (r.stop) onStop(r.stop);
        return;
      }
      push({
        id: newId(),
        from: "fixy",
        text: r.say,
        kind: r.state,
        via: "ask",
        hazard: r.confirm?.hazard,
        sourceText: body.question,
        answer: r.state === "answer" ? r : undefined,
        web: body.web,
      });
    } catch {
      push({ id: newId(), from: "fixy", text: t("offline", lang), kind: "error", via: "ask" });
    } finally {
      clearTimeout(slowTimer);
      setPending(false);
      setSlow(null);
    }
  }

  function sendText(e?: FormEvent, spoken?: string) {
    e?.preventDefault();
    const value = (spoken ?? text).trim();
    if (!value || pending) return;
    setText("");
    push({ id: newId(), from: "user", text: value });
    if (session.mode === "ask") void runAsk({ question: value, item: session.item, web: session.item === null });
    else void run({ text: value, answers: session.answers, item: session.item });
  }

  function toggleMic() {
    if (listening) {
      stopRef.current?.();
      return;
    }
    setListening(true);
    stopRef.current = listen(
      lang,
      (spoken) => sendText(undefined, spoken),
      () => setListening(false),
    );
  }

  // Opened with "Talk": start listening once. From a photo: send its description once.
  useEffect(() => {
    if (session.listenNow) {
      setSession((s) => ({ ...s, listenNow: false }));
      // One-shot: the chat was opened with "Talk", so start the mic once on mount.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      toggleMic();
    }
    if (session.start) {
      const { text: first, item } = session.start;
      setSession((s) => ({ ...s, start: undefined }));
      push({ id: newId(), from: "user", text: first });
      void run({ text: first, answers: {}, item });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.listenNow, session.start]);

  function askAnyway(m: Extract<Msg, { from: "fixy" }>) {
    const question = m.sourceText ?? session.messages.find((x) => x.from === "user")?.text;
    push({ id: newId(), from: "user", text: t("askAnyway", lang) });
    setSession((s) => ({ ...s, mode: "ask", item: null }));
    if (question) void runAsk({ question, item: null, web: true });
  }

  function answer(qid: string, value: Answer, label: string) {
    push({ id: newId(), from: "user", text: label });
    void run({ answers: { ...session.answers, [qid]: value }, item: session.item });
  }

  function confirmSafety(m: Extract<Msg, { from: "fixy" }>, yes: boolean, label: string) {
    push({ id: newId(), from: "user", text: label });
    if (m.via === "ask") {
      const question = m.sourceText ?? "";
      const base = { question, item: session.item, web: m.web };
      void runAsk(yes ? { ...base, confirm_hazard: m.hazard } : { ...base, safety_checked: true });
      return;
    }
    const base = { text: m.sourceText, answers: session.answers, item: session.item };
    void run(yes ? { ...base, confirm_hazard: m.hazard } : { ...base, safety_checked: true });
  }

  function clarify(item: string | null, label: string) {
    push({ id: newId(), from: "user", text: label });
    if (item) void run({ answers: session.answers, item });
    else push({ id: newId(), from: "fixy", text: t("onlyFans", lang), kind: "unsupported" });
  }

  const last = session.messages[session.messages.length - 1];
  const top = session.causes[0];
  const answered = Object.keys(session.answers).length > 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <TopBar onBack={onBack} backLabel={t("back", lang)}>
        <Fixy mood={pending ? "thinking" : "idle"} size={36} label="Fixy" />
        <span className="text-[17px] font-semibold">Fixy</span>
      </TopBar>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4" aria-live="polite">
        {session.messages.map((m) =>
          m.from === "user" ? (
            <div key={m.id} className="rise-in flex justify-end">
              <p className="max-w-[80%] rounded-[20px] rounded-br-md bg-brand px-4 py-3 text-[15px] text-on-brand">
                {m.text}
              </p>
            </div>
          ) : (
            <div key={m.id} className="space-y-3">
              <FixySays mood={m.kind === "diagnosis" ? "cheer" : m.kind === "confirm" ? "worried" : "idle"}>
                {m.answer ? (
                  <AnswerCard lang={lang} answer={m.answer} onOpenGuide={onOpenGuide} />
                ) : (
                  <p className="text-[15px] leading-snug">{m.text}</p>
                )}
                {m.diagnosis && (
                  <div className="mt-3 space-y-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge tone="likely">
                        {t("likely", lang)} · {Math.round(m.diagnosis.confidence * 100)}%
                      </Badge>
                      {session.tier && (
                        <Badge tone={session.tier === "verified" ? "verified" : "curated"} title={t("curatedHint", lang)}>
                          {session.tier === "verified" ? "Verified" : t("curated", lang)}
                        </Badge>
                      )}
                    </div>
                    <PrimaryButton className="w-full" onClick={() => onGuide(m.diagnosis!)}>
                      {m.diagnosis.professional ? t("whoToCall", lang) : t("showMeHow", lang)}
                    </PrimaryButton>
                  </div>
                )}
              </FixySays>
              {m === last && !pending && (
                <div className="flex flex-wrap justify-end gap-2 pl-12">
                  {m.kind === "question" && m.qid && (
                    <>
                      <Chip onClick={() => answer(m.qid!, "yes", t("yes", lang))}>{t("yes", lang)}</Chip>
                      <Chip onClick={() => answer(m.qid!, "no", t("no", lang))}>{t("no", lang)}</Chip>
                      <Chip onClick={() => answer(m.qid!, "unknown", t("notSure", lang))}>{t("notSure", lang)}</Chip>
                    </>
                  )}
                  {m.kind === "confirm" && m.hazard && (
                    <>
                      <Chip onClick={() => confirmSafety(m, true, t("yes", lang))}>{t("yes", lang)}</Chip>
                      <Chip onClick={() => confirmSafety(m, false, t("no", lang))}>{t("no", lang)}</Chip>
                    </>
                  )}
                  {m.kind === "clarify" && (
                    <>
                      {m.options?.map((o) => (
                        <Chip key={o.id} onClick={() => clarify(o.id, o.name)}>
                          {o.name}
                        </Chip>
                      ))}
                      <Chip onClick={() => clarify(null, t("noneOfThese", lang))}>{t("noneOfThese", lang)}</Chip>
                    </>
                  )}
                  {m.kind === "error" && m.via !== "ask" && lastBody && (
                    <Chip onClick={() => void run(lastBody)}>{t("retry", lang)}</Chip>
                  )}
                  {m.kind === "error" && m.via === "ask" && lastAsk && (
                    <Chip onClick={() => void runAsk(lastAsk)}>{t("retry", lang)}</Chip>
                  )}
                  {m.kind === "unsupported" && (
                    <>
                      <Chip onClick={() => askAnyway(m)}>{t("askAnyway", lang)}</Chip>
                      <Chip onClick={onBack}>{t("startOver", lang)}</Chip>
                    </>
                  )}
                </div>
              )}
            </div>
          ),
        )}
        {session.photoPending && (
          <div className="flex items-end gap-2" role="status">
            <Fixy mood="thinking" size={40} label="Fixy" />
            <div className="rounded-[20px] rounded-bl-md bg-surface px-4 py-3 shadow-soft">
              <p className="text-[15px]">{t("looking", lang)}</p>
              <p className="mt-1 text-xs text-muted">{t("photoNote", lang)}</p>
            </div>
          </div>
        )}
        {pending && (
          <div className="flex items-end gap-2" role="status" aria-label={t("thinking", lang)}>
            <Fixy mood="thinking" size={40} label="Fixy" />
            <div className="rounded-[20px] rounded-bl-md bg-surface px-4 py-3 shadow-soft">
              <span className="flex gap-1" aria-hidden="true">
                {[0, 1, 2].map((i) => (
                  <span key={i} className="typing-dot size-2 rounded-full bg-muted" style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </span>
              {slow && <p className="mt-2 text-xs text-muted">{slow}</p>}
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {top && answered && (
        <div className="flex justify-center pb-2">
          <Badge tone="likely">
            {t("likely", lang)}: {top.short} · {Math.round(top.p * 100)}%
          </Badge>
        </div>
      )}

      <form onSubmit={sendText} className="flex items-center gap-2 px-4 pb-6 pt-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={1000}
          placeholder={
            listening
              ? t("listening", lang)
              : session.messages.length <= 1
              ? t("placeholder", lang)
              : session.mode === "ask"
                ? t("askFollowUp", lang)
                : t("message", lang)
          }
          aria-label={t("message", lang)}
          className="min-h-12 min-w-0 flex-1 rounded-full border border-line bg-surface px-5 text-[15px] outline-none focus:border-brand"
        />
        <button
          type="button"
          onClick={toggleMic}
          aria-label={listening ? t("listening", lang) : t("speak", lang)}
          aria-pressed={listening}
          className={`grid size-12 shrink-0 place-items-center rounded-full border ${
            listening ? "animate-pulse border-brand bg-brand-subtle text-brand" : "border-line bg-surface"
          }`}
        >
          <Icon name="mic" size={20} />
        </button>
        <button
          type="submit"
          disabled={pending || !text.trim()}
          aria-label={t("send", lang)}
          className="grid size-12 shrink-0 place-items-center rounded-full bg-brand text-on-brand disabled:opacity-40"
        >
          <Icon name="send" size={20} />
        </button>
      </form>
    </div>
  );
}

function AnswerCard({
  lang,
  answer,
  onOpenGuide,
}: {
  lang: Lang;
  answer: AskResponse;
  onOpenGuide: (item: string, procedureId: string) => void;
}) {
  const index = new Map(answer.sources.map((src, i) => [src.id, i + 1]));
  return (
    <div className="space-y-3">
      <ul className="space-y-2">
        {answer.claims.map((c) => (
          <li key={c.text} className="text-[15px] leading-snug">
            {c.text}
            {[...c.sources].sort((a, b) => (index.get(a) ?? 0) - (index.get(b) ?? 0)).map((id) => (
              <sup key={id} className="ml-0.5 text-xs font-semibold text-brand">
                [{index.get(id)}]
              </sup>
            ))}
          </li>
        ))}
      </ul>
      {answer.caution && (
        <p className="flex gap-2 rounded-xl bg-[var(--color-status-caution-bg)] px-3 py-2 text-sm text-[var(--color-status-caution-fg)]">
          <Icon name="shield" size={16} /> {answer.caution}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        {answer.tier === "curated" ? (
          <Badge tone="curated" title={t("curatedHint", lang)}>
            {t("curated", lang)}
          </Badge>
        ) : answer.tier === "web" ? (
          <Badge tone="ai">{t("aiSuggestion", lang)}</Badge>
        ) : (
          <Badge tone="ai">{t("fromSources", lang)}</Badge>
        )}
        {answer.tier === "web" ? (
          <Badge tone="caution">{t("unverified", lang)}</Badge>
        ) : answer.verified ? (
          <Badge tone="verified" title={t("checkedHint", lang)}>
            {t("checked", lang)}
          </Badge>
        ) : (
          <Badge tone="caution" title={t("notCheckedHint", lang)}>
            {t("notChecked", lang)}
          </Badge>
        )}
      </div>
      <ol className="space-y-1 text-xs text-muted">
        {answer.sources.map((src, i) => (
          <li key={src.id}>
            [{i + 1}]{" "}
            {src.url ? (
              <a href={src.url} target="_blank" rel="noopener noreferrer" className="underline">
                {src.title}
              </a>
            ) : (
              src.title
            )}
            {src.source_type === "wikipedia" && ` · ${src.license}`}
          </li>
        ))}
      </ol>
      {answer.search_html && (
        // Google's grounding terms require showing its search suggestions as returned; a sandboxed
        // frame keeps that HTML away from the app while its links still open in a new tab.
        <iframe
          title="Google Search suggestions"
          srcDoc={answer.search_html}
          sandbox="allow-popups allow-popups-to-escape-sandbox"
          className="h-16 w-full rounded-xl border-0"
        />
      )}
      {answer.guides.map((g) => (
        <PrimaryButton
          key={`${g.item}:${g.procedure_id}`}
          className="w-full"
          onClick={() => onOpenGuide(g.item, g.procedure_id)}
        >
          {t("openGuide", lang)}
        </PrimaryButton>
      ))}
    </div>
  );
}
