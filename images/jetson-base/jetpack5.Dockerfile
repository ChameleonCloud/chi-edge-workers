# JetPack 5 (L4T r35, CUDA 11.4) — Xavier NX
#   docker build -f jetpack5.Dockerfile --build-arg SOC=t194 .
#   docker build -f jetpack5.Dockerfile --build-arg SOC=t194 --target full .
FROM ubuntu:20.04 AS base

ARG SOC=t194
ARG REPO_BASE=https://repo.download.nvidia.com/jetson

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "${REPO_BASE}/jetson-ota-public.asc" | apt-key add - \
    && echo "deb ${REPO_BASE}/${SOC} r35.6 main" > /etc/apt/sources.list.d/nvidia-l4t-soc.list \
    && echo "deb ${REPO_BASE}/common r35.6 main" > /etc/apt/sources.list.d/nvidia-l4t-common.list

# nvidia-l4t-core's preinst script greps /proc/device-tree/compatible for
# "nvidia" to verify it's running on a Jetson. This doesn't exist in docker
# builds, so we stub it.
# https://forums.developer.nvidia.com/t/installing-nvidia-l4t-core-package-in-a-docker-layer/153412
RUN mkdir -p /proc/device-tree && echo -n "nvidia" > /proc/device-tree/compatible

RUN apt-get update && apt-get install -y --no-install-recommends \
    nvidia-l4t-core \
    nvidia-l4t-cuda \
    nvidia-l4t-firmware \
    nvidia-l4t-init \
    nvidia-container-toolkit \
    libnvidia-container-tools \
    libnvidia-container1 \
    nvidia-container \
    && rm -rf /var/lib/apt/lists/*

RUN echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf \
    && echo "/usr/lib/aarch64-linux-gnu/tegra-egl" >> /etc/ld.so.conf.d/nvidia-tegra.conf \
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
    nvidia-l4t-nvsci \
    nvidia-l4t-pva \
    cuda-toolkit-11-4 \
    libcudnn8 \
    tensorrt-libs \
    && rm -rf /var/lib/apt/lists/*
