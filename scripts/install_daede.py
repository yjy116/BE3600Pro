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
from daede_service_compat import adapt_services


REPOSITORY = "kenzok8/openwrt-daede"
GROUP_NAME = "kenzok8_openwrt-daede"
FEED_LINK_DIRECTORY = Path("package/feeds/packages")
FEED_SOURCE_DIRECTORY = Path("feeds/packages/net")
RECIPE_ANCHOR = "PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)"
HOST_DEPENDENCY = "PKG_BUILD_DEPENDS:=luci-base/host"
DAEMONS = ("dae", "daed")
RECIPES = (*DAEMONS, "luci-app-daede")
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


def validate_feed_link(source, name):
    link = source / FEED_LINK_DIRECTORY / name
    expected = source / FEED_SOURCE_DIRECTORY / name
    if not link.is_symlink():
        raise ValueError(f"Expected a {name.upper()} feed symbolic link: {link}")
    if not expected.is_dir() or link.resolve(strict=True) != expected.resolve(strict=True):
        raise ValueError(f"Unexpected {name.upper()} link target: {link}; expected {expected}")
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
    destination.mkdir(parents=True)
    for name in RECIPES:
        shutil.copytree(downloaded / name, destination / name)
    service_adaptations = adapt_services(destination)
    luci_recipe = destination / "luci-app-daede/Makefile"
    luci_recipe.write_bytes(adapted_luci_recipe(luci_recipe))
    build_adaptation = {"file": "luci-app-daede/Makefile", "anchor": RECIPE_ANCHOR,
                        "added": HOST_DEPENDENCY, "reason": "Declare po2lmo host build dependency"}
    return [*service_adaptations, build_adaptation]


def install_daede(source, downloaded, entry):
    locked = validate_source_entry(entry)
    root = source.resolve(strict=True)
    links = tuple(validate_feed_link(root, name) for name in DAEMONS)
    destination = root / "package/custom" / GROUP_NAME
    if not destination.resolve().is_relative_to(root):
        raise ValueError(f"DAEDE destination escapes the OpenWrt source tree: {destination}")
    adaptations = install_payload(downloaded, destination)
    # Both links are validated before staging; remove them only after all recipes are ready.
    for link in links:
        link.unlink()
    return {
        **locked,
        "packages": list(RECIPES),
        "replacements": [
            {"package": name, "removed_symlink": (FEED_LINK_DIRECTORY / name).as_posix(),
             "preserved_feed": (FEED_SOURCE_DIRECTORY / name).as_posix(),
             "installed_directory": (destination / name).relative_to(root).as_posix()}
            for name in DAEMONS
        ],
        "adaptations": adaptations,
    }


def install_from_lock(arguments):
    locked = read_source_lock(arguments.lock)
    for name in DAEMONS:
        validate_feed_link(arguments.source, name)
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
