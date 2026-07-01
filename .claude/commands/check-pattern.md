---
description: Audit the repo for drift from the five-part Compiled AI shape.
---

Check that this repo still follows the five-part shape and report any drift. Do
not fix anything — report only.

1. **Spec** — `policies/<id>/` each has `source.md` (the prose standard), `bad.tf`,
   `good.tf`, and none carry a provider block; `policies/provider.tf` exists.
2. **Compiler** — `src/tpcompile/compiler.py` runs offline, calls the model
   directly, and retries with gate feedback (max three attempts).
3. **Gates** — `src/tpcompile/validator.py` enforces parse, check, deny-bad,
   allow-good. Flag any weakening of the gates.
4. **Artifact** — `rego/<id>.rego` exists for every policy and vice versa (unless
   `rego/` is empty). Flag any spec changed without a recompile.
5. **Runtime** — Conftest/OPA only; no model call in the verify path.

Also confirm both workflows exist (`compile.yml` dispatch-only, `verify.yml` on PR)
and that no marketing language or emoji crept into the docs.
