# Running k3s inside a container, on Balena, with Calico

This document records every load-bearing detail required to run k3s as
a Balena service with Calico networking over WireGuard tunnels. Each
section explains *what*, *why*, and the commit(s) that discovered it.

---

## cgroupv2 nesting (entrypoint.sh)

k3s (via containerd) needs to create child cgroups. When the host uses
cgroupv2 (unified hierarchy), the root cgroup's `cgroup.subtree_control`
must have controllers enabled — but you can't write to it while processes
sit in the root cgroup. The fix: evacuate all processes to `/init`, then
enable controllers.

```sh
mkdir -p /sys/fs/cgroup/init
xargs -rn1 < /sys/fs/cgroup/cgroup.procs > /sys/fs/cgroup/init/cgroup.procs || :
sed -e 's/ / +/g' -e 's/^/+/' \
  < /sys/fs/cgroup/cgroup.controllers \
  > /sys/fs/cgroup/cgroup.subtree_control
```

This is adapted from the Moby project's DinD script. License and
permission are documented inline in `k3s/entrypoint.sh`.

**History:** `999bdcf` — cgroupv2 support.

## mount --make-rshared /

Calico and kubelet require mount propagation to function (e.g., for
pod volume mounts to be visible across mount namespaces). Inside a
container the root mount may default to `private`. Without `rshared`,
kubelet will fail to mount volumes into pods, and Calico's felix
will fail health checks.

**History:** discovered on the `wip/cleaner_fleet` branch.

## privileged mode

k3s needs privileged for: creating network namespaces (Calico pods),
mounting filesystems (kubelet), managing iptables/nftables rules, and
loading kernel modules. There is no useful subset of capabilities that
works — `privileged: true` is required.

## network_mode: host

k3s agent must see the host network stack. It binds to the WireGuard
tunnel address, manages iptables rules for Calico, and the kubelet
needs direct access to host interfaces. Bridge/NAT networking breaks
all of this.

## WireGuard tunnel binding

k3s must bind to the WireGuard interface address, not any host address.
The edge devices communicate with the control plane and with each other
exclusively over WireGuard tunnels (wg-calico). The entrypoint looks up
the address at startup:

```sh
WG_ADDRESS="$(ip -brief address show wg-calico | awk '{print $3}' | cut -d '/' -f 1)"
```

Both `--bind-address` and `--node-ip` must be set to this address.
Without `--node-ip`, k3s will advertise a LAN address that other nodes
can't reach. Without `--bind-address`, the kubelet API server listens
on the wrong interface.

**Critical guard:** If `WG_ADDRESS` is empty (e.g., coordinator hasn't
configured WireGuard yet, or WireGuard is restarting), k3s must NOT
start. Starting with an empty bind address causes k3s to bind to
0.0.0.0, which it then advertises to the cluster. The node becomes
unreachable and does not self-heal — k3s doesn't re-read its bind
address. Balena's `restart: always` will retry until the tunnel is up.

**History:** `47e30cb` — bind k3s to wireguard address.
`2ad00a6` — refuse to start without a wireguard address.
`3096385` — remove depends_on (coordinator restarts k3s after tunnel changes).
`012b894` — coordinator restarts k3s service when tunnel changes.

## No depends_on for k3s → wireguard

The WireGuard tunnel is configured by the coordinator service, not by
the wireguard container's startup. The wireguard container just loads
kernel modules and brings up the interface — the address is written
later by the coordinator. A `depends_on` on wireguard would not
guarantee the tunnel has an address, and would prevent the coordinator
from restarting k3s when tunnel config changes.

**History:** `3096385` — removed depends_on.

## Volume mounts (docker-compose.yml)

### k3s_data_dir → /var/lib/rancher/k3s

The k3s data directory. Contains: downloaded images, containerd state,
CNI plugin binaries that k3s manages, etcd data (if server), and
certificates. Without persistence, every container restart re-downloads
all images and re-bootstraps the node. This is the most important volume.

**History:** `85f00c3` — mount data dir as volume to move off overlay fs.

### k3s_node_dir → /etc/rancher

k3s node configuration and registration token. Losing this forces
re-registration with the server, which can leave orphaned node objects
in the cluster.

### k3s_kubelet_dir → /var/lib/kubelet

Kubelet state: pod checkpoints, device plugins, CPU manager state.
Persisting this avoids full pod reconciliation on restart.

### calico_data_dir → /var/lib/calico

Calico's felix and node state. Includes the assigned IPAM blocks for
this node. Losing this can cause IP address conflicts when Calico
reassigns blocks.

### k3s_cni_net → /etc/cni/net.d

Calico-written CNI configuration files. Without persistence, Calico
must regenerate config on every start, during which pods cannot get
network.

### k3s_cni_bin → /opt/cni/bin

CNI plugin binaries (calico, calico-ipam, etc). These are downloaded
by the Calico DaemonSet. Without persistence, every restart
re-downloads ~50MB of binaries on a potentially slow edge connection.

### k3s_cni_log → /var/log/calico

Calico CNI plugin logs. Useful for debugging pod network failures.
Not strictly required for operation but very helpful for diagnosing
issues on remote edge devices where you can't easily SSH in.

### k3s_flexvol → /opt/libexec/kubernetes/kubelet-plugins/volume/exec

Legacy flexvolume plugin directory. Used by Calico for `flexvol-driver`
which allows Calico to install its CNI config. While flexvol is
deprecated in favor of CSI, Calico still uses it in some configurations.

