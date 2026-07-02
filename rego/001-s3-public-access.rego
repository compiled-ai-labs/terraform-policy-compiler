package main

import rego.v1

# Collect all public access blocks that are fully enabled, keyed by the bucket
# they protect (via reference in configuration).

# Determine whether a given public access block resource has all four settings true.
pab_fully_enabled(rc) if {
	rc.change.after.block_public_acls == true
	rc.change.after.ignore_public_acls == true
	rc.change.after.block_public_policy == true
	rc.change.after.restrict_public_buckets == true
}

# Set of bucket addresses that have a corresponding, fully-enabled public access block.
protected_buckets contains bucket_addr if {
	some cfg in input.configuration.root_module.resources
	cfg.type == "aws_s3_bucket_public_access_block"

	# Find the matching resource_change for this public access block.
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket_public_access_block"
	rc.address == cfg.address
	pab_fully_enabled(rc)

	# Extract the bucket reference from the config.
	some ref in cfg.expressions.bucket.references
	bucket_addr := ref
}

# Helper: does a config reference string point at a given bucket address?
references_bucket(bucket_address) if {
	some ref in protected_buckets
	startswith(ref, bucket_address)
}

# A bucket is compliant if some fully-enabled public access block references it.
bucket_protected(bucket_address) if {
	references_bucket(bucket_address)
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket"

	# skip buckets being destroyed only
	rc.change.after != null

	not bucket_protected(rc.address)
	msg := sprintf("%s has no corresponding fully-enabled aws_s3_bucket_public_access_block (all four public access settings must be true)", [rc.address])
}

# Also deny any public access block that exists but is not fully enabled.
deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket_public_access_block"
	rc.change.after != null
	not pab_fully_enabled(rc)
	msg := sprintf("%s does not set all four public access block settings to true", [rc.address])
}
