#!/bin/sh
# Starts the container's command as the unprivileged "bot" user.
#
# It runs as root only to hand the /data volume to that user: a new volume, or
# files copied in by the restore runbook, belong to root. Then it drops root and
# exec's the command, so the bot is the main process and gets SIGTERM directly
# when the host stops it (DP-4).
#
# MAINTENANCE=1 keeps the container up without starting the bot, e.g. to restore
# a snapshot (docs/restore-runbook.md).
set -eu

if [ "$(id -u)" = 0 ]; then
    if [ -d /data ]; then
        chown -R bot:bot /data
    fi
    if [ "${MAINTENANCE:-}" = 1 ]; then
        echo "{\"time\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", \"level\": \"warning\", \"event\": \"maintenance mode: the bot is not running\"}"
        exec sleep infinity
    fi
    exec setpriv --reuid=bot --regid=bot --init-groups -- "$@"
fi
exec "$@"
