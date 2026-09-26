"""Resolve the known Tailscale package/frontend file ownership conflict."""

from pathlib import Path
import sys


def migrate(makefile):
    original = makefile.read_text()
    lines = original.splitlines(keepends=True)
    conflicts = [line for line in lines if "$(INSTALL_" in line and
                 ("tailscale.init" in line or "tailscale.conf" in line)]
    if len(conflicts) != len(("tailscale.init", "tailscale.conf")):
        raise RuntimeError("Tailscale recipe changed: inspect config ownership")
    makefile.write_text("".join(line for line in lines if line not in conflicts))
    print("Tailscale config/init files owned by luci-app-tailscale; backend preserved")


if __name__ == "__main__":
    migrate(Path(sys.argv[1]))
