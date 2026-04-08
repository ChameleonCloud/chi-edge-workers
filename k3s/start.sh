#!/bin/sh
set -o errexit
set -o nounset

# If cgroups v2 are enabled, ensure nesting compatibility.
# NOTE: this may not be necessary anymore in K3s due to
# https://github.com/k3s-io/k3s/pull/4086
#########################################################################################################################################
# DISCLAIMER																																																														#
# Copied from https://github.com/moby/moby/blob/ed89041433a031cafc0a0f19cfe573c31688d377/hack/dind#L28-L37															#
# Permission granted by Akihiro Suda <akihiro.suda.cz@hco.ntt.co.jp> (https://github.com/rancher/k3d/issues/493#issuecomment-827405962)	#
# Moby License Apache 2.0: https://github.com/moby/moby/blob/ed89041433a031cafc0a0f19cfe573c31688d377/LICENSE														#
#########################################################################################################################################
if [ -f /sys/fs/cgroup/cgroup.controllers ]; then
	# move the processes from the root group to the /init group,
  # otherwise writing subtree_control fails with EBUSY.
  mkdir -p /sys/fs/cgroup/init
  if command -v busybox >/dev/null 2>&1; then
    busybox xargs -rn1 < /sys/fs/cgroup/cgroup.procs > /sys/fs/cgroup/init/cgroup.procs || :
  else
    xargs -rn1 < /sys/fs/cgroup/cgroup.procs > /sys/fs/cgroup/init/cgroup.procs || :
  fi
  # enable controllers
  sed -e 's/ / +/g' -e 's/^/+/' <"/sys/fs/cgroup/cgroup.controllers" >"/sys/fs/cgroup/cgroup.subtree_control"
fi

# Generate CDI spec from CSV mount files so the nvidia runtime knows what
# to inject into user containers. Must run at boot (needs /dev populated).
if command -v nvidia-ctk >/dev/null 2>&1; then
  nvidia-ctk cdi generate --mode=csv --output=/var/run/cdi/nvidia.yaml
  echo "CDI spec generated at /var/run/cdi/nvidia.yaml"
fi

# looking up IP address from wireguard interface
WG_ADDRESS="$(ip -brief address show wg-calico | awk '{print $3}' | cut -d '/' -f 1)"
if [ -z "${WG_ADDRESS}" ]; then
  echo "FATAL: wg-calico has no address, refusing to start k3s"
  exit 1
fi

k3s agent \
  --bind-address "${WG_ADDRESS}" \
  --node-ip "${WG_ADDRESS}" \
  --kubelet-arg=volume-plugin-dir=/opt/libexec/kubernetes/kubelet-plugins/volume/exec \
  "$@"
