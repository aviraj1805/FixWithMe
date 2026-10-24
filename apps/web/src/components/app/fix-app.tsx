"use client";

import { useCallback, useEffect, useState } from "react";
import { type Answers, type Procedure, type StepResponse, getProcedure, identify, sendOutcome, wakeApi } from "@/lib/api";
import { preparePhoto } from "@/lib/media";
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
  | { name: "guide"; item: string; procedureId: string; diagnosis: Diagnosis | null }
  | { name: "stop"; stop: NonNullable<StepResponse["stop"]> }
  | { name: "done"; resolved: boolean; tip: string | null };

const freshSession = (lang: Lang): Session => ({
  messages: [{ id: newId(), from: "fixy", text: t("whatsWrong", lang), kind: "intro" }],
  answers: {},
  item: null,
  causes: [],
  tier: null,
  mode: "diagnose",
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

  function startChat(listenNow = false) {
    setSessionState({ ...freshSession(lang), listenNow });
    setView({ name: "chat" });
  }

  async function startFromPhoto(file: File) {
    const s = freshSession(lang);
    const userMsg = { id: newId(), from: "user" as const, text: t("photo", lang) };
    setSessionState({ ...s, messages: [...s.messages, userMsg], photoPending: true });
    setView({ name: "chat" });
    try {
      const photo = await preparePhoto(file);
      const found = await identify({ image: photo.base64, mime: photo.mime, lang });
      setSessionState((cur) => ({ ...cur, photoPending: false, start: { text: found.text, item: found.item } }));
    } catch {
      setSessionState((cur) => ({
        ...cur,
        photoPending: false,
        messages: [...cur.messages, { id: newId(), from: "fixy", text: t("photoFailed", lang), kind: "intro" }],
      }));
    }
  }

  async function finish(item: string, procedureId: string, diagnosis: Diagnosis | null, resolved: boolean | null) {
    if (resolved === null) {
      goHome();
      return;
    }
    const answers: Answers = session.answers;
    if (diagnosis) {
      sendOutcome({ item, cause_id: diagnosis.cause_id, procedure_id: diagnosis.procedure_id, resolved, answers, lang }).catch(
        () => {},
      );
    }
    let tip: string | null = null;
    if (resolved) {
      tip = await getProcedure(item, procedureId, lang)
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
        <Home
          lang={lang}
          onLang={() => setLang((l) => (l === "en" ? "hi" : "en"))}
          onType={() => startChat()}
          onTalk={() => startChat(true)}
          onPhoto={(file) => void startFromPhoto(file)}
        />
      )}
      {view.name === "chat" && (
        <div className="flex h-dvh flex-col">
          <Chat
            lang={lang}
            session={session}
            setSession={setSession}
            onBack={goHome}
            onStop={(stop) => setView({ name: "stop", stop })}
            onGuide={(diagnosis) =>
              session.item &&
              setView({ name: "guide", item: session.item, procedureId: diagnosis.procedure_id, diagnosis })
            }
            onOpenGuide={(item, procedureId) => setView({ name: "guide", item, procedureId, diagnosis: null })}
          />
        </div>
      )}
      {view.name === "guide" && (
        <Guide
          lang={lang}
          item={view.item}
          procedureId={view.procedureId}
          onBack={() => setView({ name: "chat" })}
          onDone={(resolved) => void finish(view.item, view.procedureId, view.diagnosis, resolved)}
        />
      )}
      {view.name === "stop" && <Stop lang={lang} stop={view.stop} onBack={goHome} />}
      {view.name === "done" && (
        <Done lang={lang} resolved={view.resolved} tip={view.tip} nextCause={nextCause} onRestart={() => startChat()} />
      )}
    </main>
  );
}
