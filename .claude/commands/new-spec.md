---
description: Scaffold a new policy spec folder. Does not invoke the compiler.
---

Create a new policy entry under `policies/`.

Argument: a policy name. Derive the id as `NNN-slug`, where `NNN` is the next
unused three-digit number and `slug` is the kebab-case name.

Create `policies/<id>/` with three files:

- `source.md` — the prose standard, the primary input: an excerpt from a security
  or governance standard stating the control in general terms. This is what the
  compiled policy must enforce; the fixtures below only check its edges.
- `bad.tf` — a fixture that must be denied. Minimal Terraform, under 15 lines. No
  provider block (it is shared at `policies/provider.tf`).
- `good.tf` — a fixture that must pass. Minimal Terraform, under 15 lines. No
  provider block.

The fixtures are two concrete cases, not the whole standard — make sure they match
the pattern the prose describes. Do not run the compiler. Do not write any `rego/`
artifact. Stop after creating the three files and report the id.
