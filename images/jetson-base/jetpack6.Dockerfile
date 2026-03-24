# JetPack 6 (L4T r36, CUDA 12.6) — Orin Nano / AGX Orin
#   docker build -f jetpack6.Dockerfile --build-arg SOC=t234 .
#   docker build -f jetpack6.Dockerfile --build-arg SOC=t234 --target full .
FROM ubuntu:22.04 AS base

ARG SOC=t234
ARG L4T_VERSION=r36.4
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

# L4T BSP packages: https://docs.nvidia.com/jetson/archives/r36.4/DeveloperGuide/SD/SoftwarePackagesAndTheUpdateMechanism.html
# Container toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
RUN apt-get update && apt-get install -y --no-install-recommends \
    nvidia-l4t-cuda \
    nvidia-l4t-firmware \
    nvidia-l4t-init \
    nvidia-container-toolkit \
    && rm -rf /var/lib/apt/lists/*

RUN echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf \
    && echo "/usr/lib/aarch64-linux-gnu/tegra-egl" >> /etc/ld.so.conf.d/nvidia-tegra.conf \
    && ldconfig

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all
