package main

import rego.v1

# Resource types that do not support tags and should be exempt from this control.
non_taggable := {
	"aws_iam_role_policy_attachment",
	"aws_iam_policy_attachment",
	"aws_iam_role_policy",
	"aws_iam_user_policy",
	"aws_iam_group_policy",
	"aws_route",
	"aws_route_table_association",
	"aws_security_group_rule",
	"aws_lb_listener_certificate",
	"aws_volume_attachment",
	"aws_network_interface_attachment",
	"aws_iam_instance_profile",
}

# A resource change is in scope if it is a managed resource being created or
# updated, is not explicitly non-taggable, and its planned attributes carry a
# "tags" field (which is how Terraform surfaces taggable resources).
in_scope(rc) if {
	rc.mode == "managed"
	not non_taggable[rc.type]
	some action in rc.change.actions
	action in {"create", "update"}
	rc.change.after.tags != null
}

tag_value(rc, key) := v if {
	v := rc.change.after.tags[key]
}

missing_owner(rc) if {
	not tag_value(rc, "owner")
}

missing_owner(rc) if {
	tag_value(rc, "owner") == ""
}

missing_cost_center(rc) if {
	not tag_value(rc, "cost-center")
}

missing_cost_center(rc) if {
	tag_value(rc, "cost-center") == ""
}

deny contains msg if {
	some rc in input.resource_changes
	in_scope(rc)
	missing_owner(rc)
	msg := sprintf("%s is missing a non-empty 'owner' tag", [rc.address])
}

deny contains msg if {
	some rc in input.resource_changes
	in_scope(rc)
	missing_cost_center(rc)
	msg := sprintf("%s is missing a non-empty 'cost-center' tag", [rc.address])
}
