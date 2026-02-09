#!/usr/bin/env bash
set -euo pipefail

# Deploy integration to Home Assistant over SSH using local_settings.json.
# Usage:
#   ./scripts/deploy_ha_ssh.sh

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SETTINGS="$ROOT_DIR/local_settings.json"

if [[ ! -f "$SETTINGS" ]]; then
  echo "Missing $SETTINGS"
  exit 1
fi

read_json() {
  python3 - <<'PY' "$SETTINGS" "$1"
import json,sys
p=sys.argv[1]
path=sys.argv[2].split('.')
obj=json.load(open(p, encoding='utf-8'))
for part in path:
    if isinstance(obj, dict):
        obj = obj.get(part)
    else:
        obj = None
        break
if obj is None:
    print("")
elif isinstance(obj, bool):
    print("true" if obj else "false")
else:
    print(obj)
PY
}

HOST="$(read_json ha.host)"
PORT="$(read_json ha.port)"
USER="$(read_json ha.username)"
CONFIG_PATH="$(read_json ha.config_path)"
KEY_PATH="$(read_json ha.auth.private_key_path)"
AUTH_METHOD="$(read_json ha.auth.method)"
PASSWORD="$(read_json ha.auth.password)"
SRC_REL="$(read_json deploy.integration_src)"
NAME="$(read_json deploy.integration_name)"
RESTART="$(read_json deploy.restart_after_deploy)"

[[ -n "$HOST" ]] || { echo "Missing ha.host"; exit 1; }
[[ -n "$USER" ]] || { echo "Missing ha.username"; exit 1; }
[[ -n "$CONFIG_PATH" ]] || { echo "Missing ha.config_path"; exit 1; }
[[ -n "$SRC_REL" ]] || SRC_REL="custom_components/nilan_nabto"
[[ -n "$NAME" ]] || NAME="nilan_nabto"
[[ -n "$PORT" ]] || PORT="22"

SRC_DIR="$ROOT_DIR/$SRC_REL"
[[ -d "$SRC_DIR" ]] || { echo "Missing source dir: $SRC_DIR"; exit 1; }

SSH_OPTS=(-p "$PORT" -o StrictHostKeyChecking=accept-new)
SCP_OPTS=(-P "$PORT" -o StrictHostKeyChecking=accept-new)
SSH_CMD=(ssh)
SCP_CMD=(scp)
if [[ -n "$KEY_PATH" ]]; then
  SSH_OPTS+=( -i "$KEY_PATH" )
  SCP_OPTS+=( -i "$KEY_PATH" )
fi
if [[ "$AUTH_METHOD" == "password" && -n "$PASSWORD" ]]; then
  if ! command -v sshpass >/dev/null 2>&1; then
    echo "Password auth requested, but sshpass is not installed."
    echo "Install sshpass or switch to key auth in local_settings.json."
    exit 1
  fi
  SSH_CMD=(sshpass -p "$PASSWORD" ssh)
  SCP_CMD=(sshpass -p "$PASSWORD" scp)
fi

REMOTE_TMP="/tmp/${NAME}_$$"
REMOTE_DST="$CONFIG_PATH/custom_components/$NAME"

echo "Deploying $NAME to $USER@$HOST:$REMOTE_DST"
"${SSH_CMD[@]}" "${SSH_OPTS[@]}" "$USER@$HOST" "mkdir -p '$CONFIG_PATH/custom_components' && rm -rf '$REMOTE_TMP'"
"${SCP_CMD[@]}" "${SCP_OPTS[@]}" -r "$SRC_DIR" "$USER@$HOST:$REMOTE_TMP"
"${SSH_CMD[@]}" "${SSH_OPTS[@]}" "$USER@$HOST" "rm -rf '$REMOTE_DST' && mv '$REMOTE_TMP' '$REMOTE_DST'"

# Validate required files after deploy.
"${SSH_CMD[@]}" "${SSH_OPTS[@]}" "$USER@$HOST" "test -f '$REMOTE_DST/manifest.json' && test -f '$REMOTE_DST/__init__.py' && test -f '$REMOTE_DST/config_flow.py' && test -d '$REMOTE_DST/vendor/genvexnabto'"

echo "Deploy complete and verified."

if [[ "$RESTART" == "true" ]]; then
  echo "restart_after_deploy=true -> restarting Home Assistant core..."
  "${SSH_CMD[@]}" "${SSH_OPTS[@]}" "$USER@$HOST" "ha core restart || supervisorctl restart home-assistant || true"
  echo "Restart command sent."
else
  echo "Next: Restart Home Assistant or reload integration in UI."
fi
