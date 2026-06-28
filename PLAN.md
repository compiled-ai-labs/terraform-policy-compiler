# Terraform Policy Compiler — Build Plan

Second reference implementation of the Compiled AI paradigm. The LLM runs at compile time to produce Conftest/OPA Rego policies; Conftest runs deterministically at runtime against `terraform plan` JSON, with no model in the path.

Same five-part shape as `semgrep-rule-compiler`. Different runtime tool, different artifact format, identical discipline.

## Scope (v0.1)

Take a folder of policies (each with a description, a Terraform file that should violate the policy, and one that should comply), emit Rego policies that deny the bad plan and pass the good plan.

Out of scope for v0.1:

- Sentinel, Kyverno, Checkov custom checks, or any non-OPA target
- Cloud providers other than AWS
- Multi-resource policies (each seed policy concerns one resource type)
- Plan analysis beyond `resource_changes` (no `prior_state`, no `output_changes`)
- SaaS, API, or UI — CLI only
- Model abstraction layer — direct Anthropic SDK call

## Directory layout

```
terraform-policy-compiler/
├── README.md
├── LICENSE                                  Apache 2.0
├── PLAN.md                                  this file
├── CLAUDE.md                                repo memory (from template)
├── pyproject.toml                           uv-managed
├── .github/
│   └── workflows/
│       ├── compile.yml                      runs tpcompile, opens PR
│       └── verify.yml                       runs conftest on bad/good plans
├── .claude/
│   └── commands/                            (from template, four files)
├── src/
│   └── tpcompile/
│       ├── __init__.py
│       ├── cli.py                           `tpcompile build ./policies`
│       ├── compiler.py                      prompt + LLM call + retry loop
│       ├── planner.py                       terraform init+plan, returns JSON
│       ├── validator.py                     opa+conftest invocation, gate checks
│       └── prompts/
│           └── policy_from_spec.md
├── policies/                                the spec
│   ├── provider.tf                          shared fake-credentials AWS provider
│   ├── 001-no-public-s3/
│   │   ├── policy.md
│   │   ├── bad.tf
│   │   └── good.tf
│   ├── 002-rds-encryption-required/
│   │   ├── policy.md
│   │   ├── bad.tf
│   │   └── good.tf
│   └── 003-required-tags/
│       ├── policy.md
│       ├── bad.tf
│       └── good.tf
├── rego/                                    the artifact
│   ├── 001-no-public-s3.rego
│   ├── 002-rds-encryption-required.rego
│   └── 003-required-tags.rego
└── tests/
    └── test_validator.py
```

`policies/` is the spec. `rego/` is the artifact. Both committed. Reviewer sees the input next to the output.

## The shared provider

`policies/provider.tf` configures the AWS provider with fake credentials and skips all validation, so `terraform plan` produces JSON without contacting AWS:

```hcl
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "fake"
  secret_key                  = "fake"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
}
```

The compiler combines `policies/provider.tf` with each policy's `bad.tf` or `good.tf` in a temp directory before running `terraform plan`.

## The compile loop

```
for each policy_dir in policies/:
    spec = read policy.md, bad.tf, good.tf
    bad_plan_json = run_terraform_plan(provider.tf + bad.tf)        cached
    good_plan_json = run_terraform_plan(provider.tf + good.tf)      cached

    for attempt in 1..3:
        prompt = render(policy_from_spec.md, spec, bad_plan_json, good_plan_json, prior_failure=feedback)
        rego_source = call_anthropic(prompt)

        gate_1 = opa_parse(rego_source)                              valid Rego v1 syntax
        gate_2 = opa_check(rego_source)                              type/reference checks pass
        gate_3 = conftest_test(rego_source, bad_plan_json)           MUST report at least one denial
        gate_4 = conftest_test(rego_source, good_plan_json)          MUST report zero denials

        if all passed:
            write rego/<id>.rego
            break
        else:
            feedback = format_failures(gate_results)

    if still failing after 3 attempts:
        surface to human, write nothing, exit non-zero
```

`planner.py` handles the terraform invocation: creates a temp dir, copies `provider.tf` plus the target `.tf`, runs `terraform init -input=false -backend=false` then `terraform plan -out=plan.bin -input=false` then `terraform show -json plan.bin`. Plan JSON is cached on disk in `.compile-cache/<id>-{bad,good}.json` so retries skip the terraform re-run.

