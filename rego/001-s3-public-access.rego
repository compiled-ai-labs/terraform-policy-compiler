package main

import rego.v1

# Match a public access block to a bucket by its bucket reference.
pab_matches_bucket(pab, bucket) if {
	some ref in pab.change.after.bucket_refs
	ref == bucket.address
}

# Collect bucket addresses referenced by each public access block via configuration.
pab_bucket_refs(pab_address) := refs if {
	some rc in input.configuration.root_module.resources
	rc.type == "aws_s3_bucket_public_access_block"
	rc.address == pab_address
	refs := {b |
		some r in rc.expressions.bucket.references
		b := r
	}
}

# Determine whether a fully-enabled public access block exists for a given bucket.
fully_enabled_pab_for_bucket(bucket_address) if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket_public_access_block"
	after := rc.change.after
	after.block_public_acls == true
	after.ignore_public_acls == true
	after.block_public_policy == true
	after.restrict_public_buckets == true
	refs := pab_bucket_refs(rc.address)
	some ref in refs
	ref == bucket_address
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket"
	not rc.change.actions == ["delete"]
	not fully_enabled_pab_for_bucket(rc.address)
	msg := sprintf("%s has no corresponding fully-enabled aws_s3_bucket_public_access_block (all four settings must be true)", [rc.address])
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket_public_access_block"
	after := rc.change.after
	settings := {
		"block_public_acls": after.block_public_acls,
		"ignore_public_acls": after.ignore_public_acls,
		"block_public_policy": after.block_public_policy,
		"restrict_public_buckets": after.restrict_public_buckets,
	}
	some name, val in settings
	val != true
	msg := sprintf("%s does not set %s to true", [rc.address, name])
}
