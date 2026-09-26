"""Exercise the build acceptance CLI with real temporary build outputs."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_build.py"
PROFILE = "xiaomi_be3600-pro-wired-p8"
DEVICE = f"CONFIG_TARGET_qualcommbe_ipq53xx_DEVICE_{PROFILE}=y\n"
PREFIX = f"openwrt-qualcommbe-ipq53xx-{PROFILE}"
TIMEOUT_SECONDS = 10
BASELINE = "CONFIG_PACKAGE_luci=y\nCONFIG_PACKAGE_tc-tiny=y\n"
REQUESTED = ("CONFIG_PACKAGE_luci-app-passwall=y\nCONFIG_PACKAGE_ddns-scripts=y\n"
             "CONFIG_PACKAGE_dae=y\nCONFIG_PACKAGE_daed=y\nCONFIG_PACKAGE_luci-app-daede=y\n"
             "CONFIG_PACKAGE_flock=y\n")
CRITICAL_PACKAGES = (
    "luci-app-tmi-poe", "luci-i18n-tmi-poe-zh-cn", "kmod-dsa-rtl837x",
    "luci-app-gecoosac", "gecoosac",
)
CRITICAL_CONFIG = "".join(f"CONFIG_PACKAGE_{name}=y\n" for name in CRITICAL_PACKAGES)
VALID_CONFIG = DEVICE + BASELINE + REQUESTED + CRITICAL_CONFIG
PACKAGES = ("luci-app-passwall", "ddns-scripts", "dae", "daed", "luci-app-daede",
            "flock", *CRITICAL_PACKAGES)


class BuildVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.requested = self.write("plugins.config", REQUESTED)

    def write(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def invoke(self, arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, arguments)],
            capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False,
        )

    def config(self, actual, *, baseline=BASELINE, features=None):
        arguments = [
            "config", "--baseline", self.write("baseline.config", baseline),
            "--actual", self.write("actual.config", actual),
            "--requested", self.requested,
        ]
        if features is not None:
            arguments.extend(["--features", self.write("features.config", features)])
        return self.invoke(arguments)

    def assert_rejected(self, result, detail):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(detail, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_config_preserves_baseline_and_adds_requested(self):
        result = self.config(VALID_CONFIG)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_config_ignores_modules_and_passwall_feature_switches(self):
        options = (
            "CONFIG_PACKAGE_luci-app-passwall_INCLUDE_Haproxy=y\n"
            "CONFIG_PACKAGE_luci-app-passwall_Nftables_Transparent_Proxy=y\n"
            "CONFIG_PACKAGE_luci-app-daede_daed=y\n"
            "CONFIG_PACKAGE_optional-module=m\n"
        )
        self.write("plugins.config", REQUESTED + options)
        result = self.config(VALID_CONFIG, baseline=BASELINE + options)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_config_rejects_legacy_dae_and_daed_ui(self):
        for package in ("luci-app-dae", "luci-app-daed"):
            with self.subTest(package=package):
                result = self.config(VALID_CONFIG + f"CONFIG_PACKAGE_{package}=y\n")
                self.assert_rejected(result, "Excluded legacy DAE/DAED interfaces: " + package)

    def test_config_requires_both_backends_and_unified_ui(self):
        for package in ("dae", "daed", "luci-app-daede", "flock"):
            with self.subTest(package=package):
                result = self.config(VALID_CONFIG.replace(f"CONFIG_PACKAGE_{package}=y\n", ""))
                self.assert_rejected(result, "Requested configuration: missing packages: " + package)

    def test_config_rejects_lost_default_even_when_replaced(self):
        result = self.config(VALID_CONFIG.replace("tc-tiny=y", "tc-full=y"))
        self.assert_rejected(result, "tc-tiny")

    def test_config_rejects_requested_package_changed_to_module(self):
        result = self.config(VALID_CONFIG.replace("passwall=y", "passwall=m"))
        self.assert_rejected(result, "luci-app-passwall")

    def test_config_requires_exact_target_profile(self):
        result = self.config(VALID_CONFIG.replace("wired-p8", "wired-p7"))
        self.assert_rejected(result, PROFILE)

    def test_config_rejects_additional_device(self):
        result = self.config(VALID_CONFIG +
                             "CONFIG_TARGET_qualcommbe_ipq53xx_DEVICE_other-router=y\n")
        self.assert_rejected(result, "other-router")

    def test_config_reports_missing_input_without_traceback(self):
        actual = self.write("actual.config", VALID_CONFIG)
        result = self.invoke(["config", "--baseline", self.root / "absent",
                              "--actual", actual, "--requested", self.requested])
        self.assert_rejected(result, "absent")

    def test_config_verifies_enabled_and_disabled_feature_options(self):
        features = ("CONFIG_KERNEL_DEBUG_INFO_BTF=y\n"
                    "# CONFIG_KERNEL_DEBUG_INFO_REDUCED is not set\n"
                    "CONFIG_PACKAGE_luci-app-passwall_INCLUDE_Xray=y\n")
        result = self.config(VALID_CONFIG + features, features=features)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_config_rejects_missing_required_btf(self):
        result = self.config(VALID_CONFIG,
                             features="CONFIG_KERNEL_DEBUG_INFO_BTF=y\n")
        self.assert_rejected(result, "CONFIG_KERNEL_DEBUG_INFO_BTF")

    def test_config_rejects_feature_with_wrong_boolean_value(self):
        options = (
            ("CONFIG_KERNEL_DEBUG_INFO_REDUCED=y\n",
             "# CONFIG_KERNEL_DEBUG_INFO_REDUCED is not set\n"),
            ("# CONFIG_PACKAGE_luci-app-passwall_INCLUDE_Xray is not set\n",
             "CONFIG_PACKAGE_luci-app-passwall_INCLUDE_Xray=y\n"),
        )
        for actual, expected in options:
            with self.subTest(expected=expected):
                result = self.config(VALID_CONFIG + actual, features=expected)
                self.assert_rejected(result, "Feature")

    def test_config_requires_critical_packages_even_when_baseline_omits_them(self):
        for missing in CRITICAL_PACKAGES:
            with self.subTest(missing=missing):
                actual = VALID_CONFIG.replace(f"CONFIG_PACKAGE_{missing}=y\n", "")
                result = self.config(actual)
                self.assert_rejected(result, missing)
                self.assertIn("Critical configuration", result.stderr)

    def create_firmware(self):
        directory = self.root / "firmware"
        directory.mkdir(exist_ok=True)
        files = {
            f"{PREFIX}-squashfs-sysupgrade.bin": b"sysupgrade payload",
            f"{PREFIX}-squashfs-factory.ubi": b"factory payload",
            f"{PREFIX}.manifest": self.manifest_text(PACKAGES).encode(),
            "profiles.json": json.dumps({"profiles": {PROFILE: {"images": []}}}).encode(),
        }
        for name, content in files.items():
            (directory / name).write_bytes(content)
        self.write_checksums(directory)
        return directory

    def manifest_text(self, packages):
        return "".join(f"{package} - 1.0-r1\n" for package in packages)

    def write_checksums(self, directory):
        lines = []
        for path in sorted(directory.iterdir()):
            if path.name != "sha256sums":
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                lines.append(f"{digest}  {path.name}\n")
        (directory / "sha256sums").write_text("".join(lines), encoding="utf-8")

    def firmware(self, directory):
        return self.invoke(["firmware", "--directory", directory,
                            "--requested", self.requested])

    def test_firmware_accepts_complete_verified_output(self):
        result = self.firmware(self.create_firmware())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_firmware_requires_both_images_and_metadata(self):
        names = (
            f"{PREFIX}-squashfs-sysupgrade.bin", f"{PREFIX}-squashfs-factory.ubi",
            f"{PREFIX}.manifest", "profiles.json", "sha256sums",
        )
        for name in names:
            with self.subTest(name=name):
                directory = self.create_firmware()
                (directory / name).unlink()
                result = self.firmware(directory)
                self.assert_rejected(result, name.rsplit(".", 1)[-1])

    def test_firmware_rejects_manifest_from_other_device(self):
        directory = self.create_firmware()
        (directory / f"{PREFIX}.manifest").rename(directory / "another-router.manifest")
        self.write_checksums(directory)
        self.assert_rejected(self.firmware(directory), "manifest")

    def test_firmware_requires_requested_and_critical_packages(self):
        for missing in PACKAGES:
            with self.subTest(missing=missing):
                directory = self.create_firmware()
                retained = [package for package in PACKAGES if package != missing]
                (directory / f"{PREFIX}.manifest").write_text(self.manifest_text(retained))
                self.write_checksums(directory)
                self.assert_rejected(self.firmware(directory), missing)

    def test_firmware_rejects_malformed_manifest(self):
        directory = self.create_firmware()
        (directory / f"{PREFIX}.manifest").write_text("not a package record\n")
        self.write_checksums(directory)
        self.assert_rejected(self.firmware(directory), "manifest")

    def test_firmware_rejects_wrong_profile_and_broken_json(self):
        for content in ('{"profiles":{"another-router":{}}}', '{"profiles":', '[]'):
            with self.subTest(content=content):
                directory = self.create_firmware()
                (directory / "profiles.json").write_text(content)
                self.write_checksums(directory)
                self.assert_rejected(self.firmware(directory), "profiles.json")

    def test_firmware_rejects_corruption_in_any_checksummed_file(self):
        directory = self.create_firmware()
        other = directory / "buildinfo.txt"
        other.write_bytes(b"original")
        self.write_checksums(directory)
        other.write_bytes(b"corrupt")
        self.assert_rejected(self.firmware(directory), "buildinfo.txt")

    def test_firmware_rejects_malformed_or_empty_checksums(self):
        for content in ("invalid digest  file\n", ""):
            with self.subTest(content=content):
                directory = self.create_firmware()
                (directory / "sha256sums").write_text(content)
                self.assert_rejected(self.firmware(directory), "sha256sums")

    def test_firmware_rejects_checksum_path_escape(self):
        for name in ("../outside", "..\\outside", "/outside", "C:\\outside"):
            with self.subTest(name=name):
                directory = self.create_firmware()
                sums = directory / "sha256sums"
                sums.write_text(sums.read_text() + f"{'0' * 64}  {name}\n")
                self.assert_rejected(self.firmware(directory), "path")

    def test_firmware_accepts_current_directory_checksum_paths(self):
        directory = self.create_firmware()
        sums = directory / "sha256sums"
        sums.write_text(sums.read_text().replace("  ", " *./"))
        result = self.firmware(directory)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_firmware_rejects_missing_checksummed_file(self):
        directory = self.create_firmware()
        sums = directory / "sha256sums"
        sums.write_text(sums.read_text() + f"{'0' * 64}  missing.bin\n")
        self.assert_rejected(self.firmware(directory), "missing.bin")

    def test_firmware_requires_checksums_for_images_and_manifest(self):
        names = (
            f"{PREFIX}-squashfs-sysupgrade.bin", f"{PREFIX}-squashfs-factory.ubi",
            f"{PREFIX}.manifest",
        )
        for name in names:
            with self.subTest(name=name):
                directory = self.create_firmware()
                sums = directory / "sha256sums"
                retained = [line for line in sums.read_text().splitlines() if name not in line]
                sums.write_text("\n".join(retained) + "\n")
                self.assert_rejected(self.firmware(directory), name)

    def test_firmware_rejects_empty_image(self):
        directory = self.create_firmware()
        image = directory / f"{PREFIX}-squashfs-factory.ubi"
        image.write_bytes(b"")
        self.write_checksums(directory)
        self.assert_rejected(self.firmware(directory), "factory.ubi")


if __name__ == "__main__":
    unittest.main()
