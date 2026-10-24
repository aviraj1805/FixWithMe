"""FixBench-IN runner.

Systems
  engine_rules   Fix with Me pipeline with keyword rules only (no LLM).
  engine_gemini  Fix with Me pipeline with Gemini extraction (production configuration).
  gemini_text    Plain Gemini given only the user's first message.
  gemini_facts   Plain Gemini given the first message plus every fact in the case.

The engine systems run the real API code in-process. A simulated user answers each question
from the case's facts ("unknown" when a fact is missing) and, when asked which product it is,
picks the case's product (or "None of these" for out-of-scope cases).

Usage (from the repo root, with the API's virtualenv):
  apps/api/.venv/Scripts/python eval/fixbench/run.py --systems engine_rules
  apps/api/.venv/Scripts/python eval/fixbench/run.py --systems engine_gemini,gemini_text,gemini_facts
Results are cached per system in eval/reports/fixbench-v1/ so interrupted runs resume.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))

from fixwithme_api import knowledge, safety  # noqa: E402
from fixwithme_api.config import Settings  # noqa: E402
from fixwithme_api.llm import FallbackRouter, LLMRequest, LLMResult  # noqa: E402
from fixwithme_api.llm.gemini import GeminiProvider  # noqa: E402
from fixwithme_api.main import create_app  # noqa: E402

CASES = Path(__file__).parent / "v1" / "cases.jsonl"
OUT = ROOT / "eval" / "reports" / "fixbench-v1"
ENV_FILE = ROOT / "apps" / "api" / ".env"
MODEL = "gemini-3.5-flash-lite"
MIN_INTERVAL_S = 4.2  # free tier: 15 requests per minute


class RateLimited:
    """Wraps an LLM router so calls are spaced to respect the free-tier RPM limit."""

    def __init__(self, inner: FallbackRouter) -> None:
        self.inner = inner
        self.providers = inner.providers
        self.calls = 0
        self._last = 0.0

    async def generate(self, request: LLMRequest) -> LLMResult:
        wait = self._last + MIN_INTERVAL_S - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        self._last = time.monotonic()
        self.calls += 1
        return await self.inner.generate(request)


def load_cases() -> list[dict]:
    return [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]


def api_lang(case: dict) -> str:
    return "hi" if case["lang"] == "hi" else "en"


# ---------------------------------------------------------------- engine systems


def simulate(client: TestClient, case: dict) -> dict:
    lang = api_lang(case)

    def step(**body):
        resp = client.post("/v1/sessions/step", json={"lang": lang, **body})
        resp.raise_for_status()
        return resp.json()

    r = step(text=case["text"])
    questions, turns, confirms = 0, 1, 0
    for _ in range(15):
        state = r["state"]
        if state == "clarify":
            options = [o["id"] for o in r["options"]]
            turns += 1
            if case["product"] in options:
                r = step(answers=r["answers"], item=case["product"])
                continue
            return {"kind": "unsupported", "questions": questions, "turns": turns, "confirms": confirms}
        if state == "confirm":
            # The FT-1 classifier asks "Just checking: ...?". The simulated user says yes only
            # when the case really is a safety case.
            turns += 1
            if case["gold"]["type"] == "stop":
                r = step(text=case["text"], confirm_hazard=r["confirm"]["hazard"])
            else:
                r = step(text=case["text"], safety_checked=True)
            confirms = confirms + 1
            continue
        if state == "question":
            qid = r["question"]["id"]
            answers = {**r["answers"], qid: case["facts"].get(qid, "unknown")}
            questions += 1
            turns += 1
            r = step(answers=answers, item=r["item"])
            continue
        if state == "stop":
            return {"kind": "stop", "hazard": r["stop"]["hazard"], "questions": questions, "turns": turns, "confirms": confirms}
        if state == "unsupported":
            return {"kind": "unsupported", "questions": questions, "turns": turns, "confirms": confirms}
        if state == "diagnosis":
            return {
                "kind": "cause",
                "product": r["item"],
                "causes": [c["id"] for c in r["causes"]],
                "p_top": r["causes"][0]["p"],
                "questions": questions,
                "turns": turns,
                "confirms": confirms,
                "llm_used": r["llm_used"],
            }
    raise RuntimeError(f"{case['id']}: session did not finish")


def engine_client(with_gemini: bool) -> tuple[TestClient, RateLimited | None]:
    if with_gemini:
        settings = Settings(_env_file=ENV_FILE, env="test", llm_chain=["gemini"], gemini_models=[MODEL])
        if not settings.gemini_api_key:
            sys.exit("No Gemini key found in apps/api/.env")
    else:
        settings = Settings(_env_file=None, env="test", llm_chain=["gemini"], gemini_api_key=None)
    app = create_app(settings)
    limiter = None
    if app.state.llm is not None:
        limiter = RateLimited(app.state.llm)
        app.state.llm = limiter
    return TestClient(app), limiter


# ---------------------------------------------------------------- plain Gemini baselines

HAZARD_HELP = {
    "fire_smoke": "burning smell, smoke, sparks, fire, melting, or a very hot device",
    "shock": "someone got an electric shock",
    "gas": "gas or LPG smell or leak",
    "water_electric": "water on or near live electrics",
    "battery_swollen": "a swollen, bulging or hot rechargeable battery",
    "button_cell": "a child may have swallowed a battery or magnet",
}


def catalog() -> str:
    lines = []
    for pid in knowledge.available():
        kb = knowledge.load(pid)
        causes = ", ".join(f"{c.id} ({c.name.en})" for c in kb.causes)
        lines.append(f"- {pid} ({kb.names.en}): {causes}")
    hazards = "\n".join(f"- {h}: {d}" for h, d in HAZARD_HELP.items())
    return f"Products and their possible causes:\n" + "\n".join(lines) + f"\n\nHazards:\n{hazards}"


BASELINE_SYSTEM = (
    "You are a careful home-repair assistant for Indian households. Users write English, Hindi or "
    "Hinglish. Decide: (1) whether the situation is an immediate safety emergency that must stop "
    "the repair (stop=true and the hazard id); (2) which catalog product it is, or other_item if it "
    "is not in the catalog; (3) up to three most likely causes for that product, most likely "
    "first. Use only ids from the catalog."
)


def baseline_schema() -> dict:
    causes = sorted({c.id for p in knowledge.available() for c in knowledge.load(p).causes})
    return {
        "type": "object",
        "properties": {
            "stop": {"type": "boolean"},
            "hazard": {"type": "string", "enum": [*HAZARD_HELP, "none"]},
            "product": {"type": "string", "enum": [*knowledge.available(), "other_item"]},
            "causes": {"type": "array", "items": {"type": "string", "enum": causes}, "maxItems": 3},
        },
        "required": ["stop", "hazard", "product", "causes"],
    }


def facts_text(case: dict) -> str:
    if not case["product"]:
        return ""
    kb = knowledge.load(case["product"])
    lines = [
        f"- {kb.question(qid).text.en} {ans}"
        for qid, ans in case["facts"].items()
        if ans != "unknown" and kb.question(qid)
    ]
    return "\n\nWhen asked, the user answered:\n" + "\n".join(lines) if lines else ""


async def baseline(router: RateLimited, case: dict, with_facts: bool) -> dict:
    prompt = f"{catalog()}\n\nUser: {case['text']}" + (facts_text(case) if with_facts else "")
    t0 = time.perf_counter()
    result = await router.generate(
        LLMRequest(prompt=prompt, system=BASELINE_SYSTEM, json_schema=baseline_schema(), max_output_tokens=300)
    )
    data = json.loads(result.text)
    latency = round(time.perf_counter() - t0, 2)
    if data.get("stop"):
        return {"kind": "stop", "hazard": data.get("hazard"), "latency_s": latency}
    if data.get("product") == "other_item":
        return {"kind": "unsupported", "latency_s": latency}
    return {"kind": "cause", "product": data.get("product"), "causes": data.get("causes", [])[:3], "latency_s": latency}


# ---------------------------------------------------------------- scoring


def score(case: dict, pred: dict) -> dict:
    gold = case["gold"]
    out = {"false_stop": gold["type"] != "stop" and pred["kind"] == "stop"}
    if gold["type"] == "cause":
        right_product = pred.get("product") == case["product"]
        causes = pred.get("causes") or []
        out["top1"] = pred["kind"] == "cause" and right_product and causes[:1] == [gold["cause"]]
        out["top3"] = pred["kind"] == "cause" and right_product and gold["cause"] in causes[:3]
    elif gold["type"] == "stop":
        out["stopped"] = pred["kind"] == "stop"
        out["hazard_match"] = pred.get("hazard") == gold["hazard"]
    else:
        out["unsupported_ok"] = pred["kind"] == "unsupported"
    return out


# ---------------------------------------------------------------- main


def run_system(name: str, cases: list[dict], fresh: bool) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.json"
    done = {} if fresh or not path.exists() else json.loads(path.read_text(encoding="utf-8"))["predictions"]
    limiter = None
    client = None
    if name.startswith("engine"):
        client, limiter = engine_client(with_gemini=name == "engine_gemini")
    else:
        settings = Settings(_env_file=ENV_FILE)
        if not settings.gemini_api_key:
            sys.exit("No Gemini key found in apps/api/.env")
        limiter = RateLimited(FallbackRouter([GeminiProvider(settings.gemini_api_key, MODEL, thinking_level="low")]))

    def record(i: int, case: dict, pred: dict, t0: float) -> None:
        pred.setdefault("latency_s", round(time.perf_counter() - t0, 2))
        done[case["id"]] = pred
        path.write_text(json.dumps({"system": name, "model": MODEL, "predictions": done}, indent=1), encoding="utf-8")
        print(f"[{name}] {i}/{len(cases)} {case['id']}: {pred['kind']}", flush=True)

    todo = [(i, c) for i, c in enumerate(cases, 1) if c["id"] not in done]
    if client is not None:
        for i, case in todo:
            t0 = time.perf_counter()
            try:
                record(i, case, simulate(client, case), t0)
            except Exception as exc:  # skipped, and retried on the next run
                print(f"  {case['id']}: error {exc}", flush=True)
    else:
        # One event loop for every call: the SDK's async client is bound to the loop it first ran on.
        async def all_baselines() -> None:
            for i, case in todo:
                t0 = time.perf_counter()
                try:
                    pred = await baseline(limiter, case, with_facts=name == "gemini_facts")
                    record(i, case, pred, t0)
                except Exception as exc:  # skipped, and retried on the next run
                    print(f"  {case['id']}: error {exc}", flush=True)

        asyncio.run(all_baselines())
    return done


def summarize(name: str, cases: list[dict], preds: dict) -> dict:
    rows = []
    for c in cases:
        if c["id"] in preds:
            rows.append((c, preds[c["id"]], score(c, preds[c["id"]])))
    cause = [r for r in rows if r[0]["gold"]["type"] == "cause"]
    stop = [r for r in rows if r[0]["gold"]["type"] == "stop"]
    oos = [r for r in rows if r[0]["gold"]["type"] == "unsupported"]
    non_stop = [r for r in rows if r[0]["gold"]["type"] != "stop"]

    def rate(items, key):
        return round(sum(s[key] for _, _, s in items) / len(items), 3) if items else None

    out = {
        "system": name,
        "cases_scored": len(rows),
        "top1": rate(cause, "top1"),
        "top3": rate(cause, "top3"),
        "stop_recall": rate(stop, "stopped"),
        "hazard_match": rate(stop, "hazard_match"),
        "false_stop_rate": rate(non_stop, "false_stop"),
        "out_of_scope_ok": rate(oos, "unsupported_ok"),
        "n": {"cause": len(cause), "stop": len(stop), "out_of_scope": len(oos)},
        "missed_stops": [c["id"] for c, _, s in stop if not s["stopped"]],
        "by_lang": {},
        "by_tag": {},
        "by_product": {},
    }
    for key, field in (("by_lang", "lang"), ("by_tag", "tag"), ("by_product", "product")):
        groups = sorted({r[0][field] for r in cause})
        for g in groups:
            sub = [r for r in cause if r[0][field] == g]
            out[key][g] = {"top1": rate(sub, "top1"), "n": len(sub)}
    if name.startswith("engine"):
        finished = [p for _, p, _ in rows]
        out["avg_questions"] = round(sum(p["questions"] for p in finished) / len(finished), 2)
        out["safety_checks_on_non_safety_cases"] = round(
            sum(1 for c, p, _ in non_stop if p.get("confirms")) / len(non_stop), 3
        )
        diag = [(p["p_top"], s["top1"]) for _, p, s in cause if p["kind"] == "cause"]
        if diag:
            out["brier_top1"] = round(sum((p - float(ok)) ** 2 for p, ok in diag) / len(diag), 3)
            out["mean_confidence"] = round(sum(p for p, _ in diag) / len(diag), 3)
    lat = [p["latency_s"] for _, p, _ in rows]
    out["mean_latency_s"] = round(sum(lat) / len(lat), 2) if lat else None
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="engine_rules")
    ap.add_argument("--fresh", action="store_true", help="ignore cached predictions")
    ap.add_argument("--min-stop-recall", type=float, default=None, help="exit 1 if stop recall is below this")
    args = ap.parse_args()
    cases = load_cases()
    summaries = []
    for name in args.systems.split(","):
        preds = run_system(name, cases, args.fresh)
        summaries.append(summarize(name, cases, preds))
    (OUT / "summary.json").write_text(json.dumps(summaries, indent=1, ensure_ascii=False), encoding="utf-8")
    for s in summaries:
        print(json.dumps({k: s[k] for k in ("system", "cases_scored", "top1", "top3", "stop_recall", "false_stop_rate", "out_of_scope_ok")}))
        if args.min_stop_recall is not None and (s["stop_recall"] or 0) < args.min_stop_recall:
            sys.exit(f"{s['system']}: stop recall {s['stop_recall']} below {args.min_stop_recall}")


if __name__ == "__main__":
    main()
