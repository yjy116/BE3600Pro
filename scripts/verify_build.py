#!/usr/bin/env python3
"""Fail explicitly when configuration or BE3600 Pro p8 build evidence is incomplete."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


PROFILE = "xiaomi_be3600-pro-wired-p8"
DEVICE_SYMBOL = f"CONFIG_TARGET_qualcommbe_ipq53xx_DEVICE_{PROFILE}"
PACKAGE_PATTERN = re.compile(r"CONFIG_PACKAGE_([A-Za-z0-9][A-Za-z0-9+_.-]*)=y")
BOOLEAN_PATTERN = re.compile(r"(CONFIG_[A-Za-z0-9_+.-]+)=([ymn])")
DISABLED_PATTERN = re.compile(r"# (CONFIG_[A-Za-z0-9_+.-]+) is not set")
CHECKSUM_PATTERN = re.compile(r"([a-fA-F0-9]{64}) [ *](.+)")
MANIFEST_PATTERN = re.compile(r"([A-Za-z0-9][A-Za-z0-9+_.-]*)\s+-\s+\S.*")
CRITICAL_PACKAGES = frozenset({
    "luci-app-tmi-poe", "luci-i18n-tmi-poe-zh-cn", "kmod-dsa-rtl837x",
    "luci-app-gecoosac", "gecoosac",
})
HASH_CHUNK_BYTES = 1024 * 1024
FAILURE_EXIT_CODE = 1


def text_lines(path):
    return Path(path).read_text(encoding="utf-8-sig").splitlines()


def selected_packages(path):
    matches = (PACKAGE_PATTERN.fullmatch(line.strip()) for line in text_lines(path))
    # PassWall suboptions configure a package; they are not package names.
    return frozenset(match.group(1) for match in matches
                     if match and "_INCLUDE_" not in match.group(1)
                     and not match.group(1).startswith("luci-app-passwall_"))


def require_packages(expected, actual, context):
    missing = expected - actual
    if missing:
        raise ValueError(f"{context}: missing packages: {', '.join(sorted(missing))}")


def boolean_options(path):
    options = {}
    for line in text_lines(path):
        enabled = BOOLEAN_PATTERN.fullmatch(line.strip())
        disabled = DISABLED_PATTERN.fullmatch(line.strip())
        if enabled:
            options[enabled.group(1)] = enabled.group(2)
        elif disabled:
            options[disabled.group(1)] = "n"
    return options


def verify_features(requested_path, actual_path):
    expected = boolean_options(requested_path)
    actual = boolean_options(actual_path)
    mismatches = tuple(f"{key}: expected {value}, got {actual.get(key, '(missing)')}"
                       for key, value in expected.items() if actual.get(key) != value)
    if mismatches:
        raise ValueError("Feature configuration mismatch: " + "; ".join(mismatches))


def verify_config(arguments):
    selected = frozenset(line.strip().removesuffix("=y")
                         for line in text_lines(arguments.actual)
                         if line.strip().endswith("=y"))
    devices = frozenset(symbol for symbol in selected
                        if symbol.startswith("CONFIG_TARGET_") and "_DEVICE_" in symbol)
    if devices != {DEVICE_SYMBOL}:
        raise ValueError(f"Expected only device {DEVICE_SYMBOL}; selected: "
                         f"{', '.join(sorted(devices)) or '(none)'}")
    actual = selected_packages(arguments.actual)
    baseline = selected_packages(arguments.baseline)
    requested = selected_packages(arguments.requested)
    require_packages(baseline, actual, "Baseline preservation")
    require_packages(requested, actual, "Requested configuration")
    require_packages(CRITICAL_PACKAGES, actual, "Critical configuration")
    if arguments.features is not None:
        verify_features(arguments.features, arguments.actual)
    print(f"Configuration verified: {len(baseline)} baseline packages retained; "
          f"{len(requested)} requested packages selected; "
          f"{len(CRITICAL_PACKAGES)} critical packages selected; device {PROFILE}.")


def require_artifacts(directory, suffix):
    artifacts = tuple(sorted(directory.glob(f"*{PROFILE}*{suffix}")))
    if not artifacts:
        raise ValueError(f"Missing {PROFILE} artifact ending in {suffix}")
    for path in artifacts:
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Empty or invalid artifact: {path.name}")
    return artifacts


def verify_profile(directory):
    path = directory / "profiles.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid profiles.json: {error}") from error
    profiles = data.get("profiles") if isinstance(data, dict) else None
    if not isinstance(profiles, dict) or not isinstance(profiles.get(PROFILE), dict):
        raise ValueError(f"profiles.json does not contain profile {PROFILE}")


def safe_checksum_path(directory, name):
    relative = PurePosixPath(name)
    if (len(relative.parts) != 1 or relative.name == ".."
            or any(character in name for character in "\\:")):
        raise ValueError(f"Unsafe sha256sums path: {name}")
    path = directory / relative.name
    if path.resolve().parent != directory.resolve():
        raise ValueError(f"sha256sums path escapes firmware directory: {name}")
    if not path.is_file():
        raise ValueError(f"Missing sha256sums file: {name}")
    return path


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksums(directory):
    lines = text_lines(directory / "sha256sums")
    if not lines:
        raise ValueError("sha256sums is empty")
    verified = set()
    for number, line in enumerate(lines, start=1):
        match = CHECKSUM_PATTERN.fullmatch(line)
        if not match:
            raise ValueError(f"Malformed sha256sums record at line {number}")
        expected, name = match.groups()
        path = safe_checksum_path(directory, name)
        actual = file_sha256(path)
        if actual != expected.lower():
            raise ValueError(f"SHA-256 mismatch for {name}: expected {expected}, got {actual}")
        verified.add(path.name)
    return frozenset(verified)


def manifest_packages(path):
    packages = set()
    for number, line in enumerate(text_lines(path), start=1):
        if not line.strip():
            continue
        match = MANIFEST_PATTERN.fullmatch(line.strip())
        if not match:
            raise ValueError(f"Malformed manifest {path.name} at line {number}")
        packages.add(match.group(1))
    return frozenset(packages)


def verify_firmware(arguments):
    directory = arguments.directory
    sysupgrade = require_artifacts(directory, "sysupgrade.bin")
    factory = require_artifacts(directory, "factory.ubi")
    manifests = require_artifacts(directory, ".manifest")
    verify_profile(directory)
    checked = verify_checksums(directory)
    required_files = frozenset(path.name for path in sysupgrade + factory + manifests)
    missing = required_files - checked
    if missing:
        raise ValueError(f"Missing sha256sums records for: {', '.join(sorted(missing))}")
    expected = selected_packages(arguments.requested) | CRITICAL_PACKAGES
    for path in manifests:
        require_packages(expected, manifest_packages(path), f"Manifest {path.name}")
    print(f"Firmware verified for {PROFILE}: both image formats present, "
          f"{len(checked)} files SHA-256 checked, {len(expected)} required packages installed.")


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    config = commands.add_parser("config", help="Verify resolved Kconfig package selection")
    config.add_argument("--baseline", type=Path, required=True)
    config.add_argument("--actual", type=Path, required=True)
    config.add_argument("--requested", type=Path, required=True)
    config.add_argument("--features", type=Path,
                        help="Verify explicitly enabled and disabled feature options")
    config.set_defaults(verify=verify_config)
    firmware = commands.add_parser("firmware", help="Verify generated images and package manifests")
    firmware.add_argument("--directory", type=Path, required=True)
    firmware.add_argument("--requested", type=Path, required=True)
    firmware.set_defaults(verify=verify_firmware)
    return root


def main():
    arguments = parser().parse_args()
    try:
        arguments.verify(arguments)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Build verification failed: {error}", file=sys.stderr)
        return FAILURE_EXIT_CODE
    return 0


if __name__ == "__main__":
    sys.exit(main())
