# chi-edge

## Balena guide

K3s agent state is stored in a Docker volume on the Balena host; this is helpful not only because it means the state is not stored wastefully in an overlay filesystem, but also means it persists across deployments. This also means that additional state may need to be cleaned up if, e.g., the control plane radically changes and a fresh node enrollment is appropriate. "Purge device" will clean up Docker volumes on the Balena host to help with this.
