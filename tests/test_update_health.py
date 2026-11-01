"""Pairing diagnostics describe the running process, never a guessed install."""
import json
from pathlib import Path

import pytest

from aisc.application.update_health import pairing_check, pairing_health
from aisc.application.bundle_fetch import bundle_compatible
from aisc.application.doctor import run_doctor


def bundle(tmp_path, manifest=None, version="0.1.10.dev0"):
    (tmp_path / "VERSION").write_text(version, encoding="utf-8")
    if manifest is not None:
        (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def test_reports_actual_process_and_compatible_bundle(tmp_path):
    root = bundle(tmp_path, {"schema_version": 1, "compatible_cli_versions": ["0.1.10.dev0"]})
    report = pairing_health(root, cli_version="0.1.10.dev0", executable="C:/安装/aisc.exe")
    assert report["status"] == "compatible"
    assert report["cliPath"] == "C:/安装/aisc.exe"
    assert report["cliVersion"] == "0.1.10.dev0"
    assert report["bundlePath"] == str(root.resolve())
    assert report["bundleVersion"] == "0.1.10.dev0"
    assert report["manifestSchema"] == 1
    assert report["compatibleCliVersions"] == ["0.1.10.dev0"]


def test_compatibility_uses_manifest_allowlist_not_version_equality(tmp_path):
    root = bundle(tmp_path, {"schema_version": 1, "compatible_cli_versions": ["0.1.9"]})
    assert pairing_health(root, cli_version="0.1.9")["status"] == "compatible"
    report = pairing_health(root, cli_version="0.1.10.dev0")
    assert report["status"] == "incompatible"
    assert "0.1.9" in report["reason"]


@pytest.mark.parametrize("manifest", [None, [], "invalid", 1, {"schema_version": 2}, {"schema_version": 1, "compatible_cli_versions": "0.1.10.dev0"}])
def test_missing_or_malformed_manifest_fails_closed(tmp_path, manifest):
    root = bundle(tmp_path, manifest)
    report = pairing_health(root, cli_version="0.1.10.dev0")
    assert report["status"] == "incompatible"
    assert report["reason"]
    ok, reason = bundle_compatible(root, "0.1.10.dev0")
    assert not ok and reason


@pytest.mark.parametrize("schema", [True, 1.0], ids=["boolean", "float"])
def test_manifest_schema_must_be_exact_integer_one(tmp_path, schema):
    root = bundle(tmp_path, {
        "schema_version": schema,
        "compatible_cli_versions": ["0.1.10.dev0"],
    })
    ok, reason = bundle_compatible(root, "0.1.10.dev0")
    assert not ok and "schema_version" in reason
    report = pairing_health(root, cli_version="0.1.10.dev0")
    assert report["status"] == "incompatible"
    assert report["manifestSchema"] is None


def test_corrupt_manifest_does_not_break_doctor(tmp_path):
    root = bundle(tmp_path)
    (root / "manifest.json").write_bytes(b"\xffbroken")
    assert pairing_health(root)["status"] == "incompatible"


def test_missing_bundle_and_unknown_version_cannot_report_healthy(tmp_path):
    assert pairing_health(None)["status"] == "unknown"
    root = bundle(tmp_path, {"schema_version": 1, "compatible_cli_versions": [""]})
    assert pairing_health(root, cli_version="")["status"] == "unknown"
    (root / "VERSION").unlink()
    assert pairing_health(root)["status"] == "unknown"


@pytest.mark.parametrize("value", ["0+unknown", "unknown", " UNKNOWN ", "not-a-version", "0.1.10\ntoken=bad", "0.1.10."])
@pytest.mark.parametrize("field", ["cli", "bundle"])
def test_unknown_or_invalid_version_fact_cannot_report_compatible(tmp_path, field, value):
    cli_version = value if field == "cli" else "0.1.10.dev0"
    bundle_version = value if field == "bundle" else "0.1.10.dev0"
    root = bundle(tmp_path, {
        "schema_version": 1,
        "compatible_cli_versions": [cli_version],
    }, version=bundle_version)
    report = pairing_health(root, cli_version=cli_version)
    assert report["status"] == "unknown"
    assert report["reason"] == "version-unknown"
    if field == "bundle":
        assert pairing_check(root).status == "warn"


@pytest.mark.parametrize("version", [
    "0.1.10.dev0", "0.1.10.dev3+gabc123", "0.1.10rc1.dev2",
    "1!0.1.10.post1.dev2+build.7",
])
def test_valid_pep440_dev_versions_remain_compatible(tmp_path, version):
    root = bundle(tmp_path, {
        "schema_version": 1,
        "compatible_cli_versions": [version],
    }, version=version)
    report = pairing_health(root, cli_version=version)
    assert report["status"] == "compatible"
    assert report["cliVersion"] == report["bundleVersion"] == version


def test_source_checkout_without_published_manifest_is_explicitly_unknown(tmp_path):
    (tmp_path / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    root = bundle(tmp_path)
    report = pairing_health(root)
    assert report["status"] == "unknown"
    assert report["reason"] == "source-checkout-without-release-manifest"


def test_check_adds_allowlisted_json_detail_and_doctor_wires_it(tmp_path, monkeypatch):
    root = bundle(tmp_path, {"schema_version": 1, "compatible_cli_versions": ["0.1.10"], "token": "never-copy-this"})
    check = pairing_check(root)
    assert check.name == "cli-bundle-pairing" and check.status == "pass"
    assert "never-copy-this" not in check.detail
    monkeypatch.setattr("aisc.application.doctor._check_channel_confusion", lambda: check)
    report = run_doctor(root=root, which=lambda _: None)
    assert sum(c.name == "cli-bundle-pairing" for c in report.checks) == 2
