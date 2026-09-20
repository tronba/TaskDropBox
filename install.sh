#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="taskdropbox"
APP_DIR="/opt/taskdropbox"
DATA_DIR="/var/lib/taskdropbox"
CONFIG_DIR="/etc/taskdropbox"
ENV_FILE="${CONFIG_DIR}/taskdropbox.env"
SCRIPT_PATH="${BASH_SOURCE[0]}"
[[ "$SCRIPT_PATH" == */* ]] || SCRIPT_PATH="./$SCRIPT_PATH"
SOURCE_DIR="$(cd -- "${SCRIPT_PATH%/*}" && pwd)"
MODE="install"
NON_INTERACTIVE=0
BASE_URL=""
TIME_ZONE=""
PIN_FILE=""
MAX_FILE_MIB=""
MAX_SUBMISSION_MIB=""
MIN_FREE_MIB=""
SKIP_OS_UPDATES=0
SERVICE_WAS_ACTIVE=0

restart_service_after_failed_install() {
  local status=$?
  if [[ $status -ne 0 && $SERVICE_WAS_ACTIVE -eq 1 ]]; then
    echo "Installation failed after stopping TaskDropBox; attempting to restart the previous service." >&2
    systemctl start taskdropbox.service 2>/dev/null || true
  fi
  return "$status"
}

trap restart_service_after_failed_install EXIT

usage() {
  echo "Usage: sudo ./install.sh [--upgrade|--reconfigure] [options]"
  echo "  --base-url http://10.20.0.10"
  echo "  --timezone Europe/Oslo"
  echo "  --creator-pin-file /root/private-pin-file"
  echo "  --max-file-mib 25 --max-submission-mib 50 --min-free-mib 1024"
  echo "  --non-interactive"
  echo "  --skip-os-updates  CI/testing only; do not use for normal preparation"
}

fail() { echo "ERROR: $*" >&2; exit 1; }
require_value() { [[ $# -ge 2 && -n "$2" ]] || fail "Missing value for $1"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --upgrade) MODE="upgrade"; shift ;;
    --reconfigure) MODE="reconfigure"; shift ;;
    --base-url) require_value "$@"; BASE_URL="$2"; shift 2 ;;
    --timezone) require_value "$@"; TIME_ZONE="$2"; shift 2 ;;
    --creator-pin-file) require_value "$@"; PIN_FILE="$2"; shift 2 ;;
    --max-file-mib) require_value "$@"; MAX_FILE_MIB="$2"; shift 2 ;;
    --max-submission-mib) require_value "$@"; MAX_SUBMISSION_MIB="$2"; shift 2 ;;
    --min-free-mib) require_value "$@"; MIN_FREE_MIB="$2"; shift 2 ;;
    --non-interactive) NON_INTERACTIVE=1; shift ;;
    --skip-os-updates) SKIP_OS_UPDATES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Unknown option: $1" ;;
  esac
done

[[ $EUID -eq 0 ]] || fail "Run this installer as root."
[[ -r /etc/os-release ]] || fail "Cannot identify the operating system."
# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "26.04" ]] || \
  fail "TaskDropBox supports Ubuntu Server 26.04 LTS only. Found ${PRETTY_NAME:-unknown}."

if [[ -e "$APP_DIR" && "$MODE" == "install" ]]; then
  fail "An installation already exists. Rerun with --upgrade or --reconfigure; data was not changed."
fi
if [[ ! -e "$APP_DIR" && "$MODE" != "install" ]]; then
  fail "No existing installation was found for --${MODE}."
fi

if [[ -f "$ENV_FILE" ]]; then
  CURRENT_BASE_URL="$(sed -n "s/^TASKDROPBOX_BASE_URL='\(.*\)'$/\1/p" "$ENV_FILE")"
  CURRENT_TIME_ZONE="$(sed -n "s/^TASKDROPBOX_TIME_ZONE='\(.*\)'$/\1/p" "$ENV_FILE")"
  CURRENT_LANGUAGE="$(sed -n "s/^TASKDROPBOX_LANGUAGE='\(.*\)'$/\1/p" "$ENV_FILE")"
  CURRENT_MAX_FILE_MIB="$(sed -n "s/^TASKDROPBOX_MAX_FILE_MIB='\(.*\)'$/\1/p" "$ENV_FILE")"
  CURRENT_MAX_SUBMISSION_MIB="$(sed -n "s/^TASKDROPBOX_MAX_SUBMISSION_MIB='\(.*\)'$/\1/p" "$ENV_FILE")"
  CURRENT_MIN_FREE_MIB="$(sed -n "s/^TASKDROPBOX_MIN_FREE_DISK_MIB='\(.*\)'$/\1/p" "$ENV_FILE")"
else
  CURRENT_BASE_URL=""
  CURRENT_TIME_ZONE=""
  CURRENT_LANGUAGE="en"
  CURRENT_MAX_FILE_MIB=""
  CURRENT_MAX_SUBMISSION_MIB=""
  CURRENT_MIN_FREE_MIB=""
fi

prompt_value() {
  local prompt="$1" default="$2" result
  if [[ $NON_INTERACTIVE -eq 1 ]]; then
    [[ -n "$default" ]] || fail "$prompt is required in non-interactive mode."
    printf '%s' "$default"
    return
  fi
  read -r -p "$prompt [$default]: " result
  printf '%s' "${result:-$default}"
}

if [[ -z "$BASE_URL" ]]; then
  if [[ $NON_INTERACTIVE -eq 1 ]]; then
    BASE_URL="${CURRENT_BASE_URL:-}"
    [[ -n "$BASE_URL" ]] || fail "--base-url is required with --non-interactive."
  else
    BASE_URL="$(prompt_value "Static TaskDropBox URL" "${CURRENT_BASE_URL:-http://10.20.0.10}")"
  fi
fi

if [[ -z "$TIME_ZONE" ]]; then
  if [[ $NON_INTERACTIVE -eq 1 ]]; then
    TIME_ZONE="${CURRENT_TIME_ZONE:-Europe/Oslo}"
  else
    TIME_ZONE="$(prompt_value "School timezone" "${CURRENT_TIME_ZONE:-Europe/Oslo}")"
  fi
fi

if [[ -z "$MAX_FILE_MIB" ]]; then
  MAX_FILE_MIB="$(prompt_value "Maximum individual file size in MiB" "${CURRENT_MAX_FILE_MIB:-25}")"
fi
if [[ -z "$MAX_SUBMISSION_MIB" ]]; then
  MAX_SUBMISSION_MIB="$(prompt_value "Maximum total submission size in MiB" "${CURRENT_MAX_SUBMISSION_MIB:-50}")"
fi
if [[ -z "$MIN_FREE_MIB" ]]; then
  MIN_FREE_MIB="$(prompt_value "Reserved free disk space in MiB" "${CURRENT_MIN_FREE_MIB:-1024}")"
fi

for value in "$MAX_FILE_MIB" "$MAX_SUBMISSION_MIB" "$MIN_FREE_MIB"; do
  [[ "$value" =~ ^[0-9]+$ && "$value" -gt 0 ]] || fail "Size values must be positive integers."
done
(( MAX_SUBMISSION_MIB >= MAX_FILE_MIB )) || fail "Total submission size must be at least the individual file size."

BASE_URL="${BASE_URL%/}"

[[ "$BASE_URL" =~ ^http://([0-9]{1,3}\.){3}[0-9]{1,3}(:80)?$ ]] || \
  fail "Base URL must use a literal IPv4 address, such as http://10.20.0.10"
ALLOWED_HOST="${BASE_URL#http://}"
ALLOWED_HOST="${ALLOWED_HOST%:80}"
IFS=. read -r OCTET_1 OCTET_2 OCTET_3 OCTET_4 <<< "$ALLOWED_HOST"
for octet in "$OCTET_1" "$OCTET_2" "$OCTET_3" "$OCTET_4"; do
  (( 10#$octet <= 255 )) || fail "Base URL contains an invalid IPv4 address."
done

[[ -e "/usr/share/zoneinfo/${TIME_ZONE}" ]] || fail "Unknown timezone: ${TIME_ZONE}"

PIN=""
if [[ -n "$PIN_FILE" ]]; then
  [[ -f "$PIN_FILE" && -r "$PIN_FILE" ]] || fail "PIN file is not readable."
  PIN="$(tr -d '\r\n' < "$PIN_FILE")"
elif [[ "$MODE" == "install" || "$MODE" == "reconfigure" ]]; then
  [[ $NON_INTERACTIVE -eq 0 ]] || fail "--creator-pin-file is required in non-interactive mode."
  read -r -s -p "Six-digit creator PIN: " PIN; echo
  read -r -s -p "Repeat creator PIN: " PIN_AGAIN; echo
  [[ "$PIN" == "$PIN_AGAIN" ]] || fail "PIN entries did not match."
fi
[[ -z "$PIN" || "$PIN" =~ ^[0-9]{6}$ ]] || fail "Creator PIN must be exactly six digits."

echo
echo "TaskDropBox ${MODE} summary"
echo "  Source:           ${SOURCE_DIR}"
echo "  Application:      ${APP_DIR}"
echo "  Persistent data:  ${DATA_DIR} (preserved on upgrade/uninstall)"
echo "  Configuration:    ${CONFIG_DIR}"
echo "  Service URL:      ${BASE_URL}"
echo "  Timezone:         ${TIME_ZONE}"
echo "  File limit:       ${MAX_FILE_MIB} MiB per file"
echo "  Submission limit: ${MAX_SUBMISSION_MIB} MiB total"
echo "  Disk reserve:     ${MIN_FREE_MIB} MiB"
echo "  Transport:        HTTP on an isolated LAN (not encrypted)"
echo "  OS updates:       apt metadata and available upgrades will be applied"
if [[ $SKIP_OS_UPDATES -eq 1 ]]; then
  echo "  WARNING:           OS upgrades are skipped for this test run"
fi
echo "  Services:         taskdropbox.service and nginx"
echo
if [[ $NON_INTERACTIVE -eq 0 ]]; then
  read -r -p "Continue? [y/N]: " CONFIRM
  [[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "Cancelled; nothing was changed."; exit 0; }
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
if [[ $SKIP_OS_UPDATES -eq 0 ]]; then
  apt-get -y upgrade
  if [[ -e /var/run/reboot-required ]]; then
    echo "Ubuntu requires a reboot. No TaskDropBox application data was changed."
    echo "Reboot, then rerun the same installer command."
    exit 20
  fi
fi

apt-get install -y python3 python3-venv python3-pip nginx rsync curl sqlite3 gettext
timedatectl set-timezone "$TIME_ZONE"
systemctl disable --now chrony.service 2>/dev/null || true
systemctl disable --now systemd-timesyncd.service 2>/dev/null || true

if ! getent group taskdropbox >/dev/null; then groupadd --system taskdropbox; fi
if ! id taskdropbox >/dev/null 2>&1; then
  useradd --system --gid taskdropbox --home-dir "$DATA_DIR" --shell /usr/sbin/nologin taskdropbox
fi
# Nginx proxies over loopback and must not inherit access to private application data.
gpasswd -d www-data taskdropbox >/dev/null 2>&1 || true
install -d -o root -g taskdropbox -m 0750 "$CONFIG_DIR"
install -d -o taskdropbox -g taskdropbox -m 0750 "$DATA_DIR" "$DATA_DIR/files"

if systemctl is-active --quiet taskdropbox.service; then
  SERVICE_WAS_ACTIVE=1
  systemctl stop taskdropbox.service
  echo "Stopped the existing TaskDropBox service for a consistent upgrade."
fi

if [[ -f "$ENV_FILE" ]]; then
  cp -a "$ENV_FILE" "${ENV_FILE}.backup.$(date -u +%Y%m%dT%H%M%SZ)"
fi

if [[ "$MODE" != "reconfigure" ]]; then
  install -d -o root -g root -m 0755 "$APP_DIR"
  rsync -a --delete \
    --exclude '.git/' --exclude '.venv/' --exclude 'venv/' --exclude '.venv-previous/' \
    --exclude 'data/' --exclude '__pycache__/' \
    --exclude 'staticfiles/' --exclude '*.pyc' "$SOURCE_DIR/" "$APP_DIR/"

  VENV_DIR="$APP_DIR/venv"
  PREVIOUS_VENV_DIR="$APP_DIR/.venv-previous"
  [[ "$VENV_DIR" == "/opt/taskdropbox/venv" ]] || fail "Virtual-environment path failed its safety check."
  [[ "$PREVIOUS_VENV_DIR" == "/opt/taskdropbox/.venv-previous" ]] || \
    fail "Previous virtual-environment path failed its safety check."
  rm -rf -- "$PREVIOUS_VENV_DIR"
  if [[ -d "$VENV_DIR" ]]; then
    mv -- "$VENV_DIR" "$PREVIOUS_VENV_DIR"
  fi
  if python3 -m venv "$VENV_DIR" && \
     "$VENV_DIR/bin/python" -m pip install --upgrade pip && \
     "$VENV_DIR/bin/python" -m pip install "$APP_DIR"; then
    rm -rf -- "$PREVIOUS_VENV_DIR"
  else
    rm -rf -- "$VENV_DIR"
    if [[ -d "$PREVIOUS_VENV_DIR" ]]; then
      mv -- "$PREVIOUS_VENV_DIR" "$VENV_DIR"
    fi
    fail "Could not build the new virtual environment; the previous one was restored."
  fi
fi

install -d -o taskdropbox -g taskdropbox -m 0755 "$APP_DIR/staticfiles"
install -d -o root -g root -m 0755 "$APP_DIR/public"
SOURCE_ARCHIVE_TEMP="$(mktemp)"
tar -C "$APP_DIR" \
  --exclude='./venv' --exclude='./staticfiles' --exclude='./public' \
  --exclude='./data' --exclude='./.git' --exclude='__pycache__' --exclude='*.pyc' \
  -czf "$SOURCE_ARCHIVE_TEMP" .
install -o root -g root -m 0644 "$SOURCE_ARCHIVE_TEMP" "$APP_DIR/public/taskdropbox-source.tar.gz"
rm -f "$SOURCE_ARCHIVE_TEMP"

if [[ -n "$PIN" ]]; then
  PIN_HASH="$(PIN_VALUE="$PIN" "$APP_DIR/venv/bin/python" - <<'PY'
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.contrib.auth.hashers import make_password

print(make_password(os.environ["PIN_VALUE"], hasher="argon2"))
PY
)"
elif [[ -f "$ENV_FILE" ]]; then
  PIN_HASH="$(sed -n "s/^TASKDROPBOX_CREATOR_PIN_HASH='\(.*\)'$/\1/p" "$ENV_FILE")"
else
  fail "No creator PIN is available."
fi

if [[ -f "$ENV_FILE" ]]; then
  SECRET_KEY="$(sed -n "s/^TASKDROPBOX_SECRET_KEY='\(.*\)'$/\1/p" "$ENV_FILE")"
fi
if [[ -z "${SECRET_KEY:-}" ]]; then
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')"
fi

REQUEST_MIB=$((MAX_SUBMISSION_MIB + 5))
cat > "$ENV_FILE" <<EOF
TASKDROPBOX_SECRET_KEY='${SECRET_KEY}'
TASKDROPBOX_CREATOR_PIN_HASH='${PIN_HASH}'
TASKDROPBOX_ALLOWED_HOSTS='${ALLOWED_HOST}'
TASKDROPBOX_BASE_URL='${BASE_URL}'
TASKDROPBOX_TIME_ZONE='${TIME_ZONE}'
TASKDROPBOX_LANGUAGE='${CURRENT_LANGUAGE:-en}'
TASKDROPBOX_DATA_DIR='${DATA_DIR}'
TASKDROPBOX_MAX_TASK_ATTACHMENTS='10'
TASKDROPBOX_MAX_FILE_MIB='${MAX_FILE_MIB}'
TASKDROPBOX_MAX_SUBMISSION_MIB='${MAX_SUBMISSION_MIB}'
TASKDROPBOX_MAX_FILES_PER_SUBMISSION='10'
TASKDROPBOX_MIN_FREE_DISK_MIB='${MIN_FREE_MIB}'
TASKDROPBOX_CREATOR_SESSION_HOURS='8'
TASKDROPBOX_ADMIN_SESSION_HOURS='8'
TASKDROPBOX_CREATOR_PIN_GLOBAL_ATTEMPTS='50'
TASKDROPBOX_CREATOR_PIN_WINDOW_SECONDS='300'
TASKDROPBOX_CREATOR_PIN_LOCK_SECONDS='300'
EOF
chown root:taskdropbox "$ENV_FILE"
chmod 0640 "$ENV_FILE"
runuser -u www-data -- test ! -r "$ENV_FILE" || \
  fail "The Nginx account can read the private TaskDropBox configuration."

install -m 0644 "$APP_DIR/deploy/systemd/taskdropbox.service.template" /etc/systemd/system/taskdropbox.service
install -o root -g root -m 0755 "$APP_DIR/deploy/bin/taskdropbox-manage" /usr/local/sbin/taskdropbox-manage
install -o root -g root -m 0755 "$APP_DIR/deploy/bin/taskdropbox-admin" /usr/local/sbin/taskdropbox-admin
sed "s/__REQUEST_MIB__/${REQUEST_MIB}/g" "$APP_DIR/deploy/nginx/taskdropbox.conf.template" \
  > /etc/nginx/sites-available/taskdropbox
ln -sfn /etc/nginx/sites-available/taskdropbox /etc/nginx/sites-enabled/taskdropbox
rm -f /etc/nginx/sites-enabled/default

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
export HOME="$DATA_DIR"
runuser -u taskdropbox --preserve-environment -- "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" migrate --noinput
"$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" compilemessages --locale nb
runuser -u taskdropbox --preserve-environment -- "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput
runuser -u taskdropbox --preserve-environment -- "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" check
runuser -u taskdropbox --preserve-environment -- "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" test drops.tests --noinput
runuser -u www-data -- test ! -r "$DATA_DIR/db.sqlite3" || \
  fail "The Nginx account can read the private TaskDropBox database."
chown -R root:root "$APP_DIR/staticfiles"
find "$APP_DIR/staticfiles" -type d -exec chmod 0755 {} +
find "$APP_DIR/staticfiles" -type f -exec chmod 0644 {} +
nginx -t

systemctl daemon-reload
systemctl enable --now taskdropbox.service nginx.service
systemctl restart taskdropbox.service nginx.service
sleep 1
curl --fail --silent --show-error "${BASE_URL}/healthz" >/dev/null || \
  fail "Installation completed but the HTTP health check failed. Check systemctl status taskdropbox nginx."

echo
echo "TaskDropBox is ready at ${BASE_URL}"
echo "Verify server time: $(date --iso-8601=seconds) (${TIME_ZONE})"
echo "Configuration: ${ENV_FILE}"
echo "Persistent data: ${DATA_DIR}"
echo "Administration: sudo taskdropbox-admin help"
