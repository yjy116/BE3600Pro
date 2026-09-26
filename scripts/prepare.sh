#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
WRT_DIR="$ROOT/wrt"
EVIDENCE="$ROOT/artifacts"
mkdir -p "$EVIDENCE"
SOURCE_URL=$(jq -r '.firmware.url' "$ROOT/Config/sources.json")
SOURCE_SHA=$(jq -r '.firmware.sha' "$ROOT/Config/sources.json")
git init "$WRT_DIR"
git -C "$WRT_DIR" fetch --depth=1 "$SOURCE_URL" "$SOURCE_SHA"
git -C "$WRT_DIR" checkout --detach FETCH_HEAD
cd "$WRT_DIR"
patch -p1 < "$ROOT/patches/001-default-lan-address.patch"
./scripts/feeds update -a
./scripts/feeds install -a
cp "$ROOT/Config/device.config" .config
make defconfig
cp .config "$EVIDENCE/upstream-default.config"
python3 "$ROOT/scripts/add_packages.py" --source "$WRT_DIR" \
    --lock "$ROOT/Config/sources.json" --evidence "$EVIDENCE/extra-sources.json"
python3 "$ROOT/scripts/install_daede.py" --source "$WRT_DIR" \
    --lock "$ROOT/Config/sources.json" --evidence "$EVIDENCE/daede-source.json"

# This LuCI frontend owns the service config/init files, as in AX6600.
# Keep the upstream Tailscale binary recipe and version.
if [[ -d package/custom/asvow_luci-app-tailscale ]]; then
    python3 "$ROOT/scripts/tailscale_compat.py" feeds/packages/net/tailscale/Makefile
fi
cp -R "$ROOT/package/." package/custom/
cat "$EVIDENCE/upstream-default.config" "$ROOT/Config/plugins.config" \
    "$ROOT/Config/features.config" > .config
make defconfig
cp .config "$EVIDENCE/build.config"
./scripts/diffconfig.sh > "$EVIDENCE/diffconfig"
cp feeds.conf.default "$EVIDENCE/feeds.conf.default"
cp "$ROOT/Config/sources.json" "$EVIDENCE/sources.json"
cp "$ROOT/Config/package-versions.json" "$EVIDENCE/package-versions.json"
git rev-parse HEAD > "$EVIDENCE/firmware-sha.txt"
for feed in feeds/*/.git; do
    feed_dir=${feed%/.git}
    printf '%s %s\n' "$feed_dir" "$(git -C "$feed_dir" rev-parse HEAD)"
done > "$EVIDENCE/feed-shas.txt"
git diff > "$EVIDENCE/source-changes.patch"
git -C feeds/packages diff > "$EVIDENCE/packages-feed-changes.patch"
python3 "$ROOT/scripts/verify_build.py" config \
    --baseline "$EVIDENCE/upstream-default.config" --actual .config \
    --requested "$ROOT/Config/plugins.config" --features "$ROOT/Config/features.config"
