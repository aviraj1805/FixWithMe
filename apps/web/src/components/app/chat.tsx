"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import { Fixy } from "@/components/fixy/fixy";
import { Icon } from "@/components/ui/icons";
import { Badge, Chip, FixySays, PrimaryButton, TopBar } from "@/components/ui/parts";
import { type Answer, type Answers, type StepResponse, step } from "@/lib/api";
import { type Lang, t } from "@/lib/i18n";

export type Msg =
  | { id: number; from: "user"; text: string }
  | {
      id: number;
      from: "fixy";
      text: string;
      kind: "intro" | "question" | "clarify" | "unsupported" | "diagnosis" | "error";
      qid?: string;
      options?: StepResponse["options"];
      diagnosis?: NonNullable<StepResponse["diagnosis"]>;
    };

export type Session = {
  messages: Msg[];
  answers: Answers;
  item: string | null;
  causes: StepResponse["causes"];
  tier: StepResponse["tier"];
};

type Body = { text?: string; answers: Answers; item: string | null };

let nextId = 1;
export const newId = () => nextId++;

export function Chat({
  lang,
  session,
  setSession,
  onBack,
  onStop,
  onGuide,
}: {
  lang: Lang;
  session: Session;
  setSession: (update: (s: Session) => Session) => void;
  onBack: () => void;
  onStop: (stop: NonNullable<StepResponse["stop"]>) => void;
  onGuide: (diagnosis: NonNullable<StepResponse["diagnosis"]>) => void;
}) {
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [slow, setSlow] = useState(false);
  const [lastBody, setLastBody] = useState<Body | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [session.messages.length, pending]);

  const push = (msg: Msg) => setSession((s) => ({ ...s, messages: [...s.messages, msg] }));

  async function run(body: Body) {
    setPending(true);
    setLastBody(body);
    const slowTimer = setTimeout(() => setSlow(true), 4000);
    try {
      const r = await step({ ...body, lang });
      setSession((s) => ({
        ...s,
        answers: r.answers,
        item: r.item ?? s.item,
        causes: r.causes.length ? r.causes : s.causes,
        tier: r.tier ?? s.tier,
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
        options: r.options,
        diagnosis: r.diagnosis ?? undefined,
      });
    } catch {
      push({ id: newId(), from: "fixy", text: t("offline", lang), kind: "error" });
    } finally {
      clearTimeout(slowTimer);
      setPending(false);
      setSlow(false);
    }
  }

  function sendText(e: FormEvent) {
    e.preventDefault();
    const value = text.trim();
    if (!value || pending) return;
    setText("");
    push({ id: newId(), from: "user", text: value });
    void run({ text: value, answers: session.answers, item: session.item });
  }

  function answer(qid: string, value: Answer, label: string) {
    push({ id: newId(), from: "user", text: label });
    void run({ answers: { ...session.answers, [qid]: value }, item: session.item });
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
              <FixySays mood={m.kind === "diagnosis" ? "cheer" : "idle"}>
                <p className="text-[15px] leading-snug">{m.text}</p>
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
                  {m.kind === "error" && lastBody && (
                    <Chip onClick={() => void run(lastBody)}>{t("retry", lang)}</Chip>
                  )}
                  {m.kind === "unsupported" && <Chip onClick={onBack}>{t("startOver", lang)}</Chip>}
                </div>
              )}
            </div>
          ),
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
              {slow && <p className="mt-2 text-xs text-muted">{t("wakingUp", lang)}</p>}
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
          placeholder={session.messages.length <= 1 ? t("placeholder", lang) : t("message", lang)}
          aria-label={t("message", lang)}
          className="min-h-12 min-w-0 flex-1 rounded-full border border-line bg-surface px-5 text-[15px] outline-none focus:border-brand"
        />
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
