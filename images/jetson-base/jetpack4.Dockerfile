# JetPack 4 (L4T r32, CUDA 10.2) — Jetson Nano
#   docker build -f jetpack4.Dockerfile --build-arg SOC=t210 .
#   docker build -f jetpack4.Dockerfile --build-arg SOC=t210 --target full .
FROM ubuntu:18.04 AS base

ARG SOC=t210
ARG REPO_BASE=https://repo.download.nvidia.com/jetson

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "${REPO_BASE}/jetson-ota-public.asc" | apt-key add - \
    && echo "deb ${REPO_BASE}/${SOC} r32.7 main" > /etc/apt/sources.list.d/nvidia-l4t-soc.list \
    && echo "deb ${REPO_BASE}/common r32.7 main" > /etc/apt/sources.list.d/nvidia-l4t-common.list

# nvidia-l4t-core's preinst script checks /proc/device-tree/compatible to
# verify it's on a Jetson. This marker file tells it to skip that check.
# https://gitlab.com/nvidia/container-images/l4t-base
RUN mkdir -p /opt/nvidia/l4t-packages/ \
    && touch /opt/nvidia/l4t-packages/.nv-l4t-disable-boot-fw-update-in-preinstall

RUN apt-get update && apt-get install -y --no-install-recommends \
    nvidia-l4t-core \
    nvidia-l4t-cuda \
    nvidia-l4t-firmware \
    nvidia-l4t-init \
    nvidia-container-toolkit \
    libnvidia-container-tools \
    libnvidia-container1 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get download nvidia-container-csv-cuda \
    && dpkg --force-depends -i nvidia-container-csv-cuda*.deb \
    && rm -f nvidia-container-csv-cuda*.deb \
    && rm -rf /var/lib/apt/lists/*

RUN echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf \
    && ldconfig

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all

# ---------- optional: multimedia, graphics, ML libs ----------
FROM base AS full

RUN apt-get update && apt-get install -y --no-install-recommends \
    nvidia-l4t-3d-core \
    nvidia-l4t-multimedia \
    nvidia-l4t-multimedia-utils \
    nvidia-l4t-camera \
    nvidia-l4t-libvulkan \
    nvidia-l4t-gstreamer \
    nvidia-l4t-x11 \
    cuda-toolkit-10-2 \
    nvidia-container-csv-cudnn \
    nvidia-container-csv-tensorrt \
    nvidia-container-csv-visionworks \
    && rm -rf /var/lib/apt/lists/*
