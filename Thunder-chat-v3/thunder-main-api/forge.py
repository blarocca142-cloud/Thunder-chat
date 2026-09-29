"""Thunder Forge: trade idle GPU time for code that is proven to work.

A frontier model writes working code on the first try more often because it
is bigger. A mid-size local model can close much of that gap another way -
the way AlphaCode and CodeT did: don't trust one attempt, make several, run
them all against tests, keep what passes, and repair what fails using the real
error output. The GPU is idle between messages; this spends it on correctness.

    1. Tests first, written blind - in a separate call that never sees any
       solution, so the tests cannot be bent to fit a solution's mistakes.
    2. N candidate solutions at different temperatures, for real variety.
    3. Every candidate run against the tests in the sandbox (no network).
    4. If none pass, the closest one is repaired from its actual traceback,
       for a few rounds.
    5. If every candidate fails the SAME assertion, the test itself is the
       likely culprit: the test is reviewed against the task and rewritten
       once, instead of "fixing" code that was right.

Nothing is reported as working unless it ran and passed here. The result says
what ran, how many attempts it took, and whether the tests were revised.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import tools

# Same window as app.py's chat calls - see the note on NUM_CTX there. Read from
# the environment rather than imported so forge stays usable standalone.
NUM_CTX = int(os.environ.get("THUNDER_NUM_CTX", "16384"))
CANDIDATES = int(os.environ.get("FORGE_CANDIDATES", "4"))
REPAIR_ROUNDS = int(os.environ.get("FORGE_REPAIR_ROUNDS", "3"))
TEMPS = [0.2, 0.6, 0.9, 1.1, 0.4, 0.8]
PASS_MARK = "ALL TESTS PASSED"

FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)
ASSERT_LINE = re.compile(r'File "[^"]*test_forge\.py", line (\d+)')


def _chat(ollama: str, model: str, system: str, user: str, temperature: float) -> str:
    payload = {"model": model, "stream": False, "think": False,
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
               "options": {"temperature": temperature, "num_predict": 4096, "repeat_penalty": 1.0,
                           # Forge runs on the chat model, so it must ask for the
                           # same window chat uses. Without this the first forge
                           # call evicted the resident chat runner and reloaded
                           # it at the default - then the next chat message
                           # reloaded it right back.
                           "num_ctx": NUM_CTX}}
    req = urllib.request.Request(f"{ollama}/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return (json.loads(r.read().decode()).get("message") or {}).get("content", "")


def _code(text: str) -> str:
    blocks = FENCE.findall(text)
    if blocks:
        return max(blocks, key=len).strip()
    return text.strip()


TEST_SYSTEM = (
    "You write tests, not solutions. Write ONE Python test script for the task below.\n"
    "- The solution will be in solution.py; start with `from solution import *`.\n"
    "- Plain assert statements only, no pytest. Cover normal cases and edge cases, but only "
    "behaviour the task actually specifies - never invent requirements.\n"
    f"- The last line must be: print('{PASS_MARK}')\n"
    "Reply with a single ```python block and nothing else."
)
SOLVE_SYSTEM = (
    "You are an expert programmer. Write solution.py for the task below: complete, "
    "importable Python with no top-level side effects (no input(), no prints at import). "
    "Reply with a single ```python block and nothing else."
)


def run_case(solution: str, test: str) -> dict:
    out = tools.run_files({"solution.py": solution, "test_forge.py": test}, "test_forge.py")
    out["passed"] = out.get("exit_code") == 0 and PASS_MARK in (out.get("stdout") or "")
    m = ASSERT_LINE.findall(out.get("stderr") or "")
    out["failed_at"] = int(m[-1]) if m else None
    return out


def _score(res: dict) -> int:
    """How close a failure is. Failing later in the test file means more
    asserts passed first; an import or syntax error is worst."""
    if res["passed"]:
        return 10_000
    if res.get("failed_at"):
        return res["failed_at"]
    return -1


def forge(task: str, ollama: str, model: str, candidates: int = CANDIDATES,
          rounds: int = REPAIR_ROUNDS) -> dict:
    log: list[str] = []
    test = _code(_chat(ollama, model, TEST_SYSTEM, task, 0.2))
    if PASS_MARK not in test:
        test += f"\nprint('{PASS_MARK}')\n"
    log.append(f"wrote tests ({test.count('assert')} asserts), blind to any solution")
    tests_revised = False

    def attempt(temp: float) -> str:
        return _code(_chat(ollama, model, SOLVE_SYSTEM, task, temp))

    with ThreadPoolExecutor(max_workers=candidates) as pool:
        sols = list(pool.map(attempt, [TEMPS[i % len(TEMPS)] for i in range(candidates)]))
    results = [run_case(s, test) for s in sols]
    attempts = len(sols)
    log.append(f"{attempts} candidates: {sum(r['passed'] for r in results)} passed")

    for rnd in range(rounds + 1):
        winners = [i for i, r in enumerate(results) if r["passed"]]
        if winners:
            best = min(winners, key=lambda i: len(sols[i]))  # shortest passing: least to go wrong
            return {"status": "passed", "solution": sols[best], "tests": test,
                    "attempts": attempts, "tests_revised": tests_revised, "log": log}
        if rnd == rounds:
            break

        # Everyone tripping on the same line smells like a bad test.
        lines = {r.get("failed_at") for r in results}
        if not tests_revised and len(results) > 1 and len(lines) == 1 and None not in lines:
            line_no = lines.pop()
            bad = test.splitlines()[line_no - 1] if 0 < line_no <= len(test.splitlines()) else ""
            review = _chat(ollama, model, TEST_SYSTEM,
                           f"{task}\n\nEvery independent solution failed this line of the tests:\n"
                           f"    {bad.strip()}\n\nIf that assertion does not follow from the task, "
                           "rewrite the test script without it. Otherwise return the script unchanged.\n\n"
                           f"```python\n{test}\n```", 0.1)
            new_test = _code(review)
            if new_test and new_test != test:
                test = new_test if PASS_MARK in new_test else new_test + f"\nprint('{PASS_MARK}')\n"
                tests_revised = True
                log.append(f"every candidate failed test line {line_no}; the test was reviewed and revised")
                results = [run_case(s, test) for s in sols]
                continue

        best = max(range(len(results)), key=lambda i: _score(results[i]))
        err = (results[best].get("stderr") or results[best].get("error") or "")[-3000:]
        fix = _code(_chat(ollama, model, SOLVE_SYSTEM,
                          f"{task}\n\nThis attempt fails its tests:\n```python\n{sols[best]}\n```\n\n"
                          f"Test output:\n```\n{err}\n```\nFix it.", 0.3))
        sols.append(fix)
        results.append(run_case(fix, test))
        attempts += 1
        log.append(f"repair round {rnd + 1}: {'passed' if results[-1]['passed'] else 'still failing'}")

    best = max(range(len(results)), key=lambda i: _score(results[i]))
    return {"status": "failed", "solution": sols[best], "tests": test, "attempts": attempts,
            "tests_revised": tests_revised, "log": log,
            "last_error": (results[best].get("stderr") or results[best].get("error") or "")[-1500:]}
