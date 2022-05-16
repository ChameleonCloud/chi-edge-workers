![logo](./chi-edge-raspberrypi-logo.png)

# chi-edge-workers

## Wireguard kernel module build

The Wireguard kernel module is available on most newer kernels. However, some Balena
device types are sufficiently old as to not include it. The `install-wireguard.sh` will
lazily attempt to compile the kernel module on build.

Because builds will usually NOT happen on the target device, we will not be able to
reliably detect support for Wireguard in the kernel. Therefore, each type of device that
needs a custom build should be added to the `case` statement to point to the latest
available kernel header file. **N.B.**: the version is always the Balena kernel version
with a ".dev" suffix, from what I can tell.

## Balena guide

K3s agent state is stored in a Docker volume on the Balena host; this is helpful not
only because it means the state is not stored wastefully in an overlay filesystem, but
also means it persists across deployments. This also means that additional state may
need to be cleaned up if, e.g., the control plane radically changes and a fresh node
enrollment is appropriate. "Purge device" will clean up Docker volumes on the Balena
host to help with this.
