#!/bin/sh
# Runs unprivileged on the host. Polkit authorizes only the fixed KMS helper.
# GSR passes socket, DRM card and home; home is deliberately unused.
set -eu
if [ "$#" -ne 3 ]; then
    echo 'Trama KMS: expected socket, DRM card and home' >&2
    exit 2
fi
case "$1" in
    /*) ;;
    *) echo 'Trama KMS: socket must be an absolute path' >&2; exit 2 ;;
esac
if [ "${#1}" -gt 107 ]; then
    echo 'Trama KMS: socket path exceeds Linux limit' >&2
    exit 2
fi
case "$2" in
    /dev/dri/card*) card_number=${2#/dev/dri/card} ;;
    *) echo 'Trama KMS: expected /dev/dri/cardN' >&2; exit 2 ;;
esac
case "$card_number" in
    ''|*[!0-9]*) echo 'Trama KMS: invalid DRM card number' >&2; exit 2 ;;
esac
exec /usr/bin/pkexec /var/lib/flatpak/app/io.github.xoloitzcuintle95.Trama/current/active/files/bin/gsr-kms-server "$1" "$2"
