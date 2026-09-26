#!/usr/bin/env python3
"""Apply reviewed mutual exclusion to the pinned DAEDE service and LuCI files."""

import hashlib
from pathlib import Path
import shutil
import subprocess


PATCH_FILE = Path(__file__).resolve().parents[1] / "patches/003-daede-backend-exclusion.patch"
COMMAND_TIMEOUT_SECONDS = 30
UPSTREAM_SHA = "0b0e5d671e5748a060fbd79abc2f73733b09f902"
UI_DIRECTORY = "luci-app-daede/htdocs/luci-static/resources/view/daede"
NEW_HELPER = "luci-app-daede/root/usr/share/luci-app-daede/backend-exec"
# Fingerprints normalize line endings and final blank lines, without changing code.
UPSTREAM_FILES = {
    "dae/files/dae.init": "753db2db1d3f8c0ab97df6cdd0559bb2482330d9d37e5b8fac521fc4337482ef",
    "daed/files/daed.init": "a7981282134159794eea3112ebd8a440116e5035e67ec145184f3d9e308daebe",
    "daed/files/daed-guard": "81a34d05b7135e1f6c9535029d909b828c02e30eb52b6e775492c17a7433ddf8",
    "luci-app-daede/Makefile": "00aafa8b25a2dae4908c3a224cc0fa0454e128e4546f4fe01ed26274a892e261",
    "luci-app-daede/root/usr/share/rpcd/acl.d/luci-app-daede.json": "30151c846765616e184c8388b7c2bb1d8580c55ce9606779eecd38eda9e822a4",
    f"{UI_DIRECTORY}/backend.js": "7c5689d9dd0fe63c6a0e33aefb1fbdcb0307fded0d76227a018a649a4a0d9a98",
    f"{UI_DIRECTORY}/widgets.js": "ca845332d3944320214e05093ecb862beb30dca28c538275e786f8dabdb5162e",
}


def validate_upstream(bundle):
    if (bundle / NEW_HELPER).exists():
        raise ValueError(f"DAEDE upstream helper already exists: {NEW_HELPER}")
    for relative, expected in UPSTREAM_FILES.items():
        path = bundle / relative
        text = path.read_text(encoding="utf-8").rstrip() + "\n"
        actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if actual != expected:
            raise ValueError(f"DAEDE upstream fingerprint mismatch: {relative}; expected {UPSTREAM_SHA}")


def patch_executable():
    executable = shutil.which("patch")
    if executable:
        return executable
    git = shutil.which("git")
    windows_tool = Path(git).parent.parent / "usr/bin/patch.exe" if git else None
    if windows_tool is not None and windows_tool.is_file():
        return str(windows_tool)
    raise OSError("GNU patch is required to apply the reviewed DAEDE service adaptation")


def run_patch(command, dry_run):
    options = command + (["--dry-run"] if dry_run else [])
    result = subprocess.run(options, check=False, capture_output=True, text=True,
                            timeout=COMMAND_TIMEOUT_SECONDS)
    if result.returncode:
        raise ValueError("DAEDE service patch failed: " + (result.stdout + result.stderr).strip())


def adapt_services(bundle):
    root = Path(bundle).resolve(strict=True)
    validate_upstream(root)
    command = [patch_executable(), "--batch", "--forward", "--fuzz=0", "-p1",
               "--directory", root.as_posix(), "--input", PATCH_FILE.as_posix()]
    run_patch(command, True)
    run_patch(command, False)
    return [{"patch": PATCH_FILE.name, "sha256": hashlib.sha256(PATCH_FILE.read_bytes()).hexdigest(),
             "upstream_sha": UPSTREAM_SHA, "files": sorted([*UPSTREAM_FILES, NEW_HELPER]),
             "reason": "Persist backend selection and refuse overlapping DAE/DAED service startup"}]
