#!/usr/bin/env bash
# Pull the configured MongoDB image, falling back to Docker Hub on registry quota errors.
set -euo pipefail
image="${MONGO_IMAGE:-mongo:7}"
fallback="${MONGO_FALLBACK_IMAGE:-mongo:7}"
attempts="${MONGO_PULL_ATTEMPTS:-3}"

pull_with_retries() {
  local candidate="$1"
  local attempt
  for ((attempt=1; attempt<=attempts; attempt++)); do
    if docker pull "$candidate"; then
      return 0
    fi
    if (( attempt < attempts )); then
      sleep $((attempt * 10))
    fi
  done
  return 1
}

if pull_with_retries "$image"; then
  exit 0
fi
if [[ "$fallback" == "$image" ]]; then
  echo "MongoDB image pull failed: $image" >&2
  exit 1
fi
echo "Primary MongoDB registry unavailable; trying fallback: $fallback" >&2
if pull_with_retries "$fallback"; then
  # Docker Compose still refers to MONGO_IMAGE. Tag the fetched fallback accordingly.
  docker tag "$fallback" "$image"
  exit 0
fi
echo "Failed to pull MongoDB from both $image and $fallback" >&2
exit 1
