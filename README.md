# terraform-policy-compiler

Compile a plain-English Terraform policy into a Conftest/OPA Rego rule. An LLM
drafts the rule at compile time from a bad/good plan pair; validation gates prove
the rule denies the bad plan and passes the good one before it is committed. The
runtime is Conftest against `terraform show -json` output — no model in the path.

## Why

LLMs are good at drafting a Rego rule from an example and bad at being trusted
with it. A rule that looks right but matches the wrong attribute, or denies
nothing, or denies everything, is worse than no rule. So the model never gets its
output committed on trust: every candidate is run against a known-bad Terraform
plan (must deny) and a known-good plan (must pass), using the same Conftest the
runtime uses. Only rules that clear the gates land in `rego/`. This is the
Compiled AI pattern — an LLM authors the artifact at compile time, the runtime
stays deterministic. See the article "Compiled AI: Engineering Deterministic LLM
Systems" ([Medium](https://medium.com/@boristeplitsky)) and arXiv:2604.05150.

## The five-part flow

1. **Spec** — `policies/<id>/`: a `policy.md` plus a `bad.tf` that violates it and
   a `good.tf` that complies. The shared provider lives in `policies/provider.tf`.
2. **Compiler** — `src/tpcompile/compiler.py`: renders the prompt, calls the model,
   runs the gates, retries up to three times with the validator error fed back in.
3. **Validation gates** — `src/tpcompile/validator.py`: `opa parse`, `opa check`,
   then Conftest must deny the bad plan and pass the good plan.
4. **Artifact** — `rego/<id>.rego`: the committed, reviewable policy.
5. **Runtime** — Conftest evaluating the artifact against `terraform show -json`
   output. Deterministic, auditable, no inference.

## Try it

```
export ANTHROPIC_API_KEY=sk-...
uv sync
uv run tpcompile build ./policies
```

Compiling needs terraform, opa, and conftest on PATH. Running the tests needs opa
and conftest but no API key.

## Worked example

`policies/001-no-public-s3/` says every S3 bucket must have a matching
`aws_s3_bucket_public_access_block` with all four block flags set to `true`.
`bad.tf` declares a bucket with no access block; `good.tf` declares the bucket and
a fully-configured block. The planner runs `terraform plan` on each and caches the
JSON to `.compile-cache/`. The model drafts a Rego rule that denies a bucket whose
plan has no fully-blocked access block. The gates confirm the rule fires on
`bad.tf`'s plan and stays silent on `good.tf`'s. The result is written to
`rego/001-no-public-s3.rego`.

## Limitations (v0.1)

- AWS only, and the seed policies match single representative resource types
  (S3 ACL, RDS instance, EC2 tags) rather than every taggable or encryptable kind.
- Plans are generated with fake credentials and `-backend=false`; resources whose
  planned values depend on real API reads will not be fully populated.
- One artifact per policy folder. No cross-resource or module-aware policies.
- The gates prove behavior on the supplied bad/good plans only. A policy is as
  good as its examples.

## Roadmap

- More providers (GCP, Azure) behind the same gate discipline.
- Richer bad/good sets per policy, including multiple offending resource types.
- Policy bundles and namespaces for grouping related rules.
- Autofix suggestions emitted alongside denials.

## Related work

- **redhat-et/gatekeeper-policy-generator** — generates Gatekeeper policies for
  Kubernetes via curated templates plus Claude Code orchestration. This repo
  targets Terraform plans and uses example-driven generation with four-gate
  validation rather than curated templates.
- **aatakansalar/yaml-opa-llm-guardrails** — compiles a YAML DSL into Rego for LLM
  output guardrails. Same compile-to-Rego shape, different domain (IaC vs LLM I/O)
  and different input (bad/good plans vs a YAML DSL).
- **ARPaCCino** (arXiv:2507.10584, July 2025) — agentic RAG generating Rego from
  natural language with human-in-the-loop validation. A research artifact; this is
  a CLI you clone and run.
- **Apple Prose2Policy** — natural language to Rego for access policies with
  auto-generated tests. Different policy domain (access control vs IaC).
- **OPA community issue #8426** — OPA maintainers acknowledging LLM-Rego
  hallucination problems in the 2025 community survey. Direct evidence that the
  validation-gates approach this repo demonstrates is the right answer.

## Collaborate

Three ways in:

- **Use it** — open an issue with a Terraform pattern you want compiled.
- **Extend it** — send a PR for a new provider, policy, or gate.
- **Build the next compiler** — pick another runtime (GitHub Actions, Dependabot,
  CODEOWNERS) and apply the same shape.

Contact: compiledailabs@gmail.com.

## License

Apache 2.0.
