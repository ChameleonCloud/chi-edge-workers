#!/bin/sh
set -o errexit
set -o nounset

# Balena will mount a socket and set DOCKER_HOST to
# point to the socket path.
if [ -n "${DOCKER_HOST:-}" ]; then
  echo "Shimming $DOCKER_HOST socket"
  # for containerd
  mkdir -p /run/k3s/containerd
  ln -sf "${DOCKER_HOST##unix://}" /run/k3s/containerd/containerd.sock
  # for Docker, if used instead
  ln -sf "${DOCKER_HOST##unix://}" /var/run/docker.sock
fi

exec k3s agent \
  --kubelet-arg=cgroup-driver=systemd \
  --kubelet-arg=cgroups-per-qos=false \
  --kubelet-arg=enforce-node-allocatable= \
  --kubelet-arg=volume-plugin-dir=/opt/libexec/kubernetes/kubelet-plugins/volume/exec
  "$@"
