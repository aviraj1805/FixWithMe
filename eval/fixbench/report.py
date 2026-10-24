"""Builds the FixBench-IN markdown report from cached predictions in eval/reports/fixbench-v1/."""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from run import OUT, load_cases, summarize  # noqa: E402

LABELS = {
    "gemini_text": "(a) Gemini, first message only",
    "gemini_facts": "(a+) Gemini, first message + all facts",
    "engine_rules_before_fix": "(d0) Engine, rules only — before the budget fix",
    "engine_rules": "(d) Engine, rules only",
    "engine_gemini": "(d) Engine + Gemini extraction (production)",
}


def pct(x):
    return "—" if x is None else f"{x * 100:.1f}%"


def main() -> None:
    cases = load_cases()
    rows = []
    for name in LABELS:
        path = OUT / f"{name}.json"
        if path.exists():
            preds = json.loads(path.read_text(encoding="utf-8"))["predictions"]
            rows.append(summarize(name, cases, preds))
    (OUT / "summary.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")

    n = rows[0]["n"]
    lines = [
        f"# FixBench-IN v1 results ({date.today().isoformat()})",
        "",
        f"{len(cases)} cases: {n['cause']} with a known cause, {n['stop']} safety stops, "
        f"{n['out_of_scope']} out-of-scope items. Model for every Gemini call: `gemini-3.5-flash-lite` (free tier).",
        "",
        "| System | Top-1 | Top-3 | STOP recall | False STOPs | Out-of-scope handled | Avg questions | Mean latency |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in rows:
        lines.append(
            f"| {LABELS[s['system']]} | {pct(s['top1'])} | {pct(s['top3'])} | {pct(s['stop_recall'])} | "
            f"{pct(s['false_stop_rate'])} | {pct(s['out_of_scope_ok'])} | {s.get('avg_questions', '—')} | "
            f"{s['mean_latency_s']} s |"
        )
    lines += ["", "## Missed safety stops", ""]
    for s in rows:
        lines.append(f"- {LABELS[s['system']]}: {', '.join(s['missed_stops']) or 'none'}")
    lines += ["", "## Top-1 by language", "", "| System | English | Hindi | Hinglish |", "|---|---|---|---|"]
    for s in rows:
        b = s["by_lang"]
        lines.append(f"| {LABELS[s['system']]} | {pct(b['en']['top1'])} | {pct(b['hi']['top1'])} | {pct(b['hinglish']['top1'])} |")
    lines += ["", "## Top-1 by case type", "", "| System | Typical | Atypical | Hard |", "|---|---|---|---|"]
    for s in rows:
        b = s["by_tag"]
        lines.append(f"| {LABELS[s['system']]} | {pct(b['typical']['top1'])} | {pct(b['atypical']['top1'])} | {pct(b['hard']['top1'])} |")
    eng = [s for s in rows if "brier_top1" in s]
    if eng:
        lines += ["", "## Engine calibration", "", "| System | Mean confidence in top cause | Brier score (top-1) |", "|---|---|---|"]
        for s in eng:
            lines.append(f"| {LABELS[s['system']]} | {pct(s['mean_confidence'])} | {s['brier_top1']} |")
    (OUT.parent / f"fixbench-v1-{date.today().isoformat()}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
