"""Add only package recipes absent from the upstream package metadata."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess


def checkout(source, destination):
    subprocess.run(["git", "init", str(destination)], check=True)
    url = f"https://github.com/{source['repo']}.git"
    subprocess.run(["git", "-C", str(destination), "fetch", "--depth=1", url,
                    source["sha"]], check=True)
    subprocess.run(["git", "-C", str(destination), "checkout", "--detach",
                    "FETCH_HEAD"], check=True)


def install_group(source, context):
    missing = [item for item in source["packages"]
               if item["name"] not in context["available"]]
    if not missing:
        print(f"Upstream already provides all packages from {source['repo']}")
        return
    source_dir = context["downloads"] / source["repo"].replace("/", "_")
    checkout(source, source_dir)
    group = context["custom"] / source["repo"].replace("/", "_")
    group.mkdir(parents=True)
    for item in missing:
        recipe = source_dir / item["path"]
        if not (recipe / "Makefile").is_file():
            raise RuntimeError(f"Missing recipe: {recipe}")
        shutil.copytree(recipe, group / item["name"],
                        ignore=shutil.ignore_patterns(".git", ".github"))
        print(f"Added {item['name']} from {source['repo']}@{source['sha']}")
    version = source_dir / "version.mk"
    if version.is_file():
        shutil.copy2(version, group / version.name)
    context["records"].append({"repo": source["repo"], "sha": source["sha"],
                               "packages": [item["name"] for item in missing]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    metadata = (args.source / "tmp/.packageinfo").read_text()
    available = {line.removeprefix("Package: ") for line in metadata.splitlines()
                 if line.startswith("Package: ")}
    if not available:
        raise RuntimeError("No upstream package metadata; run make defconfig first")
    context = {"available": available, "downloads": args.source / ".extra",
               "custom": args.source / "package/custom", "records": []}
    for source in json.loads(args.lock.read_text())["extras"]:
        install_group(source, context)
    args.evidence.write_text(json.dumps(context["records"], indent=2) + "\n")


if __name__ == "__main__":
    main()
