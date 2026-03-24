# JetPack 4 (L4T r32, CUDA 10.2) — Jetson Nano
#   docker build -f jetpack4.Dockerfile --build-arg SOC=t210 .
#   docker build -f jetpack4.Dockerfile --build-arg SOC=t210 --target full .
FROM ubuntu:18.04 AS base

ARG SOC=t210
ARG L4T_VERSION=r32.7
ARG REPO_BASE=https://repo.download.nvidia.com/jetson

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "${REPO_BASE}/jetson-ota-public.asc" | apt-key add - \
    && echo "deb ${REPO_BASE}/${SOC} ${L4T_VERSION} main" > /etc/apt/sources.list.d/nvidia-l4t-soc.list \
    && echo "deb ${REPO_BASE}/common ${L4T_VERSION} main" > /etc/apt/sources.list.d/nvidia-l4t-common.list

# nvidia-l4t-core's preinst script checks /proc/device-tree/compatible to
# verify it's on a Jetson. This marker file tells it to skip that check.
# https://gitlab.com/nvidia/container-images/l4t-base
RUN mkdir -p /opt/nvidia/l4t-packages/ \
    && touch /opt/nvidia/l4t-packages/.nv-l4t-disable-boot-fw-update-in-preinstall

# L4T BSP packages: https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-3276/index.html
# Container toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
RUN apt-get update && apt-get install -y --no-install-recommends \
    nvidia-l4t-cuda \
    nvidia-l4t-firmware \
    nvidia-l4t-init \
    nvidia-container-toolkit \
    && rm -rf /var/lib/apt/lists/*

# CUDA runtime libraries for GPU workloads (cudart, cublas, cufft, curand,
# cusolver, cusparse, npp, nvrtc, nvgraph).
RUN apt-get update && apt-get install -y --no-install-recommends \
    cuda-libraries-10-2 \
    && rm -rf /var/lib/apt/lists/*

# The nvidia container runtime reads CSV files to know which paths to mount
# into containers. The nvidia-container-csv-cuda package provides this but
# depends on cuda-toolkit-10-2 (~3GB). Write it directly instead.
RUN mkdir -p /etc/nvidia-container-runtime/host-files-for-container.d \
    && echo "dir, /usr/local/cuda-10.2" > /etc/nvidia-container-runtime/host-files-for-container.d/cuda.csv

RUN echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf \
    && ldconfig

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all
