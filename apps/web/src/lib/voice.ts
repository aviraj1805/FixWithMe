import { API_URL } from "./api";
import type { Lang } from "./i18n";

let current: HTMLAudioElement | null = null;
let ttsDown = false; // after a failure (quota), use the browser voice for the rest of the visit

/** Strip things that sound bad read aloud: citation marks, symbols, emoji. */
function clean(text: string): string {
  return text
    .replace(/\[\d+\]/g, "")
    .replace(/[•*_#>~]/g, "")
    .replace(/[\u{1F300}-\u{1FAFF}]/gu, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 600);
}

function pickVoice(lang: Lang): SpeechSynthesisVoice | undefined {
  const voices = window.speechSynthesis.getVoices();
  const want = lang === "hi" ? /^hi/i : /^en-(IN|GB|US)/i;
  const female = /(swara|neerja|kalpana|heera|female|zira|aria|jenny|samantha|google हिन्दी|google uk english female|veena|lekha)/i;
  const inLang = voices.filter((v) => want.test(v.lang));
  return (
    inLang.find((v) => female.test(v.name) && /natural|online|google/i.test(v.name)) ??
    inLang.find((v) => female.test(v.name)) ??
    inLang.find((v) => /IN/.test(v.lang)) ??
    inLang[0]
  );
}

function browserSpeak(text: string, lang: Lang): Promise<void> {
  return new Promise((resolve) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return resolve();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang === "hi" ? "hi-IN" : "en-IN";
    const v = pickVoice(lang);
    if (v) u.voice = v;
    u.pitch = 1.1;
    u.rate = 1.0;
    u.onend = () => resolve();
    u.onerror = () => resolve();
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  });
}

/** Fixy speaks: Gemini's warm female voice, or the browser's best female voice as a fallback.
 * Resolves when speech ends (or fails), so callers can start listening afterwards. */
export async function speak(text: string, lang: Lang): Promise<void> {
  stopSpeaking();
  const line = clean(text);
  if (!line) return;
  if (!ttsDown) {
    try {
      const res = await fetch(`${API_URL}/v1/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: line, lang }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const url = URL.createObjectURL(await res.blob());
      const audio = new Audio(url);
      current = audio;
      await new Promise<void>((resolve) => {
        audio.onended = audio.onerror = audio.onpause = () => resolve();
        audio.play().catch(() => resolve());
      });
      URL.revokeObjectURL(url);
      return;
    } catch {
      ttsDown = true;
    }
  }
  await browserSpeak(line, lang);
}

export function stopSpeaking(): void {
  current?.pause();
  current = null;
  if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
}

/** Spoken commands in a guide ("next", "aage", "repeat"…). */
export function voiceCommand(text: string): "next" | "back" | "repeat" | "yes" | "no" | "unknown" | null {
  const t = text.toLowerCase().trim();
  if (/^(next|aage|aagey|agla|age|done|ho gaya|hogaya|आगे|अगला|हो गया)\b/.test(t)) return "next";
  if (/^(back|previous|peeche|piche|pichla|पीछे|पिछला)\b/.test(t)) return "back";
  if (/^(repeat|again|dobara|phir se|fir se|दोबारा|फिर से)\b/.test(t)) return "repeat";
  if (/^(not sure|pata nahi|pata nahin|maloom nahi|पता नहीं)\b/.test(t)) return "unknown";
  if (/^(yes|yeah|yep|haan|ha|han|ji haan|हाँ|हां|जी)\b/.test(t)) return "yes";
  if (/^(no|nope|nahi|nahin|na|नहीं|ना)\b/.test(t)) return "no";
  return null;
}
