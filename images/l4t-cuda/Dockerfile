#   r32.7 / CUDA 10.2:  UBUNTU=18.04 L4T_VERSION=r32.7 CUDA=10-2 CUDA_VERSION=10.2
#   r36.4 / CUDA 12.6:  UBUNTU=22.04 L4T_VERSION=r36.4 CUDA=12-6 CUDA_VERSION=12.6
ARG UBUNTU=22.04
FROM ubuntu:${UBUNTU} AS base

ARG L4T_VERSION=r36.4
ARG CUDA=12-6
ARG CUDA_VERSION=12.6

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://repo.download.nvidia.com/jetson/jetson-ota-public.asc" | apt-key add - \
    && echo "deb https://repo.download.nvidia.com/jetson/common ${L4T_VERSION} main" \
        > /etc/apt/sources.list.d/nvidia-l4t-common.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    cuda-libraries-${CUDA} \
    && rm -rf /var/lib/apt/lists/*

RUN echo "/usr/local/cuda-${CUDA_VERSION}/lib64" > /etc/ld.so.conf.d/cuda.conf \
    && ldconfig

ENV LD_LIBRARY_PATH=/usr/local/cuda-${CUDA_VERSION}/lib64
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all

# --- devel: compiler + dev headers for user build stages ---
FROM base AS devel

ARG CUDA=12-6
ARG CUDA_VERSION=12.6

RUN apt-get update && apt-get install -y --no-install-recommends \
    cuda-cudart-dev-${CUDA} \
    cuda-nvcc-${CUDA} \
    g++ \
    libcublas-dev-${CUDA} \
    make \
    && rm -rf /var/lib/apt/lists/*

ENV CUDA_HOME=/usr/local/cuda-${CUDA_VERSION}
ENV PATH="${CUDA_HOME}/bin:${PATH}"

# --- infra: SOC l4t platform libs + nvidia-container-toolkit for GPU injection ---
#   t210:  SOC=t210 L4T_VERSION=r32.7 CUDA_VERSION=10.2
#   t194:  SOC=t194 L4T_VERSION=r32.7 CUDA_VERSION=10.2
#   t234:  SOC=t234 L4T_VERSION=r36.4 CUDA_VERSION=12.6
FROM base AS infra

ARG SOC=t234
ARG L4T_VERSION=r36.4
ARG CUDA_VERSION=12.6
ARG NVIDIA_CONTAINER_TOOLKIT_VERSION=1.19.0-1

# SOC-specific L4T platform libraries
RUN echo "deb https://repo.download.nvidia.com/jetson/${SOC} ${L4T_VERSION} main" \
        > /etc/apt/sources.list.d/nvidia-l4t-soc.list \
    && mkdir -p /opt/nvidia/l4t-packages/ \
    && touch /opt/nvidia/l4t-packages/.nv-l4t-disable-boot-fw-update-in-preinstall

RUN apt-get update && apt-get install -y --no-install-recommends \
    nvidia-l4t-cuda \
    nvidia-l4t-firmware \
    nvidia-l4t-init \
    nvidia-l4t-tools \
    && rm -rf /var/lib/apt/lists/*

RUN echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf \
    && echo "/usr/lib/aarch64-linux-gnu/tegra-egl" >> /etc/ld.so.conf.d/nvidia-tegra.conf \
    && ldconfig

# nvidia-container-toolkit (mounts host CUDA + tegra libs into user containers)
RUN curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
    && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    > /etc/apt/sources.list.d/nvidia-container-toolkit.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    libnvidia-container-tools=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
    libnvidia-container1=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
    nvidia-container-toolkit=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
    nvidia-container-toolkit-base=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
    && rm -rf /var/lib/apt/lists/*

# add extra paths to mount into end-user container via nvidia runtime
RUN mkdir -p /etc/nvidia-container-runtime/host-files-for-container.d \
    && echo "dir, /usr/local/cuda-${CUDA_VERSION}" >> /etc/nvidia-container-runtime/host-files-for-container.d/l4t.csv \
    && echo "lib, /usr/bin/tegrastats" >> /etc/nvidia-container-runtime/host-files-for-container.d/l4t.csv
