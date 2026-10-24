"use client";

import { useEffect, useState } from "react";
import { getHealth, type Health } from "@/lib/api";

type State = { kind: "checking" } | { kind: "ok"; health: Health } | { kind: "down" };

export function ApiStatus() {
  const [state, setState] = useState<State>({ kind: "checking" });

  useEffect(() => {
    const controller = new AbortController();
    getHealth(controller.signal)
      .then((health) => setState({ kind: "ok", health }))
      .catch((err: unknown) => {
        if (!controller.signal.aborted) {
          console.warn("API health check failed", err);
          setState({ kind: "down" });
        }
      });
    return () => controller.abort();
  }, []);

  const label =
    state.kind === "checking"
      ? "Waking up the server…"
      : state.kind === "ok"
        ? `Server online · v${state.health.version}`
        : "Server unreachable";

  const dot =
    state.kind === "ok" ? "bg-emerald-500" : state.kind === "down" ? "bg-red-500" : "bg-amber-400";

  return (
    <p role="status" className="flex items-center gap-2 text-sm text-muted">
      <span className={`inline-block size-2 rounded-full ${dot}`} aria-hidden />
      {label}
    </p>
  );
}
