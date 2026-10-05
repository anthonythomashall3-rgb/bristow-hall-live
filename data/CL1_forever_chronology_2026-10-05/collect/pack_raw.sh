#!/bin/sh
# pack each series' raw ALFRED batches (the bytes as served, plus its vintage_dates.txt) for the repository
cd "$(dirname "$0")/.." && mkdir -p raw/alfred_packed && for d in raw/alfred/*/; do id=$(basename "$d"); tar -czf "raw/alfred_packed/$id.tar.gz" -C raw/alfred "$id"; done && ls -la raw/alfred_packed
