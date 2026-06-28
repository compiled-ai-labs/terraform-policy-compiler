---
description: Run the gates on committed rego/ artifacts. Read-only.
---

Verify every committed artifact against its spec, the same checks `verify.yml`
runs in CI.

For each `rego/<id>.rego`:

1. Confirm a matching `policies/<id>/` exists with `policy.md`, `bad.tf`, `good.tf`
   (and the reverse: every policy folder has a matching rego). If `rego/` is empty,
   there is nothing to verify — stop.
2. Regenerate plan JSON with `uv run tpcompile plan <id>`.
3. Run `conftest test` on the bad plan (expect >= 1 denial) and the good plan
   (expect 0), counting denials from `--output json`.

Report pass/fail per policy. Do not modify any files.
