#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
REGISTRY="${REGISTRY:-ghcr.io/chameleoncloud/chi-edge-workers}"

build() {
  local soc=$1 l4t=$2 ubuntu=$3 cuda=$4
  echo "Building ${soc}-${l4t}"
  docker buildx build \
    --build-arg SOC="$soc" \
    --build-arg L4T_VERSION="$l4t" \
    --build-arg UBUNTU="$ubuntu" \
    --build-arg CUDA_VERSION="$cuda" \
    --platform linux/arm64 \
    --tag "${REGISTRY}/jetson-base:${soc}-${l4t}" \
    "$DIR"
}

build t210 r32.7 18.04 10.2
build t194 r32.7 18.04 10.2
build t234 r36.4 22.04 12.6
