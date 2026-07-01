# terraform-policy-compiler

Compile a written standard — an excerpt from a security or governance policy —
into a Conftest/OPA Rego rule. The prose is the primary input: an LLM reads it at
compile time and drafts a rule that enforces it, while a bad/good Terraform plan
pair serves as validation fixtures. The gates prove the rule denies the bad plan
and passes the good one before it is committed. The runtime is Conftest against
`terraform show -json` output — no model in the path.

## Why

A standard is written prose: "no S3 bucket may be public," with the scope and the
exceptions spelled out in paragraphs. Turning that into an enforceable Rego rule
is exactly the step that cannot be done deterministically — and it is the step you
least want a model doing live in CI. So it happens once, at compile time, behind
gates. The prose is the primary input; the model drafts a rule that enforces it;
two Terraform plan fixtures — one that must be denied, one that must pass — prove
the rule before it lands in `rego/`. The fixtures only check the edges: the rule
must generalise to the standard's full scope, not overfit the one resource in the
bad plan. The prose is authoritative and slow-moving, the fixtures are an
independent check, and the committed artifact is plain Rego that Conftest runs with
no model in the path. This is the Compiled AI pattern — an LLM authors the artifact
at compile time, the runtime stays deterministic. See the article "Compiled AI:
Engineering Deterministic LLM Systems"
([Medium](https://medium.com/@boristeplitsky)) and arXiv:2604.05150.

## The five-part flow

1. **Spec** — `policies/<id>/`: a `source.md` prose standard (the primary input),
   plus `bad.tf` and `good.tf` fixtures — one that must be denied, one that must
   pass. The shared provider lives in `policies/provider.tf`.
2. **Compiler** — `src/tpcompile/compiler.py`: renders the prompt from the prose and
   both plans, calls the model, runs the gates, retries up to three times with the
   validator error fed back in.
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

`policies/001-s3-public-access/source.md` is an excerpt of a cloud security
standard: every S3 bucket must have public access fully blocked, meaning an
`aws_s3_bucket_public_access_block` with all four settings set to `true`. `bad.tf`
declares a bucket with no access block; `good.tf` declares the bucket and a
fully-configured block. The planner runs `terraform plan` on each and caches the
JSON to `.compile-cache/`. The model reads the standard and drafts a Rego rule that
enforces it, using the two plans to check its edges. The gates confirm the rule
denies `bad.tf`'s plan and passes `good.tf`'s. The result is written to
`rego/001-s3-public-access.rego`.

## Limitations (v0.1)

- AWS only. The seed standards cover S3 public access, RDS encryption, and
  resource tagging.
- Plans are generated with fake credentials and `-backend=false`; resources whose
  planned values depend on real API reads will not be fully populated.
- One artifact per policy folder. No cross-resource or module-aware policies.
- Fixtures are not held out. The gates prove the policy denies the bad plan and
  passes the good one, but a policy can clear both while under-enforcing the
  standard's wider scope. Human review of policy against standard is expected.
- Some standards may be unexpressible against plan JSON (for example, controls that
  need runtime state Conftest never sees). Those are skipped, not compiled.

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
