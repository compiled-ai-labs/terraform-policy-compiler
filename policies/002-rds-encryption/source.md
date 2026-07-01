---
type: security-standard
source: Cloud Security Standard, section 3.4 "Encryption at rest"
---

# Managed databases must encrypt data at rest

All persistent data stores must be encrypted at rest. For relational databases on AWS this means every `aws_db_instance` and every `aws_rds_cluster` has storage encryption enabled. Encryption at rest is a baseline requirement in every compliance regime we operate under, and there is no performance justification for omitting it on the instance classes we use.

The setting is not on by default for every engine and instance combination, and it cannot be changed in place after the database is created. Enabling it later requires taking a snapshot and restoring into a new encrypted instance, which for a production database means downtime and risk. For that reason the control is enforced at provisioning. A database created without encryption is expensive to fix later, so it must never be created that way in the first place.

A relational database resource that does not set storage encryption to true is a violation. Where the data classification requires a customer-managed key, the absence of a key reference is also a violation, but the baseline control this section defines is simply that encryption is enabled.
