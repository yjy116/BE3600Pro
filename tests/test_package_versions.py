"""Verify pinned package versions through the real firmware acceptance CLI."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROFILE = "xiaomi_be3600-pro-wired-p8"
PREFIX = f"openwrt-qualcommbe-ipq53xx-{PROFILE}"
TIMEOUT_SECONDS = 10
EXPECTED_VERSIONS = {
    "daed": "2026.09.24-r2",
    "luci-app-daede": "1.15-r6",
    "luci-theme-aurora": "1.4.0-r20260920",
    "luci-app-aurora-config": "1.2.5-r20260920",
}
OTHER_PACKAGES = {
    name: "1.0-r1" for name in (
        "luci", "luci-app-tmi-poe", "luci-i18n-tmi-poe-zh-cn",
        "kmod-dsa-rtl837x", "luci-app-gecoosac", "gecoosac",
    )
}


class PackageVersionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.versions = ROOT / "Config" / "package-versions.json"
        self.requested = self.directory / "plugins.config"
        self.requested.write_text("CONFIG_PACKAGE_luci=y\n", encoding="utf-8")
        for suffix in ("sysupgrade.bin", "factory.ubi"):
            (self.directory / f"{PREFIX}-squashfs-{suffix}").write_bytes(b"firmware fixture")
        (self.directory / "profiles.json").write_text(json.dumps({"profiles": {PROFILE: {}}}))

    def manifest(self, versions, *, extra=""):
        packages = OTHER_PACKAGES | versions
        records = "".join(f"{name} - {version}\n" for name, version in packages.items())
        (self.directory / f"{PREFIX}.manifest").write_text(records + extra, encoding="utf-8")
        sums = []
        for path in sorted(self.directory.iterdir()):
            if path.name != "sha256sums":
                sums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n")
        (self.directory / "sha256sums").write_text("".join(sums), encoding="utf-8")

    def invoke(self):
        return subprocess.run([
            sys.executable, str(ROOT / "scripts" / "verify_build.py"), "firmware",
            "--directory", str(self.directory), "--requested", str(self.requested),
            "--versions", str(self.versions),
        ], capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)

    def assert_rejected(self, result, detail):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("Build verification failed:", result.stderr)
        self.assertIn(detail, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_accepts_exact_daed_and_aurora_versions(self):
        self.manifest(EXPECTED_VERSIONS)
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("4 package versions verified", result.stdout)

    def test_rejects_old_daed_or_aurora_version(self):
        for package in EXPECTED_VERSIONS:
            with self.subTest(package=package):
                self.manifest(EXPECTED_VERSIONS | {package: "1.27.0-r1"})
                result = self.invoke()
                self.assert_rejected(result, package)
                self.assertIn("expected " + EXPECTED_VERSIONS[package], result.stderr)
                self.assertIn("got 1.27.0-r1", result.stderr)

    def test_requires_versioned_package_even_when_not_in_requested_config(self):
        for missing in EXPECTED_VERSIONS:
            with self.subTest(missing=missing):
                retained = {name: version for name, version in EXPECTED_VERSIONS.items()
                            if name != missing}
                self.manifest(retained)
                self.assert_rejected(self.invoke(), missing)

    def test_rejects_manifest_record_without_version(self):
        self.manifest(EXPECTED_VERSIONS | {"daed": ""})
        self.assert_rejected(self.invoke(), "Malformed manifest")

    def test_rejects_standalone_dae_and_legacy_daed_ui(self):
        for package in ("dae", "luci-app-dae", "luci-app-daed"):
            with self.subTest(package=package):
                self.manifest(EXPECTED_VERSIONS | {package: "1.0-r1"})
                self.assert_rejected(self.invoke(), "Excluded DAE or legacy DAED packages: " + package)

    def test_rejects_duplicate_manifest_package_versions(self):
        self.manifest(EXPECTED_VERSIONS, extra="daed - 1.27.0-r1\n")
        self.assert_rejected(self.invoke(), "Duplicate manifest package: daed")

    def test_rejects_missing_or_invalid_version_value(self):
        for invalid in (None, "", " ", 211, "2.1.1 r1"):
            with self.subTest(invalid=invalid):
                self.versions = self.directory / "package-versions.json"
                self.versions.write_text(json.dumps(EXPECTED_VERSIONS | {"daed": invalid}))
                self.manifest(EXPECTED_VERSIONS)
                self.assert_rejected(self.invoke(), "Invalid package version for daed")

    def test_rejects_empty_or_malformed_versions_map(self):
        for invalid in ("{}", "[]", "null", '{"daed":'):
            with self.subTest(invalid=invalid):
                self.versions = self.directory / "package-versions.json"
                self.versions.write_text(invalid, encoding="utf-8")
                self.manifest(EXPECTED_VERSIONS)
                self.assert_rejected(self.invoke(), "package-versions.json")

    def test_rejects_duplicate_version_requirement(self):
        self.versions = self.directory / "package-versions.json"
        self.versions.write_text('{"daed":"1.27.0-r1","daed":"2.1.1-r1"}')
        self.manifest(EXPECTED_VERSIONS)
        self.assert_rejected(self.invoke(), "Duplicate package-version key: daed")

    def test_rejects_missing_versions_file(self):
        self.versions = self.directory / "absent-versions.json"
        self.manifest(EXPECTED_VERSIONS)
        self.assert_rejected(self.invoke(), "absent-versions.json")


if __name__ == "__main__":
    unittest.main()
