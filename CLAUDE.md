# CLAUDE.md

This repo follows the **Compiled AI** paradigm. The LLM runs at compile time to produce a deterministic artifact. The runtime tool consumes that artifact without any model in the path.

See the `compiled-ai` skill for the full paradigm and conventions. If the skill is not loaded, treat this file as the authoritative reference.

## This repo

- **One-liner:** Compile written security/governance standards into Conftest/OPA Rego policies, gate-verified against Terraform plan fixtures.
- **Spec folder:** `policies/`
- **Compiler entry:** `uv run tpcompile build ./policies`
- **Artifact folder:** `rego/`
- **Runtime tool:** `conftest` (against `terraform show -json` output)

## The pattern (always)

1. **Spec** — each `policies/<id>/` holds `source.md` (a prose standard, the primary input) plus `bad.tf` and `good.tf` fixtures. Source of truth. Human-maintained.
2. **Compiler** — `src/tpcompile/compiler.py`. Calls LLM with a templated prompt. Runs offline.
3. **Validation gates** — `src/tpcompile/validator.py`. Non-negotiable. Parse, check, functional verdict on known plans.
4. **Artifact** — committed file. Reviewable like any code. Versioned. Pinned by consumers.
5. **Runtime** — boring deterministic tool. Consumes the artifact. No LLM.

## Validation discipline

The LLM does not get its output committed unless an external validator agrees the artifact does what it claims. No exceptions.

- `opa parse` first. If it does not parse, retry with the parse error fed back into the prompt.
- `opa check` next. Types and references must resolve.
- Then `conftest test` against the known-bad plan. The policy MUST report at least one denial.
- Then `conftest test` against the known-good plan. The policy MUST report zero denials.
- Maximum 3 retries with feedback. After that, surface to human and write nothing.

## What this repo is NOT

This repo does not contain runtime AI. There is no LLM call in any code path triggered by user actions or policy evaluation. If a contributor proposes one, push back and point them at the Compiled AI thesis.

## Voice and style

- Terse, technical. No marketing language. No AI markers. No emoji.
- Sentence case in all docs and commit messages.
- Pushback expected when responses over-explain or drift from the actual question.

## Workflow commands

- `/new-spec <name>` — scaffold a new spec entry in `policies/`.
- `/compile` — run the compile loop locally.
- `/verify` — run gates on all existing committed artifacts.
- `/check-pattern` — audit this repo for drift from the five-part shape.

## Locked decisions

- License: Apache 2.0.
- LLM: Anthropic SDK direct. Model `claude-opus-4-8`, override via `TPCOMPILE_MODEL`.
- Python: 3.11+, uv for package management.
- Tests: pytest. Lint: ruff.
- External binaries required at compile and verify time: `terraform` >= 1.6, `opa` >= 1.0, `conftest` >= 0.50.
- Rego target syntax: v1.
- CI: GitHub Actions. Two workflows: `compile.yml` (manual dispatch, opens PR with regenerated artifacts) and `verify.yml` (every PR, runs gates on committed artifacts).
