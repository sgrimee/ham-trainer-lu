"""Score one or more models against the golden grading cases (specs/TRAINER.md §8.2).

    mise run eval-grader                                  # the configured LLM_MODEL
    mise run eval-grader openai/gpt-5.1                   # one candidate
    mise run eval-grader openai/gpt-5.1 mistralai/mistral-medium-3.1
    mise run eval-grader --runs 2 openai/gpt-5.1          # also report repeatability
    mise run eval-grader --set spelling                   # the spelling battery (specs/LEARN-2-3.md §4.3)
    mise run eval-grader --set parts-2-3                  # BASE parts 2-3 only (LEARN-2-3 §4.5)
    mise run eval-grader --set german                     # German answers (LEARN-DE §2.5)
    mise run eval-grader --set all                        # golden (parts 2-3 included) and spelling

Reads LLM_BASE_URL / LLM_API_KEY / LLM_MODEL from the environment, which mise
autoloads from .env. Needs a key and spends a few cents per model, so it is
deliberately not a pytest test. Raw responses land in var/eval/ for inspection.

Run it after every change to app/grading_prompt.py.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # the fixtures, alongside this file
sys.path.insert(0, str(HERE.parent))  # the repo root, for the app package

import grading_fixtures  # noqa: E402
import spelling_fixtures  # noqa: E402

from app import catalogue, official_wordings  # noqa: E402
from app.grading_prompt import request_body  # noqa: E402  (the exact body the app itself sends)

SETS = {
    "golden": grading_fixtures.CASES,  # parts-2-3 and German included
    "parts-2-3": grading_fixtures.PART_2_3,
    "german": grading_fixtures.GERMAN,  # specs/LEARN-DE.md §2.5
    "spelling": spelling_fixtures.CASES,
}
CASES = SETS["golden"]  # replaced by main() from --set

OUT_DIR = HERE.parent / "var" / "eval"


def guide_context(case) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The other official wordings and guide notes the app would send for this
    case (specs/LEARN-2-3.md §4.5): the case's question id is its id's leading
    digits, and its sub-item the catalogue item whose reference is the case's."""
    cid, lang, _, reference = case[:4]
    qid = int(re.match(r"\d+", cid).group())
    q = catalogue.load().by_id.get(qid)
    # A German case's reference is the neutral cell where German has none.
    items = [
        i for i in (q or {}).get("answer", []) if (i["text"].get(lang) or i["text"].get("fr")) == reference
    ]
    if not items:
        return (), ()
    item_no = items[0]["item_no"]
    return official_wordings.for_item(qid, item_no, lang), official_wordings.notes_for_item(
        qid, item_no, lang
    )