## Validation gates (non-negotiable)

1. `opa parse` accepts the Rego source.
2. `opa check` succeeds (types and references resolve).
3. `conftest test --policy <generated> <bad_plan.json>` reports ≥ 1 denial.
4. `conftest test --policy <generated> <good_plan.json>` reports 0 denials.

The LLM does not get its output committed unless OPA and Conftest both agree the policy does what it claims.

## Prompt template

Lives at `src/tpcompile/prompts/policy_from_spec.md`. Reviewable separately. Carries:

- Concise description of Rego v1 syntax with one canonical Conftest `deny` rule example for Terraform plans.
- The policy description verbatim from `policy.md`.
- The full `bad_plan.json` labeled `MUST_DENY`.
- The full `good_plan.json` labeled `MUST_PASS`.
- Constraint: output only Rego, `package main`, Rego v1 syntax, no commentary, no code fences.
- On retry: prior attempt plus the exact validator error.

## Seed policies (v0.1)

1. **001-no-public-s3** — `aws_s3_bucket` is non-compliant if it lacks a corresponding `aws_s3_bucket_public_access_block` with all four block flags set to `true`. `bad.tf` declares a bucket without the access block; `good.tf` declares both resources properly configured.
2. **002-rds-encryption-required** — `aws_db_instance` must have `storage_encrypted = true`. `bad.tf` omits it; `good.tf` sets it.
3. **003-required-tags** — every taggable resource must have both `owner` and `cost-center` tags. `bad.tf` declares a resource with only `Name`; `good.tf` includes all three.

These are placeholders. Swap in real policies from HIPAA/Shamash/Merlin work when ready.

## Locked decisions

- License: Apache 2.0.
- LLM: Anthropic SDK direct. Model: `claude-opus-4-8`, override via `TPCOMPILE_MODEL`.
- Python: 3.11+. Package manager: uv. Tests: pytest. Lint: ruff.
- External binaries required at compile and verify time: `terraform` ≥ 1.6, `opa` ≥ 1.0, `conftest` ≥ 0.50.
- Rego target syntax: v1.

## Meta-verification

`.github/workflows/verify.yml` runs the four gates against every committed `rego/<id>.rego` paired with its spec's `bad.tf` and `good.tf`. It installs `terraform`, `opa`, and `conftest`, regenerates plan JSON from the `.tf` files (no cache in CI), and asserts:

- Each `rego/` file has a matching `policies/<id>/` directory and vice versa (bidirectional drift detection).
- Each policy still denies its `bad.tf` and passes its `good.tf`.

If `rego/` is empty, the workflow exits cleanly. Once any rule exists, missing or extra rules fail CI.

## Related work

The README's `Related work` section cites and differentiates from:

- **redhat-et/gatekeeper-policy-generator** — generates Gatekeeper policies for Kubernetes via curated templates plus Claude Code orchestration. This repo targets Terraform plans and uses example-driven generation with four-gate validation rather than curated templates.
- **aatakansalar/yaml-opa-llm-guardrails** — compiles a YAML DSL into Rego for LLM output guardrails. Same compile-to-Rego shape, different domain (IaC vs LLM I/O) and different input (incidents vs YAML DSL).
- **ARPaCCino** (arXiv 2507.10584, July 2025) — agentic RAG generating Rego from NL with human-in-the-loop validation. Research artifact; this is a CLI you clone and run.
- **Apple Prose2Policy** — NL → Rego for access policies with auto-generated tests. Different policy domain (access control vs IaC).
- **OPA community issue #8426** — OPA maintainers acknowledging LLM-Rego hallucination problems in the 2025 community survey. Direct evidence that the validation-gates approach this repo demonstrates is the right answer.

## Distribution

- README per the structure used in `semgrep-rule-compiler` plus the `Related work` section above.
- Cross-link from the Compiled AI Medium series.
- Update `compiled-ai-labs/.github/profile/README.md` to list this repo as the second reference implementation.
- r/Terraform and r/devops posts framed around the "Rego tax" tailwind, without naming Compiled AI prematurely — lead with the mechanism.
- HN Show HN now becomes viable: two reference implementations of one paradigm, not a single tool.
