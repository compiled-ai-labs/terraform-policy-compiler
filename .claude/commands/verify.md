---
description: Run the gates on committed rego/ artifacts. Read-only.
---

Verify every committed artifact against its spec, the same checks `verify.yml`
runs in CI:

```
uv run tpcompile verify ./policies
```

This checks spec/artifact drift in both directions (every `rego/<id>.rego` has a
matching `policies/<id>/` with `source.md`, `bad.tf`, `good.tf`, and vice versa),
regenerates plan JSON from the fixtures, and re-runs the four gates on the
committed Rego. Empty `rego/` is a clean exit. Needs terraform, opa, and conftest
on PATH; no API key.

Report pass/fail per policy. Do not modify any files.
