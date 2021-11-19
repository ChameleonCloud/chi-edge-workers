#!/bin/sh

if [ -n "$BALENA_SOCK" ]; then
  ln -sf /var/run/docker.sock $BALENA_SOCK
fi

exec k3s "$@"
