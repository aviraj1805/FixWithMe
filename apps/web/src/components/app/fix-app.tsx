"use client";

import { useCallback, useEffect, useState } from "react";
import { type Answers, type Procedure, type StepResponse, getProcedure, sendOutcome, wakeApi } from "@/lib/api";
import { type Lang, t } from "@/lib/i18n";
import { Chat, type Session, newId } from "./chat";
import { Guide } from "./guide";
import { Home, Welcome } from "./home";
import { Done, Stop } from "./outcomes";

type Diagnosis = NonNullable<StepResponse["diagnosis"]>;
type View =
  | { name: "welcome" }
  | { name: "home" }
  | { name: "chat" }
  | { name: "guide"; diagnosis: Diagnosis }
  | { name: "stop"; stop: NonNullable<StepResponse["stop"]> }
  | { name: "done"; resolved: boolean; tip: string | null };

const freshSession = (lang: Lang): Session => ({
  messages: [{ id: newId(), from: "fixy", text: t("whatsWrong", lang), kind: "intro" }],
  answers: {},
  item: null,
  causes: [],
  tier: null,
});

export function FixApp() {
  const [lang, setLang] = useState<Lang>("en");
  const [view, setView] = useState<View>({ name: "welcome" });
  const [session, setSessionState] = useState<Session>(() => freshSession("en"));

  useEffect(() => {
    wakeApi();
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setSession = useCallback((update: (s: Session) => Session) => setSessionState(update), []);
  const goHome = useCallback(() => setView({ name: "home" }), []);

  function startChat() {
    setSessionState(freshSession(lang));
    setView({ name: "chat" });
  }

  async function finish(diagnosis: Diagnosis, resolved: boolean | null) {
    if (resolved === null) {
      goHome();
      return;
    }
    const answers: Answers = session.answers;
    sendOutcome({ cause_id: diagnosis.cause_id, procedure_id: diagnosis.procedure_id, resolved, answers, lang }).catch(
      () => {},
    );
    let tip: string | null = null;
    if (resolved) {
      tip = await getProcedure(diagnosis.procedure_id, lang)
        .then((p: Procedure) => p.prevent)
        .catch(() => null);
    }
    setView({ name: "done", resolved, tip });
  }

  const nextCause = session.causes[1] ?? null;

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col">
      {view.name === "welcome" && <Welcome lang={lang} onDone={goHome} />}
      {view.name === "home" && (
        <Home lang={lang} onLang={() => setLang((l) => (l === "en" ? "hi" : "en"))} onType={startChat} />
      )}
      {view.name === "chat" && (
        <div className="flex h-dvh flex-col">
          <Chat
            lang={lang}
            session={session}
            setSession={setSession}
            onBack={goHome}
            onStop={(stop) => setView({ name: "stop", stop })}
            onGuide={(diagnosis) => setView({ name: "guide", diagnosis })}
          />
        </div>
      )}
      {view.name === "guide" && (
        <Guide
          lang={lang}
          procedureId={view.diagnosis.procedure_id}
          onBack={() => setView({ name: "chat" })}
          onDone={(resolved) => void finish(view.diagnosis, resolved)}
        />
      )}
      {view.name === "stop" && <Stop lang={lang} stop={view.stop} onBack={goHome} />}
      {view.name === "done" && (
        <Done lang={lang} resolved={view.resolved} tip={view.tip} nextCause={nextCause} onRestart={startChat} />
      )}
    </main>
  );
}
