import type { Lang } from "./i18n";

/** Downscale a photo to at most `max` px and re-encode as JPEG. Re-encoding through a canvas
 * also drops EXIF metadata (GPS location, device), so none of it leaves the phone. */
export async function preparePhoto(file: File, max = 768): Promise<{ base64: string; mime: "image/jpeg" }> {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, max / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  const dataUrl = canvas.toDataURL("image/jpeg", 0.8);
  return { base64: dataUrl.slice(dataUrl.indexOf(",") + 1), mime: "image/jpeg" };
}

type Recognition = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

function recognitionCtor(): (new () => Recognition) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as (new () => Recognition) | null;
}

export const speechSupported = () => recognitionCtor() !== null;

/** Push-to-talk with the browser's speech recognition. Chrome sends audio to Google's servers
 * for this; typing is always available instead. Returns a stop function. */
export function listen(lang: Lang, onText: (text: string) => void, onEnd: () => void): () => void {
  const Ctor = recognitionCtor();
  if (!Ctor) {
    onEnd();
    return () => {};
  }
  const rec = new Ctor();
  rec.lang = lang === "hi" ? "hi-IN" : "en-IN";
  rec.interimResults = false;
  rec.maxAlternatives = 1;
  rec.onresult = (e) => {
    const text = e.results[0]?.[0]?.transcript?.trim();
    if (text) onText(text);
  };
  rec.onerror = () => onEnd();
  rec.onend = () => onEnd();
  rec.start();
  return () => rec.stop();
}