def grade(model: str, case) -> dict:
    """One grading call. A failure is a result, not a crash."""
    cid, lang, question, reference, candidate = case[:5]
    body = request_body(model, lang, question, reference, candidate, *guide_context(case))

    req = urllib.request.Request(
        f"{os.environ['LLM_BASE_URL']}/chat/completions",
        method="POST",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {os.environ['LLM_API_KEY']}", "Content-Type": "application/json"},
    )
    started = time.time()
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                payload = json.load(response)
            usage = payload.get("usage", {})
            return {
                "case": cid,
                "secs": round(time.time() - started, 1),
                "tokens_in": usage.get("prompt_tokens") or 0,
                "tokens_out": usage.get("completion_tokens") or 0,
                **json.loads(payload["choices"][0]["message"]["content"]),
            }
        except urllib.error.HTTPError as e:
            # 429 here is usually upstream capacity, not our own rate limit.
            if e.code in (429, 503) and attempt < 3:
                time.sleep(15 * (attempt + 1))
                continue
            return {"case": cid, "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
        except Exception as e:  # noqa: BLE001
            if attempt < 3:
                time.sleep(10)
                continue
            return {"case": cid, "error": str(e)[:200]}
    raise AssertionError("unreachable: the last loop iteration always returns")


def verdict(result: dict) -> tuple[str, float]:
    """Derive the verdict and the proportional score (specs/TRAINER.md §7.2).

    A near element (specs/LEARN-2-3.md §4.2) scores as missing, as in
    app/scoring.py; the verdict is "near" when it is the only thing wrong.
    """
    elements = result.get("elements", [])
    present = sum(1 for e in elements if e["present"])
    near = sum(1 for e in elements if e["present"] and e.get("near"))
    found = present - near
    total = len(elements)
    share = found / total if total else 0.0
    if result.get("incorrect"):
        return ("partial" if present else "incorrect"), share
    if total and present == total:
        return ("near", share) if near else ("correct", 1.0)
    return ("incorrect" if present == 0 else "partial"), share


def one_run(model: str) -> dict[str, dict]:
    with ThreadPoolExecutor(max_workers=4) as pool:
        return {r["case"]: r for r in pool.map(lambda c: grade(model, c), CASES)}


def report(model: str, runs: list[dict[str, dict]]) -> dict:
    """Print the per-case table for the first run, and summarise across all runs."""
    first = runs[0]
    print(f"\n{model}")
    print(f"  {'case':14} {'expected':10} {'got':10} {'score':>6}  {'':4} notes")
    hits = traps_hit = traps = 0
    for case in CASES:
        cid, expected, must_flag = case[0], case[5], case[6]
        r = first[cid]
        if "error" in r:
            print(f"  {cid:14} {expected:10} {'ERROR':10} {'':>6}       {r['error']}")
            continue
        got, share = verdict(r)
        # A near form (spelling_fixtures) is right on the air but not the ILR's
        # form: a grader that withholds full marks and flags it has done its job.
        ok = got == expected or (expected == "near" and got == "partial")
        hits += ok
        note = ""
        if expected == "near":
            # must_flag names the near word, which must be reported near, not false.
            flagged = [e for e in r.get("elements", []) if e.get("near")]
            note = f"near → {flagged[0].get('official', '')!r}" if flagged else ""
        elif must_flag:
            traps += 1
            caught = any(must_flag.lower() in s.lower() for s in r.get("incorrect", []))
            traps_hit += caught
            note = "false statement flagged" if caught else "MISSED THE FALSE STATEMENT"
        print(
            f"  {cid:14} {expected:10} {got:10} {share * 100:5.0f}%  "
            f"{'ok ' if ok else 'BAD'} {r['secs']:4.1f}s  {note}"
        )

    graded = [r for r in first.values() if "error" not in r]
    stable = drift = None
    if len(runs) > 1:
        pairs = [
            (verdict(a[c]), verdict(b[c]))
            for a, b in zip(runs, runs[1:], strict=False)
            for c in a
            if "error" not in a[c] and "error" not in b[c]
        ]
        stable = sum(x[0] == y[0] for x, y in pairs) / len(pairs) if pairs else 0
        drift = sum(abs(x[1] - y[1]) for x, y in pairs) / len(pairs) if pairs else 0

    summary = {
        "model": model,
        "verdicts": hits,
        "cases": len(CASES),
        "traps": f"{traps_hit}/{traps}",
        "median_s": sorted(r["secs"] for r in graded)[len(graded) // 2] if graded else None,
        "tokens_in": round(sum(r["tokens_in"] for r in graded) / len(graded)) if graded else 0,
        "tokens_out": round(sum(r["tokens_out"] for r in graded) / len(graded)) if graded else 0,
        "errors": sum(1 for r in first.values() if "error" in r),
        "stable": stable,
        "drift": drift,
    }
    print(
        f"  -> {hits}/{len(CASES)} verdicts, {traps_hit}/{traps} false statements caught, "
        f"median {summary['median_s']}s, ~{summary['tokens_in']} in / {summary['tokens_out']} out tokens"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("models", nargs="*", help="model ids; defaults to $LLM_MODEL")
    parser.add_argument(
        "--runs", type=int, default=1, help="repeat each model N times and report verdict stability"
    )
    parser.add_argument("--set", choices=[*SETS, "all"], default="golden", help="which cases to score")
    args = parser.parse_args()
    global CASES
    CASES = SETS[args.set] if args.set != "all" else [*SETS["golden"], *SETS["spelling"]]

    for var in ("LLM_BASE_URL", "LLM_API_KEY"):
        if not os.environ.get(var):
            sys.exit(f"{var} is not set. mise autoloads .env; see .env.example.")
    models = args.models or [os.environ.get("LLM_MODEL", "")]
    if not any(models):
        sys.exit("No model given and LLM_MODEL is not set.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    for model in models:
        runs = [one_run(model) for _ in range(args.runs)]
        (OUT_DIR / f"{model.replace('/', '_')}-{args.set}.json").write_text(
            json.dumps(runs, indent=1, ensure_ascii=False)
        )
        summaries.append(report(model, runs))

    if len(summaries) > 1 or args.runs > 1:
        print(
            f"\n{'model':38} {'verdicts':>9} {'traps':>6} {'median':>7} "
            f"{'tok in/out':>11} {'stable':>7} {'drift':>6} {'err':>4}"
        )
        for s in summaries:
            stable = f"{s['stable'] * 100:.0f}%" if s["stable"] is not None else "-"
            drift = f"{s['drift'] * 100:.1f}pp" if s["drift"] is not None else "-"
            print(
                f"{s['model']:38} {s['verdicts']:6}/{s['cases']:<2} {s['traps']:>6} "
                f"{s['median_s']:6}s {s['tokens_in']:5}/{s['tokens_out']:<5} "
                f"{stable:>7} {drift:>6} {s['errors']:4}"
            )

    print(f"\nRaw responses: {OUT_DIR}")
    worst = min((s["verdicts"] for s in summaries), default=0)
    return 0 if worst == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
