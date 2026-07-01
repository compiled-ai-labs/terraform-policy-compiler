You are compiling a written standard into a Conftest/OPA Rego policy. You are
given a prose standard (SOURCE) and two Terraform plan JSON documents: one that
MUST be denied and one that MUST pass. Write a single Rego policy that enforces
the standard, using the two plans only to check the edges.

## Rego v1 + Conftest primer

Conftest evaluates `deny` rules in `package main` against the input document and
reports each produced message as a failure. Write Rego v1: `import rego.v1`, use
`deny contains msg if { ... }`, and iterate with `some x in collection`. A
Terraform plan produced by `terraform show -json` holds its resources under
`input.resource_changes`, each with a `type`, an `address`, and a `change.after`
object holding the planned attributes. Build one message per offending resource
and bind it with `:=`. Example:

```rego
package main

import rego.v1

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket_public_access_block"
	rc.change.after.block_public_acls == false
	msg := sprintf("%s does not block public ACLs", [rc.address])
}
```

## SOURCE

This is the standard. It states the control in general terms. Your policy must
enforce the general intent of this text, not just the one resource that happens to
appear in MUST_DENY. Read its stated scope carefully — which resource types it
covers, what counts as a violation, and any exceptions.

{{SOURCE}}

## Terraform plan JSON — MUST_DENY

This plan violates the standard. Your policy MUST produce at least one denial for
it.

```json
{{BAD_PLAN_JSON}}
```

## Terraform plan JSON — MUST_PASS

This plan complies with the standard. Your policy MUST produce zero denials for
it.

```json
{{GOOD_PLAN_JSON}}
```

## Instructions

- Write a Rego policy in `package main` that enforces the general standard in
  SOURCE. Cover every resource type and condition the standard names, not only the
  resource that appears in MUST_DENY.
- Use the two plans to check your edges: the policy must deny MUST_DENY and pass
  MUST_PASS. But a policy that only denies the specific resource in MUST_DENY,
  while ignoring the standard's stated scope, is wrong.
- Use Rego v1 syntax (`import rego.v1`).
- Output only the Rego policy. No commentary, no explanation, no markdown fences.

## If the standard cannot be expressed

If the standard in SOURCE genuinely cannot be enforced against `terraform show
-json` plan output with Conftest — for example it requires runtime state that
Conftest never sees — do not guess. Output exactly one line and nothing else:

```
UNEXPRESSIBLE: <short reason>
```

{{RETRY_FEEDBACK}}
