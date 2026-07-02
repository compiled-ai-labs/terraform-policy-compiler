package main

import rego.v1

# Resource types that do not support tags and should be exempted.
# Only taggable resources are in scope per the standard.
non_taggable(t) if {
	non_taggable_types[t]
}

non_taggable_types := {
	"aws_iam_policy_attachment",
	"aws_iam_role_policy_attachment",
	"aws_iam_user_policy_attachment",
	"aws_iam_group_policy_attachment",
	"aws_route",
	"aws_route_table_association",
	"aws_security_group_rule",
	"aws_vpc_security_group_ingress_rule",
	"aws_vpc_security_group_egress_rule",
	"aws_network_acl_rule",
	"aws_iam_role_policy",
	"aws_iam_user_policy",
	"aws_iam_group_policy",
	"aws_lb_target_group_attachment",
	"aws_autoscaling_attachment",
	"aws_volume_attachment",
	"aws_ebs_snapshot_copy",
}

# Consider only managed resources being created or updated (not deleted).
in_scope(rc) if {
	rc.mode == "managed"
	startswith(rc.provider_name, "registry.terraform.io/hashicorp/aws")
	not non_taggable(rc.type)
	some action in rc.change.actions
	action in {"create", "update"}
}

tags(rc) := t if {
	t := rc.change.after.tags
	is_object(t)
}

tags(rc) := {} if {
	not is_object(rc.change.after.tags)
}

valid_tag(t, key) if {
	v := t[key]
	is_string(v)
	trim_space(v) != ""
}

deny contains msg if {
	some rc in input.resource_changes
	in_scope(rc)
	t := tags(rc)
	not valid_tag(t, "owner")
	msg := sprintf("%s is missing a non-empty 'owner' tag", [rc.address])
}

deny contains msg if {
	some rc in input.resource_changes
	in_scope(rc)
	t := tags(rc)
	not valid_tag(t, "cost-center")
	msg := sprintf("%s is missing a non-empty 'cost-center' tag", [rc.address])
}
