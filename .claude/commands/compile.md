---
description: Run the compile loop over policies/. Shows the diff. Does not commit.
---

Run `uv run tpcompile build ./policies`.

This needs terraform, opa, and conftest on PATH, and `ANTHROPIC_API_KEY` set. For
each policy folder the compiler generates plan JSON, drafts a Rego rule, and runs
the gates, retrying up to three times with validator feedback.

After it finishes, show the diff under `rego/` and report which policies passed
and which failed. Do not commit. Leave the artifacts for the user to review.
