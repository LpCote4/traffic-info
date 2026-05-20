#!/bin/bash
set -e

CLEAR=false
ARGS=()

for arg in "$@"; do
    if [[ "$arg" == "--clear" ]]; then
        CLEAR=true
    else
        ARGS+=("$arg")
    fi
done

if $CLEAR; then
    echo "Clearing state and logs..."
    rm -f data/state.json data/travel_log.csv
    echo "Done."
fi

docker compose up "${ARGS[@]}"
