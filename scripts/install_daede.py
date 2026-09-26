#!/usr/bin/env python3
"""Install the pinned kenzok8 DAEDE recipes, preserving the original packages feed."""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from add_packages import checkout


REPOSITORY = "kenzok8/openwrt-daede"
GROUP_NAME = "kenzok8_openwrt-daede"
FEED_LINK = Path("package/feeds/packages/daed")
FEED_SOURCE = Path("feeds/packages/net/daed")
RECIPE_ANCHOR = "PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)"
HOST_DEPENDENCY = "PKG_BUILD_DEPENDS:=luci-base/host"
RECIPES = ("daed", "luci-app-daede")
CONFIG_RESOURCE = Path("dae/files/dae.config")
REQUIRED_FILES = tuple(Path(name) / "Makefile" for name in RECIPES) + (CONFIG_RESOURCE,)
FAILURE_EXIT_CODE = 1


def validate_source_entry(entry):
    if not isinstance(entry, dict) or entry.get("repo") != REPOSITORY:
        raise ValueError(f"daede must select the maintained repository {REPOSITORY}")
    sha = entry.get("sha")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
        raise ValueError("daede.sha must be a full 40-character commit SHA")
    return {"repo": REPOSITORY, "sha": sha.lower()}


def read_source_lock(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    entry = data.get("daede") if isinstance(data, dict) else None
    return validate_source_entry(entry)


def validate_feed_link(source):
    link = source / FEED_LINK
    expected = source / FEED_SOURCE
    if not link.is_symlink():
        raise ValueError(f"Expected a DAED feed symbolic link: {link}")
    if not expected.is_dir() or link.resolve(strict=True) != expected.resolve(strict=True):
        raise ValueError(f"Unexpected DAED link target: {link}; expected {expected}")
    return link


def adapted_luci_recipe(recipe):
    original = recipe.read_bytes().decode("utf-8")
    if re.search(r"^PKG_BUILD_DEPENDS\s*[:+?]?=", original, flags=re.MULTILINE):
        raise ValueError("luci-app-daede already declares PKG_BUILD_DEPENDS; review the adaptation")
    if original.splitlines().count(RECIPE_ANCHOR) != 1:
        raise ValueError("luci-app-daede must contain a unique PKG_BUILD_DIR anchor")
    newline = "\r\n" if "\r\n" in original else "\n"
    anchor_pattern = r"^" + re.escape(RECIPE_ANCHOR) + r"(?=\r?$)"
    adapted = re.sub(anchor_pattern, lambda match: match.group() + newline + HOST_DEPENDENCY,
                     original, count=1, flags=re.MULTILINE)
    return adapted.encode("utf-8")


def install_payload(downloaded, destination):
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"DAEDE custom package directory already exists: {destination}")
    for relative in REQUIRED_FILES:
        if not (downloaded / relative).is_file():
            raise ValueError(f"Missing source file: {downloaded / relative}")
    luci_recipe = adapted_luci_recipe(downloaded / "luci-app-daede/Makefile")
    destination.mkdir(parents=True)
    for name in RECIPES:
        shutil.copytree(downloaded / name, destination / name)
    resource = destination / CONFIG_RESOURCE
    resource.parent.mkdir(parents=True)
    shutil.copy2(downloaded / CONFIG_RESOURCE, resource)
    (destination / "luci-app-daede/Makefile").write_bytes(luci_recipe)
    return [{"file": "luci-app-daede/Makefile", "anchor": RECIPE_ANCHOR,
             "added": HOST_DEPENDENCY, "reason": "Declare po2lmo host build dependency"}]


def install_daede(source, downloaded, entry):
    locked = validate_source_entry(entry)
    root = source.resolve(strict=True)
    link = validate_feed_link(root)
    destination = root / "package/custom" / GROUP_NAME
    if not destination.resolve().is_relative_to(root):
        raise ValueError(f"DAEDE destination escapes the OpenWrt source tree: {destination}")
    adaptations = install_payload(downloaded, destination)
    # Remove only the verified feed link after every replacement file is ready.
    link.unlink()
    return {
        **locked,
        "packages": list(RECIPES),
        "replacement": {"removed_symlink": FEED_LINK.as_posix(),
                        "preserved_feed": FEED_SOURCE.as_posix(),
                        "installed_directory": destination.relative_to(root).as_posix()},
        "resources": [CONFIG_RESOURCE.as_posix()],
        "adaptations": adaptations,
    }


def install_from_lock(arguments):
    locked = read_source_lock(arguments.lock)
    validate_feed_link(arguments.source)
    downloaded = arguments.source / ".extra" / GROUP_NAME
    checkout(locked, downloaded)
    actual = subprocess.run(["git", "-C", str(downloaded), "rev-parse", "HEAD"],
                            check=True, capture_output=True, text=True).stdout.strip()
    if actual != locked["sha"]:
        raise ValueError(f"DAEDE checkout mismatch: expected {locked['sha']}, got {actual}")
    evidence = install_daede(arguments.source, downloaded, locked)
    arguments.evidence.parent.mkdir(parents=True, exist_ok=True)
    arguments.evidence.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"Installed {REPOSITORY}@{actual}; evidence: {arguments.evidence}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        install_from_lock(arguments)
    except (OSError, UnicodeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"DAEDE installation failed: {error}", file=sys.stderr)
        return FAILURE_EXIT_CODE
    return 0


if __name__ == "__main__":
    sys.exit(main())
