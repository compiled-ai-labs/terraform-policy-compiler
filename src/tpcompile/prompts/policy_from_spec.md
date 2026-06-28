You are compiling a Terraform policy into a Conftest/OPA Rego rule. You are given
a plain-English policy description and two Terraform plan JSON documents: one that
MUST be denied and one that MUST pass. Write a single Rego policy that denies the
first and allows the second.

## Rego v1 + Conftest primer

Conftest evaluates `deny` rules in `package main` against the input document and
reports each produced message as a failure. Write Rego v1: `import rego.v1`, use
`deny contains msg if { ... }`, and iterate with `some x in collection`. A
Terraform plan's resources are under `input.resource_changes`, each with a
`type`, an `address`, and a `change.after` object holding the planned attributes.
Build one message per offending resource and bind it with `:=`. Example:

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

## Policy

{{POLICY_MD}}

## Terraform plan JSON — MUST_DENY

This plan violates the policy. Your rule MUST produce at least one denial for it.

```json
{{BAD_PLAN_JSON}}
```

## Terraform plan JSON — MUST_PASS

This plan complies with the policy. Your rule MUST produce zero denials for it.

```json
{{GOOD_PLAN_JSON}}
```

## Constraints

- Package must be `package main`.
- Use Rego v1 syntax (`import rego.v1`).
- Output only the Rego policy. No commentary, no explanation, no markdown fences.
- Match on resource attributes present in the plan JSON above, not on assumptions.

{{RETRY_FEEDBACK}}
