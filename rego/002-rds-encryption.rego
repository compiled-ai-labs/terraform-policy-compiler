package main

import rego.v1

db_types := {"aws_db_instance", "aws_rds_cluster"}

deny contains msg if {
	some rc in input.resource_changes
	db_types[rc.type]
	rc.change.after.storage_encrypted != true
	msg := sprintf("%s does not enable storage encryption at rest", [rc.address])
}
