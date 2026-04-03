# GPU Support Configuration Matrix

## The Problem

Three components must agree on how GPU devices are identified and passed
to containers:

1. **nvidia-container-toolkit** — the container runtime that injects GPU
   access into containers
2. **k8s-device-plugin** — discovers GPUs, tells kubelet about them, and
   injects device info into pods
3. **k3s/containerd** — orchestrates container creation, forwards runtime
   config

On Tegra (Jetson) platforms there is no NVML — device discovery and GPU
injection work differently than on discrete GPUs.

## Tested Configurations

### Configuration A: toolkit ≤ 1.17.x + device plugin v0.14.1 (WORKING)

| Component | Version | Setting |
|---|---|---|
| nvidia-container-toolkit | ≤ 1.17.9 | `mode = "auto"` (defaults to legacy on Tegra) |
| k8s-device-plugin | v0.14.1 | `deviceListStrategy: envvar` |
| k3s | v1.29.x | `--default-runtime=nvidia` |

**How it works:** The v0.14.1 plugin detects Tegra via `/etc/nv_tegra_release`
(accessible from within the pod on k3s), discovers a single `tegra` device,
and sets `NVIDIA_VISIBLE_DEVICES=tegra` on scheduled pods. The ≤ 1.17.x
runtime uses a legacy prestart hook that understands `tegra` as a device ID
and mounts GPU libraries via CSV files.

**Why it works:** The legacy prestart hook in ≤ 1.17.x uses
`libnvidia-container0` (.so.0) which natively understands the `tegra`
device identifier.

### Configuration B: toolkit 1.18.x+ + device plugin v0.14.1 (BROKEN)

| Component | Version | Setting |
|---|---|---|
| nvidia-container-toolkit | ≥ 1.18.0 | any mode |
| k8s-device-plugin | v0.14.1 | `deviceListStrategy: envvar` |

**Why it fails:** Starting with v1.18.0, the toolkit uses "just-in-time CDI
spec generation" instead of the legacy prestart hook. The device plugin still
passes `NVIDIA_VISIBLE_DEVICES=tegra`, but the JIT CDI generator does not
recognize `tegra` as a valid device ID.

- `mode = "auto"`: tries CDI, fails with `unsupported device id: tegra`
- `mode = "csv"`: still uses JIT CDI generation internally, same error
- `mode = "legacy"`: needs `libnvidia-container.so.0`, which was removed
  in v1.19.0

### Configuration C: toolkit 1.19.x + device plugin v0.19.0 (UNTESTED)

| Component | Version | Setting |
|---|---|---|
| nvidia-container-toolkit | 1.19.x | `mode = "auto"` |
| k8s-device-plugin | v0.19.0 | `deviceListStrategy: cdi-annotations` |
| k3s | v1.29.x | `--default-runtime=nvidia` |

**Theory:** The v0.19.0 plugin would send proper CDI device names
(`nvidia.com/gpu=0`) instead of `tegra`, which the v1.19.0 runtime
understands. However, the v0.19.0 plugin requires Tegra platform detection
files mounted into its pod:

- `/etc/nv_tegra_release` — identifies the platform as Tegra
- `/sys/devices/soc0/family` — used by newer platform detection logic

The plugin also needs `NVIDIA_VISIBLE_DEVICES=void` so the nvidia runtime
skips GPU injection for the plugin pod itself.

**CDI spec generation:** Must run before k3s starts:
```
nvidia-ctk cdi generate --mode=csv --output=/var/run/cdi/nvidia.yaml
```

The `--mode=csv` flag is required because auto mode incorrectly selects
nvml on Tegra ([forum reference](https://forums.developer.nvidia.com/t/podman-gpu-on-jetson-agx-orin/297734/10)).

**Open question:** Does the v0.19.0 plugin also need `/var/run/cdi` mounted
to read the CDI spec, or does it only need the platform detection files?

## Key Version Boundaries

| Version | Change |
|---|---|
| toolkit v1.10.0 | CSV mode added for Tegra |
| toolkit v1.15.0 | `nvidia-container-runtime` package removed, consolidated into toolkit |
| toolkit v1.17.4 | CUDA compat mounting disabled by default |
| toolkit v1.18.0 | Legacy mode deprecated; JIT CDI spec generation becomes default |
| toolkit v1.19.0 | `libnvidia-container0` (.so.0) removed; legacy mode no longer functional |
| device-plugin v0.14.1 | Last version with simple Tegra detection via `/etc/nv_tegra_release` |
| device-plugin v0.15.0 | `cdi-cri` strategy added |
| device-plugin v0.19.0 | Tegra detection uses `/sys/devices/soc0/family`; requires CDI |
| k8s v1.29 | CDIDevices API beta (enabled by default) |

## start.sh Configuration

For **Configuration A** (toolkit ≤ 1.17.x), start.sh needs no nvidia-specific
setup — the legacy hook handles everything.

For **Configuration C** (toolkit 1.19.x), start.sh needs:
```sh
if command -v nvidia-ctk >/dev/null 2>&1; then
  nvidia-ctk runtime configure --runtime=containerd
  mkdir -p /var/run/cdi
  nvidia-ctk cdi generate --mode=csv --output=/var/run/cdi/nvidia.yaml
fi
```

## References

- [NVIDIA Container Toolkit runtime modes](https://github.com/NVIDIA/nvidia-container-toolkit)
- [CDI on Jetson (forum)](https://forums.developer.nvidia.com/t/podman-gpu-on-jetson-agx-orin/297734/10)
- [k8s-device-plugin Tegra manager](https://github.com/NVIDIA/k8s-device-plugin/blob/main/internal/rm/tegra_manager.go)
- [k3s GPU support](https://docs.k3s.io/advanced)
- [CDIDevices KEP-4009](https://github.com/kubernetes/enhancements/tree/master/keps/sig-node/4009-add-cdi-devices-to-device-plugin-api)
