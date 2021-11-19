#!/bin/sh

# Balena will mount a socket and set DOCKER_HOST to
# point to the socket path.
if [ -n "$DOCKER_HOST" ]; then
  ln -sf "${DOCKER_HOST##unix://}" /var/run/docker.sock 
fi

exec k3s "$@"
