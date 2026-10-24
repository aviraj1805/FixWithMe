import type { Lang } from "./i18n";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Answer = "yes" | "no" | "unknown";
export type Answers = Record<string, Answer>;

export type Cause = { id: string; name: string; short: string; p: number };

export type StepResponse = {
  state: "question" | "diagnosis" | "stop" | "confirm" | "clarify" | "unsupported";
  say: string;
  confirm: { hazard: string; text: string } | null;
  item: string | null;
  answers: Answers;
  options: { id: string; name: string }[];
  causes: Cause[];
  question: { id: string; text: string; safety: boolean } | null;
  diagnosis: {
    cause_id: string;
    cause: string;
    confidence: number;
    label: "likely" | "possible" | "uncertain";
    procedure_id: string;
    procedure_title: string;
    professional: boolean;
  } | null;
  stop: { hazard: string; title: string; actions: string[]; call: string } | null;
  tier: "verified" | "curated" | null;
  llm_used: boolean;
};

export type SourceRef = { title: string; url: string };

export type Procedure = {
  id: string;
  tier: "verified" | "curated";
  title: string;
  safety_level: 0 | 1 | 2 | 3;
  minutes: number | null;
  difficulty: string | null;
  cost_inr: { min: number; max: number; basis: "estimate" } | null;
  tools: string[];
  steps: { text: string; caution: string | null; sources: SourceRef[] }[];
  verify: string | null;
  prevent: string | null;
  professional: string | null;
  reason: string | null;
  sources: SourceRef[];
};

export type AskResponse = {
  state: "answer" | "abstain" | "stop" | "confirm";
  say: string;
  claims: { text: string; sources: string[] }[];
  sources: { id: string; title: string; url: string | null; license: string; source_type: string }[];
  tier: "curated" | "sourced" | "web" | null;
  guides: { item: string; procedure_id: string; safety_level: number }[];
  caution: string | null;
  verified: boolean;
  stop: StepResponse["stop"];
  confirm: StepResponse["confirm"];
  search_html: string | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export function step(body: {
  text?: string;
  answers: Answers;
  item: string | null;
  lang: Lang;
  safety_checked?: boolean;
  confirm_hazard?: string;
}): Promise<StepResponse> {
  return request("/v1/sessions/step", { method: "POST", body: JSON.stringify(body) });
}

/** Free-form question, answered only from cited sources; abstains when they don't cover it. */
export function ask(body: {
  question: string;
  item: string | null;
  lang: Lang;
  safety_checked?: boolean;
  confirm_hazard?: string;
  web?: boolean;
}): Promise<AskResponse> {
  return request("/v1/ask", { method: "POST", body: JSON.stringify(body) });
}

export function getProcedure(item: string, id: string, lang: Lang): Promise<Procedure> {
  return request(`/v1/procedures/${encodeURIComponent(item)}/${encodeURIComponent(id)}?lang=${lang}`);
}

export function sendOutcome(body: {
  item: string;
  cause_id: string;
  procedure_id: string;
  resolved: boolean;
  answers: Answers;
  lang: Lang;
}): Promise<{ stored: boolean }> {
  return request("/v1/outcomes", { method: "POST", body: JSON.stringify(body) });
}

export type Identified = { item: string | null; name: string; problem: string | null; text: string };

/** Photo → item + visible problem. The photo is downscaled and EXIF-free (see media.ts). */
export function identify(body: { image: string; mime: string; lang: Lang }): Promise<Identified> {
  return request("/v1/identify", { method: "POST", body: JSON.stringify(body) });
}

/** Warm the API early: Render's free tier sleeps after 15 minutes and takes ~1 minute to wake. */
export function wakeApi(): void {
  fetch(`${API_URL}/health`, { cache: "no-store" }).catch(() => {});
}