**History:** `fd1a508` — added calico volumes. `d0e9794` — cleanup that preserved them.

### wireguard_etc → /etc/wireguard

Shared between the wireguard and coordinator containers. The coordinator
writes WireGuard config files here; the wireguard container reads them.
This is the coordination mechanism between the two services.

## tmpfs mounts

### /run/k3s

k3s runtime state: containerd socket, k3s agent socket. Must be tmpfs
because this state is invalid across container restarts.

### /run/containerd

containerd's runtime socket and state. Same reason as /run/k3s.

### /run/calico, /run/nodeagent

Calico felix runtime state and the nodeagent socket (used for Calico
IPAM communication). Must be fresh on each start.

## ulimits (nproc, nofile)

k3s + containerd + kubelet + calico collectively can easily exhaust
default ulimits (1024). Each pod gets its own set of processes and
file descriptors. 65535 is standard for Kubernetes nodes.

## restart: always

k3s must survive transient failures: WireGuard tunnel not ready yet,
temporary loss of connectivity to the control plane, OOM kills of
containerd. Balena's restart policy handles this.

## Kernel modules

### WireGuard (wireguard.ko)

Required for the VPN tunnels. On modern kernels (5.6+), WireGuard is
built into the kernel. On older balenaOS releases and Jetson devices
with older kernels (4.9), it had to be compiled from source against
the specific kernel headers. The wireguard container uses the
`io.balena.features.kernel-modules` label to get access to
`/lib/modules` on the host for `modprobe`.

**History:** `6d5c103` — first wireguard addition. `ce5471d` — switched
from bind mount to kernel-modules label. `d7a36a7` — don't detect
kernel support at build time (build host != target device).
`0436473` — rpi4 has wireguard in-tree, skip building.

### IPIP (ipip.ko, tunnel4.ko)

Calico's default encapsulation mode uses IP-in-IP tunneling. On most
kernels this is built-in. On Jetson L4T 32.7.x kernels, it was missing
and had to be compiled from kernel source. The `ipip/src/` directory
contained the kernel module source for this.

**History:** `6b8052a` — build ipip module for jetson platforms.

## Balena labels

### io.balena.features.kernel-modules: "1" (wireguard)

Gives the container access to `/lib/modules` on the host, enabling
`modprobe wireguard`. Without this, the wireguard container cannot
load the kernel module.

### io.balena.features.supervisor-api: "1" (coordinator)

Gives the coordinator access to the Balena supervisor API. Used to
restart the k3s service when WireGuard tunnel configuration changes,
and to read device metadata (device name, type, etc).

## What was tried and abandoned

### systemd inside the container

Early versions ran systemd as PID 1 inside the k3s container, with k3s
as a systemd service. This was needed because k3s assumed a systemd
cgroup driver. It was removed because: it added enormous complexity,
required masking many systemd units, and broke regularly with balenaOS
updates. The cgroupv2 nesting fix made it unnecessary.

**History:** `f698ca9` (add systemd) → `e443e0b` ("this works!" with
systemd+k3s service) → `d0e9794` (remove systemd, direct exec).

### procfs / sysfs / host PID namespace

Multiple attempts were made to mount `/proc` and `/sys` from the host,
and to use `pid: host`. All were reverted. Mounting host procfs caused
conflicts with balena's own process management. Host PID namespace
leaked balena supervisor processes into the container. `privileged: true`
already provides the necessary access.

**History:** `1d3881b` → `dcf3d97` → `92e1a79` → `8ee6178` (procfs/sysfs).
`c6bb7a6` → `c9c9fea` → `a9988d7` (host pid). `5099b4d` (final revert).

### Docker CRI (vs containerd)

k3s was briefly switched to use Docker as its container runtime (via the
`--docker` flag). This required the balena socket symlink. It was
abandoned in favor of k3s's built-in containerd because Docker added
an unnecessary layer and the balena socket shimming was fragile.

**History:** `e30e76f` → `5910094` → `c6edb63` (back to containerd).

### balena-socket symlink

The balena engine exposes a Docker-compatible socket. Early versions
created a symlink from the balena socket to `/var/run/docker.sock` or
`/run/k3s/containerd/containerd.sock`. This was removed when switching
to k3s's built-in containerd, which manages its own socket.

**History:** `175a751` → `2c35954` → `6c9f921` → `d0e9794` (removed).

### dbus label

Used with the systemd approach to give k3s access to the host dbus
socket for cgroup management. Removed along with systemd.

**History:** `990b403` → `d0e9794`.

## Coordinator behavior notes

The coordinator container manages WireGuard tunnel lifecycle:
- Reads tunnel configuration from the CHI@Edge control plane (OpenStack)
- Writes WireGuard config files to the shared `/etc/wireguard` volume
- Brings up/down WireGuard interfaces via the `wg` tool
- Restarts the k3s service via the Balena supervisor API when tunnel
  config changes (because k3s binds to the tunnel address at startup
  and does not detect address changes)

Changing the node's WireGuard IP requires deleting and re-registering
the node in Kubernetes. See: https://kubernetes.io/docs/concepts/architecture/nodes/#node-name-uniqueness

**History:** `012b894` — restart k3s when tunnel changes.
`d6e0b22` — hostname update support (disabled by default, restarts
Docker engine which is destructive).
