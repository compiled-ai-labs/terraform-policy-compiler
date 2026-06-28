---
description: Scaffold a new policy spec folder. Does not invoke the compiler.
---

Create a new policy entry under `policies/`.

Argument: a policy name. Derive the id as `NNN-slug`, where `NNN` is the next
unused three-digit number and `slug` is the kebab-case name.

Create `policies/<id>/` with three files:

- `policy.md` — 3-6 lines, plain English: the rule and its rationale.
- `bad.tf` — minimal Terraform that violates the rule, under 15 lines. No provider
  block (it is shared at `policies/provider.tf`).
- `good.tf` — minimal Terraform that complies, under 15 lines. No provider block.

Do not run the compiler. Do not write any `rego/` artifact. Stop after creating
the three files and report the id.
