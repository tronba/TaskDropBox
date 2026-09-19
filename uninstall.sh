#!/usr/bin/env bash
set -Eeuo pipefail

[[ $EUID -eq 0 ]] || { echo "Run as root." >&2; exit 1; }

echo "This removes TaskDropBox services and application code."
echo "Persistent data in /var/lib/taskdropbox and configuration in /etc/taskdropbox will be preserved."
read -r -p "Continue? [y/N]: " CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 0; }

systemctl disable --now taskdropbox.service 2>/dev/null || true
rm -f /etc/systemd/system/taskdropbox.service
rm -f /usr/local/sbin/taskdropbox-manage
rm -f /etc/nginx/sites-enabled/taskdropbox /etc/nginx/sites-available/taskdropbox
systemctl daemon-reload
systemctl reload nginx 2>/dev/null || true
rm -rf -- /opt/taskdropbox

echo "Application code and services were removed."
echo "Preserved data: /var/lib/taskdropbox"
echo "Preserved configuration: /etc/taskdropbox"
echo "No data-removal option is provided by this script; remove preserved paths only through a separately reviewed procedure."
