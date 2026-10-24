export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Health = {
  status: "ok";
  version: string;
  llm_provider: string;
};

export async function getHealth(signal?: AbortSignal): Promise<Health> {
  // Render's free tier sleeps after 15 min idle and takes about a minute to wake up.
  const res = await fetch(`${API_URL}/health`, { signal, cache: "no-store" });
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}
