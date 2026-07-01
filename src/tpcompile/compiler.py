"""The compile loop: prose standard in, gate-verified Rego out.

The primary input is `source.md` — a prose excerpt from a security or governance
standard. `bad.tf`/`good.tf` are demoted to validation fixtures: two concrete
cases the compiled policy must get right. The policy must enforce the general
standard in the prose, not merely deny the specific resource in the bad fixture.

For each policy folder the compiler produces plan JSON from the fixtures, renders
the prompt with the prose plus both plans, calls the model, and runs the gates. On
failure it feeds the exact validator error back into the next prompt and retries,
up to three attempts. Rego is written only when every gate passes.

If the model judges the standard genuinely unexpressible against Terraform plan
JSON, it returns the `UNEXPRESSIBLE:` sentinel; the compiler skips the gates,
writes nothing, and records the reason as a skip rather than a hard failure.

The model is a direct Anthropic SDK call. No model abstraction, no retry
library. Model id comes from TPCOMPILE_MODEL, defaulting to the strongest
available model because compile time is cheap and correctness is not.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import anthropic

from . import planner, validator

MODEL = os.environ.get("TPCOMPILE_MODEL", "claude-opus-4-8")
MAX_TOKENS = 2048
MAX_ATTEMPTS = 3
UNEXPRESSIBLE = "UNEXPRESSIBLE:"

_PROMPT_TEMPLATE = (Path(__file__).parent / "prompts" / "policy_from_source.md").read_text(
    encoding="utf-8"
)


@dataclass
class PolicyResult:
    policy_id: str
    ok: bool
    attempts: int
    rego: str | None = None
    failure: str | None = None
    skipped: bool = False
    reason: str | None = None


def _read_source(policy_dir: Path) -> str:
    return (policy_dir / "source.md").read_text(encoding="utf-8").strip()


def _render_prompt(source: str, bad_json: str, good_json: str, feedback: str | None) -> str:
    if feedback:
        retry = (
            "## Previous attempt failed validation\n\n"
            "Your previous output did not pass the gates. Output corrected Rego only. "
            "The exact validator error was:\n\n```\n" + feedback + "\n```\n"
        )
    else:
        retry = ""
    return (
        _PROMPT_TEMPLATE.replace("{{SOURCE}}", source)
        .replace("{{BAD_PLAN_JSON}}", bad_json)
        .replace("{{GOOD_PLAN_JSON}}", good_json)
        .replace("{{RETRY_FEEDBACK}}", retry)
    )


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def _unexpressible_reason(text: str) -> str | None:
    """Return the reason if the model refused with the UNEXPRESSIBLE sentinel."""
    stripped = text.strip()
    if not stripped:
        return None
    first = stripped.splitlines()[0].strip()
    if first.startswith(UNEXPRESSIBLE):
        return first[len(UNEXPRESSIBLE) :].strip()
    return None


def _call_llm(client: anthropic.Anthropic, prompt: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in message.content if block.type == "text")
    return _strip_fences(text)


def compile_policy(
    policy_dir: Path, provider_tf: Path, rego_dir: Path, cache_dir: Path
) -> PolicyResult:
    policy_id = policy_dir.name
    source = _read_source(policy_dir)

    plan_paths = planner.plan_policy(policy_dir, provider_tf, cache_dir)
    bad_json = plan_paths["bad"].read_text(encoding="utf-8")
    good_json = plan_paths["good"].read_text(encoding="utf-8")

    client = anthropic.Anthropic()
    feedback: str | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = _render_prompt(source, bad_json, good_json, feedback)
        output = _call_llm(client, prompt)

        reason = _unexpressible_reason(output)
        if reason is not None:
            return PolicyResult(policy_id, ok=False, attempts=attempt, skipped=True, reason=reason)

        gate = validator.run_gates(output, plan_paths["bad"], plan_paths["good"])
        if gate.passed:
            rego_dir.mkdir(parents=True, exist_ok=True)
            (rego_dir / f"{policy_id}.rego").write_text(output.rstrip() + "\n", encoding="utf-8")
            return PolicyResult(policy_id, ok=True, attempts=attempt, rego=output)
        feedback = gate.feedback

    return PolicyResult(policy_id, ok=False, attempts=MAX_ATTEMPTS, failure=feedback)


def compile_all(
    spec_dir: Path, rego_dir: Path, cache_dir: Path = planner.CACHE_DIR
) -> list[PolicyResult]:
    spec_dir = Path(spec_dir)
    provider_tf = spec_dir / "provider.tf"
    results: list[PolicyResult] = []
    for policy_dir in sorted(p for p in spec_dir.iterdir() if p.is_dir()):
        if not (policy_dir / "source.md").is_file():
            continue
        results.append(compile_policy(policy_dir, provider_tf, Path(rego_dir), cache_dir))
    return results
