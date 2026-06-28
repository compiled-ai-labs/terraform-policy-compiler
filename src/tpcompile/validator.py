"""Validation gates for a candidate Rego policy.

Four gates, run in order. The first two are structural and stop the pipeline on
failure; the last two are functional and both run so the LLM gets full feedback.

  1. opa parse   - the Rego is syntactically valid.
  2. opa check   - the Rego compiles (types, safety, imports).
  3. conftest    - the policy denies the known-bad plan (>= 1 denial).
  4. conftest    - the policy allows the known-good plan (0 denials).

Conftest exits non-zero whenever there is a denial, so exit code alone cannot
tell a passing run from a failing one. Denials are counted from `--output json`.

Stdlib only: json + shutil + subprocess + tempfile. opa and conftest are
expected on PATH.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


class ValidatorError(RuntimeError):
    """Raised when a required external tool is missing from PATH."""


@dataclass
class GateResult:
    """Outcome of running the gates. `feedback` is fed back into the next prompt."""

    passed: bool = True
    failures: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.passed = False
        self.failures.append(message)

    @property
    def feedback(self) -> str:
        return "\n\n".join(self.failures)


def _require(tool: str) -> None:
    if shutil.which(tool) is None:
        raise ValidatorError(
            f"{tool} not found on PATH. Install it and ensure `{tool}` is callable."
        )


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True)


def opa_parse(rego_path: Path) -> tuple[bool, str]:
    """Gate 1: `opa parse` accepts the file."""
    _require("opa")
    proc = _run(["opa", "parse", str(rego_path)])
    if proc.returncode != 0:
        return False, (proc.stderr.strip() or proc.stdout.strip())
    return True, ""


def opa_check(rego_path: Path) -> tuple[bool, str]:
    """Gate 2: `opa check` compiles the file."""
    _require("opa")
    proc = _run(["opa", "check", str(rego_path)])
    if proc.returncode != 0:
        return False, (proc.stderr.strip() or proc.stdout.strip())
    return True, ""


def conftest_denials(rego_path: Path, plan_json: Path) -> tuple[int, str]:
    """Run conftest and count denials from JSON output.

    Returns (denial_count, raw_output). A count of -1 means the JSON output
    could not be parsed at all (a conftest invocation error, not a verdict).
    """
    _require("conftest")
    proc = _run(
        [
            "conftest",
            "test",
            str(plan_json),
            "--policy",
            str(rego_path.parent),
            "--output",
            "json",
            "--no-color",
        ]
    )
    try:
        results = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return -1, (proc.stderr.strip() or proc.stdout.strip())

    count = 0
    for result in results:
        count += len(result.get("failures") or [])
    return count, proc.stdout


def run_gates(rego_text: str, bad_json: Path, good_json: Path) -> GateResult:
    """Run all four gates against `rego_text` and return the aggregated result."""
    result = GateResult()
    with tempfile.TemporaryDirectory(prefix="tpcompile-gate-") as tmp:
        rego_path = Path(tmp) / "policy.rego"
        rego_path.write_text(rego_text, encoding="utf-8")

        ok, err = opa_parse(rego_path)
        if not ok:
            result.fail(f"Gate 1 (opa parse) failed:\n{err}")
            return result

        ok, err = opa_check(rego_path)
        if not ok:
            result.fail(f"Gate 2 (opa check) failed:\n{err}")
            return result

        bad_count, bad_out = conftest_denials(rego_path, bad_json)
        if bad_count < 1:
            result.fail(
                "Gate 3 (deny known-bad plan) failed: expected at least 1 denial on "
                f"{bad_json.name}, got {max(bad_count, 0)}.\n{bad_out}"
            )

        good_count, good_out = conftest_denials(rego_path, good_json)
        if good_count != 0:
            result.fail(
                "Gate 4 (allow known-good plan) failed: expected 0 denials on "
                f"{good_json.name}, got {good_count}.\n{good_out}"
            )

    return result
