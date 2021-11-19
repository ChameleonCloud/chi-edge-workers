#!/bin/sh

# Balena will mount a socket and set DOCKER_HOST to
# point to the socket path.
if [ -n "$DOCKER_HOST" ]; then
  mkdir -p /run/k3s/containerd
  ln -sf "${DOCKER_HOST##unix://}" /run/k3s/containerd/containerd.sock
fi

exec k3s "$@"
