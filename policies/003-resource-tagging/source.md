---
type: governance-standard
source: Cloud Governance Standard, section 1.2 "Resource ownership"
---

# Every resource must declare an owner and a cost centre

Every provisioned resource must carry two tags: `owner` and `cost-center`. The owner tag identifies the team accountable for the resource. The cost-center tag maps spend to a budget line. Without both, we cannot attribute cost, we cannot find who to contact when a resource misbehaves, and we cannot clean up orphaned infrastructure with any confidence.

This is a governance control rather than a security control, but we enforce it the same way, because retrofitting tags across an existing estate is painful and never gets prioritised. Enforcing at provisioning keeps the estate clean by construction.

Any taggable resource declared without both an `owner` tag and a `cost-center` tag is a violation. A resource that carries only one of the two is still a violation. The values must be non-empty; a tag that is present but set to an empty string does not satisfy the control.
