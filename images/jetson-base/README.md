# Jetson Base Images

Base container images for NVIDIA Jetson devices. These are built infrequently and
consumed by the fleet k3s service (`fleet/k3s/Dockerfile.jetson`).

## Why base images?

Installing NVIDIA packages on Jetson is slow — large downloads from
`repo.download.nvidia.com`, many dependencies, and ldconfig updates. By building
this layer once and publishing it to GHCR, the fleet builds that run on every push
just pull a cached base and add k3s on top.

## What's installed

Each image starts from a stock Ubuntu base (no balenalib) and adds:

**L4T SoC packages** (`nvidia-l4t-*`) — the board support package for the specific
Jetson SoC. These provide the Tegra driver stack, firmware, multimedia codecs,
camera HAL, and GPU libraries. They come from the SoC-specific apt repo
(`jetson/<soc>/dists/<dist>/main`).

**CUDA toolkit and ML libraries** — CUDA, cuDNN, and TensorRT, so that containers
scheduled by k3s can access GPU compute. These come from the common apt repo
(`jetson/common/dists/<dist>/main`).

**NVIDIA Container Toolkit** — enables GPU passthrough into containers that k3s
schedules on the device. JetPack 4 uses CSV-based passthrough
(`nvidia-container-csv-*`), while JetPack 5+ uses `nvidia-container` for device
discovery.

**Tegra ldconfig** — `/usr/lib/aarch64-linux-gnu/tegra` (and `tegra-egl` on
JetPack 5+) are added to `ld.so.conf.d` so GPU libraries are found at runtime.

## What's NOT installed

- **k3s** — added by the fleet Dockerfile
- **Application code** — added by the fleet coordinator/wireguard services
- **Kernel modules** — provided by the host OS (balenaOS)

## Supported devices

| Device | SoC | JetPack | L4T | Ubuntu | Dockerfile | Image tag |
|--------|-----|---------|-----|--------|------------|-----------|
| Jetson Nano | t210 | 4 | r32.7 | 18.04 | jetpack4.Dockerfile | `t210-r32.7` |
| Xavier NX | t194 | 5 | r35.6 | 20.04 | jetpack5.Dockerfile | `t194-r35.6` |
| Orin Nano / AGX Orin | t234 | 6 | r36.5 | 22.04 | jetpack6.Dockerfile | `t234-r36.5` |

## Building

Build all images in parallel:

```bash
docker buildx create --name jetson-builder --driver docker-container --use
docker buildx bake -f docker-bake.hcl
```

Build and push:

```bash
docker buildx bake -f docker-bake.hcl --push
```

Build a single target:

```bash
docker buildx bake -f docker-bake.hcl orin
```

## Package naming across JetPack generations

JetPack 6 introduced the "upgradable compute stack" which renamed many packages:

| JetPack 4/5 | JetPack 6 |
|-------------|-----------|
| `cuda-toolkit-10-2` / `cuda-toolkit-11-4` | `nvidia-cuda` |
| `libcudnn8` / `libcudnn9-cuda-12` | `nvidia-cudnn8` |
| `tensorrt-libs` | `nvidia-tensorrt` |
| `nvidia-container-csv-*` | `nvidia-container` |
| `nvidia-l4t-libvulkan` | removed |
| `nvidia-l4t-gstreamer` | deprecated |
