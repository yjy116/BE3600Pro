#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT/wrt"
make download -j"$(nproc)" V=s 2>&1 | tee "$ROOT/artifacts/download.log"
make -j"$(nproc)" V=s 2>&1 | tee "$ROOT/artifacts/build.log"
python3 "$ROOT/scripts/verify_build.py" firmware \
    --directory bin/targets/qualcommbe/ipq53xx \
    --requested "$ROOT/Config/plugins.config" \
    --versions "$ROOT/Config/package-versions.json"
mkdir -p "$ROOT/artifacts/firmware"
find bin/targets/qualcommbe/ipq53xx -maxdepth 1 -type f \
    -exec cp -t "$ROOT/artifacts/firmware" {} +
