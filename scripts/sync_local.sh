#!/usr/bin/env bash
set -euo pipefail

# Sync custom integration into a local Home Assistant config directory.
# Usage:
#   ./scripts/sync_local.sh /path/to/ha_config
# Example:
#   ./scripts/sync_local.sh /config

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <ha_config_dir>"
  exit 1
fi

HA_CONFIG_DIR="$1"
SRC_DIR="custom_components/nilan_nabto"
DST_DIR="$HA_CONFIG_DIR/custom_components/nilan_nabto"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "Source integration not found: $SRC_DIR"
  exit 1
fi

mkdir -p "$HA_CONFIG_DIR/custom_components"
rm -rf "$DST_DIR"
cp -r "$SRC_DIR" "$DST_DIR"

echo "Synced to: $DST_DIR"
echo "Next: Restart Home Assistant, then reload Nilan CodeWizard integration."
