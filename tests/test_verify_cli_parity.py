"""Keep provenance differences separate from doctor protocol regressions."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "verify_cli_parity", Path(__file__).resolve().parents[1] / "scripts/verify-cli-parity.py"
)
parity = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(parity)


def doctor():
    detail = {
        "cliPath": "/pip/bin/python",
        "cliEntrypoint": "/pip/bin/aisc",
        "cliVersion": "0.1.10.dev0",
        "bundlePath": "/shared/bundle",
        "bundleVersion": "0.1.10.dev0",
        "manifestSchema": 1,
        "compatibleCliVersions": ["0.1.10.dev0"],
        "status": "pass",
        "reason": "manifest-allows-running-cli",
    }
    return {
        "meta": {"protocol": parity.PROTOCOL, "command": "doctor", "exit_code": 0},
        "data": {"host": {"checks": [{
            "name": "cli-bundle-pairing", "status": "pass", "detail": json.dumps(detail)
        }]}},
        "errors": [],
    }


def check(env):
    return env["data"]["host"]["checks"][0]


def edit_detail(env, **changes):
    detail = json.loads(check(env)["detail"])
    detail.update(changes)
    check(env)["detail"] = json.dumps(detail)


def compare(a, b):
    return parity._compare(
        "doctor --format json",
        subprocess.CompletedProcess([], 0, json.dumps(a), ""),
        subprocess.CompletedProcess([], 0, json.dumps(b), ""),
        None, True,
    )


def test_doctor_accepts_pip_and_frozen_executable_provenance():
    a = doctor()
    b = copy.deepcopy(a)
    edit_detail(b, cliPath="/dist/aisc", cliEntrypoint="/dist/aisc")
    assert compare(a, b) is None


@pytest.mark.parametrize("field,value", [
    ("bundlePath", "/wrong/bundle"), ("bundleVersion", "0.1.9"),
    ("cliVersion", "0.1.9"), ("manifestSchema", 2),
    ("compatibleCliVersions", ["0.1.9"]), ("status", "fail"),
    ("reason", "version-mismatch"),
])
def test_doctor_retains_pairing_semantic_differences(field, value):
    a = doctor()
    b = copy.deepcopy(a)
    edit_detail(b, **{field: value})
    assert compare(a, b) is not None


@pytest.mark.parametrize("field", ["cliPath", "cliEntrypoint"])
@pytest.mark.parametrize("value", [None, "", " ", 123, [], {}])
def test_doctor_does_not_mask_invalid_provenance(field, value):
    a = doctor()
    b = copy.deepcopy(a)
    edit_detail(b, **{field: value})
    assert compare(a, b) is not None


@pytest.mark.parametrize("field", ["cliPath", "cliEntrypoint"])
def test_doctor_retains_missing_provenance(field):
    a = doctor()
    b = copy.deepcopy(a)
    detail = json.loads(check(b)["detail"])
    del detail[field]
    check(b)["detail"] = json.dumps(detail)
    assert compare(a, b) is not None


@pytest.mark.parametrize("raw", ["not json", "[]", "null"])
def test_doctor_retains_malformed_pairing_details(raw):
    a = doctor()
    b = copy.deepcopy(a)
    check(b)["detail"] = raw
    assert compare(a, b) is not None


def test_other_commands_and_checks_do_not_mask_provenance():
    for command, name in [("version", "cli-bundle-pairing"), ("doctor", "other-check")]:
        a = doctor()
        a["meta"]["command"] = command
        check(a)["name"] = name
        b = copy.deepcopy(a)
        edit_detail(b, cliPath="/different")
        assert compare(a, b) is not None


def test_doctor_retains_outer_check_status_and_missing_detail():
    for change in ("status", "detail"):
        a = doctor()
        b = copy.deepcopy(a)
        if change == "status":
            check(b)["status"] = "fail"
        else:
            del check(b)["detail"]
        assert compare(a, b) is not None
