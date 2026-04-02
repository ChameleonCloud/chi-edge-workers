# Jetson base image
#   Jetson Nano (t210):  --build-arg UBUNTU=18.04 --build-arg SOC=t210 --build-arg L4T_VERSION=r32.7 --build-arg CUDA=10-2 --build-arg CUDA_VERSION=10.2
#   Xavier NX   (t194):  --build-arg UBUNTU=18.04 --build-arg SOC=t194 --build-arg L4T_VERSION=r32.7 --build-arg CUDA=10-2 --build-arg CUDA_VERSION=10.2
#   Orin Nano   (t234):  --build-arg UBUNTU=22.04 --build-arg SOC=t234 --build-arg L4T_VERSION=r36.4 --build-arg CUDA=12-6 --build-arg CUDA_VERSION=12.6
ARG UBUNTU=22.04
FROM ubuntu:${UBUNTU} AS base

ARG SOC=t234
ARG L4T_VERSION=r36.4
ARG CUDA=12-6
ARG CUDA_VERSION=12.6
ARG NVIDIA_CONTAINER_TOOLKIT_VERSION=1.17.9-1
ARG REPO_BASE=https://repo.download.nvidia.com/jetson

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg \
    && rm -rf /var/lib/apt/lists/*

# L4T BSP repo (nvidia-l4t-* packages)
RUN curl -fsSL "${REPO_BASE}/jetson-ota-public.asc" | apt-key add - \
    && echo "deb ${REPO_BASE}/${SOC} ${L4T_VERSION} main" > /etc/apt/sources.list.d/nvidia-l4t-soc.list \
    && echo "deb ${REPO_BASE}/common ${L4T_VERSION} main" > /etc/apt/sources.list.d/nvidia-l4t-common.list

# Container toolkit repo (nvidia-container-toolkit, libnvidia-container)
# https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
RUN curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
    && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    > /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Skip Jetson device-tree check during nvidia-l4t-core install.
# https://gitlab.com/nvidia/container-images/l4t-base
RUN mkdir -p /opt/nvidia/l4t-packages/ \
    && touch /opt/nvidia/l4t-packages/.nv-l4t-disable-boot-fw-update-in-preinstall

RUN apt-get update && apt-get install -y --no-install-recommends \
    nvidia-l4t-cuda \
    nvidia-l4t-firmware \
    nvidia-l4t-init \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    cuda-libraries-${CUDA} \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    nvidia-container-toolkit=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
    nvidia-container-toolkit-base=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
    libnvidia-container-tools=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
    libnvidia-container1=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
    && rm -rf /var/lib/apt/lists/*

# The nvidia-container-toolkit only reads devices.csv, drivers.csv, and l4t.csv
# by default (see internal/platform-support/tegra/csv/csv.go DefaultFileList).
# Add CUDA toolkit directory to l4t.csv so it gets mounted into containers.
RUN mkdir -p /etc/nvidia-container-runtime/host-files-for-container.d \
    && echo "dir, /usr/local/cuda-${CUDA_VERSION}" > /etc/nvidia-container-runtime/host-files-for-container.d/l4t.csv

RUN echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf \
    && echo "/usr/lib/aarch64-linux-gnu/tegra-egl" >> /etc/ld.so.conf.d/nvidia-tegra.conf \
    && ldconfig

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all
