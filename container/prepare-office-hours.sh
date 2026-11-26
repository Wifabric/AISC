#!/bin/sh
# Stage pinned market assets in the image. Engines discover a skill only after explicit installation.
set -eu
downloads=${1:-/tmp/dl}
market=/opt/aisc/market
mkdir -p "$market/gstack"
tar -xzf "$downloads/gstack-office-hours-8143a91809b2.tar.gz" -C "$market/gstack"
arch=$(dpkg --print-architecture)
case "$arch" in amd64) arch=x64 ;; arm64) arch=arm64 ;; esac
archive="$downloads/bun-linux-$arch-1.4.4.tgz"
if [ -f "$archive" ]; then
    mkdir -p "$market/bun"
    tar -xzf "$archive" -C "$market/bun"
    test "$("$market/bun/package/bin/bun" --version)" = 1.4.4
    ln -sf "$market/bun/package/bin/bun" /usr/local/bin/bun
fi
