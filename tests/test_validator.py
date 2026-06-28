"""Gate tests for validator.run_gates.

Each gate gets one passing case and one failing case, exercised with real opa and
conftest binaries. The plan JSON here is hand-written to the shape that
`terraform show -json` emits (resources under `resource_changes` with a
`change.after` object), so the tests do not need terraform to run.
"""

from __future__ import annotations

import json
import shutil

import pytest

from tpcompile import validator

pytestmark = pytest.mark.skipif(
    shutil.which("opa") is None or shutil.which("conftest") is None,
    reason="requires opa and conftest on PATH",
)


def _plan(acl: str) -> dict:
    return {
        "format_version": "1.2",
        "resource_changes": [
            {
                "address": "aws_s3_bucket_acl.data",
                "type": "aws_s3_bucket_acl",
                "name": "data",
                "change": {"actions": ["create"], "after": {"acl": acl}},
            }
        ],
    }


@pytest.fixture
def bad_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(_plan("public-read")), encoding="utf-8")
    return path


@pytest.fixture
def good_json(tmp_path):
    path = tmp_path / "good.json"
    path.write_text(json.dumps(_plan("private")), encoding="utf-8")
    return path


# A correct policy: denies the public ACL, allows the private one.
PASSING = """\
package main

import rego.v1

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket_acl"
	rc.change.after.acl == "public-read"
	msg := sprintf("%s is public", [rc.address])
}
"""

# Gate 1: unterminated rule body — opa parse rejects it.
GATE1_FAIL = """\
package main

import rego.v1

deny contains msg if {
	msg := "broken"
"""

# Gate 2: parses, but `unbound` is an unsafe variable — opa check rejects it.
GATE2_FAIL = """\
package main

import rego.v1

deny contains msg if {
	msg := unbound
}
"""

# Gate 3: compiles, but never matches the bad plan — zero denials where >=1 is required.
GATE3_FAIL = """\
package main

import rego.v1

deny contains msg if {
	some rc in input.resource_changes
	rc.change.after.acl == "this-value-never-appears"
	msg := sprintf("%s is public", [rc.address])
}
"""

# Gate 4: denies every bucket ACL, so the good plan is denied too.
GATE4_FAIL = """\
package main

import rego.v1

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket_acl"
	msg := sprintf("%s has an ACL", [rc.address])
}
"""


def test_all_gates_pass(bad_json, good_json):
    result = validator.run_gates(PASSING, bad_json, good_json)
    assert result.passed, result.feedback


def test_gate1_parse_failure(bad_json, good_json):
    result = validator.run_gates(GATE1_FAIL, bad_json, good_json)
    assert not result.passed
    assert "Gate 1" in result.feedback


def test_gate2_check_failure(bad_json, good_json):
    result = validator.run_gates(GATE2_FAIL, bad_json, good_json)
    assert not result.passed
    assert "Gate 2" in result.feedback


def test_gate3_bad_not_denied(bad_json, good_json):
    result = validator.run_gates(GATE3_FAIL, bad_json, good_json)
    assert not result.passed
    assert "Gate 3" in result.feedback


def test_gate4_good_denied(bad_json, good_json):
    result = validator.run_gates(GATE4_FAIL, bad_json, good_json)
    assert not result.passed
    assert "Gate 4" in result.feedback
