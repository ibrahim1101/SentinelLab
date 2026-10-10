#!/usr/bin/env bash
# CI helper: retry transient Docker Hub MongoDB pull failures.
set -euo pipefail
image="${MONGO_IMAGE:-mongo:7}"
for attempt in 1 2 3 4 5; do
  if docker pull "$image"; then
    exit 0
  fi
  if [ "$attempt" -eq 5 ]; then
    echo "Failed to pull $image after five attempts" >&2
    exit 1
  fi
  sleep $((attempt * 15))
done
