#!/bin/bash

set -euo pipefail

echo "downloading binaries"
wget "https://developer.nvidia.com/embedded/l4t/r32_release_v6.1/t186/jetson_linux_r32.6.1_aarch64.tbz2" && \
    tar -xf "jetson_linux_r32.6.1_aarch64.tbz2" && \
    rm -f "jetson_linux_r32.6.1_aarch64.tbz2"

echo "find and replace"
cd Linux_for_Tegra && \
    sed -i 's/config.tbz2\"/config.tbz2\" --exclude=etc\/hosts --exclude=etc\/hostname/g' apply_binaries.sh && \
    sed -i 's/install --owner=root --group=root \"${QEMU_BIN}\" \"${L4T_ROOTFS_DIR}\/usr\/bin\/\"/#install --owner=root --group=root \"${QEMU_BIN}\" \"${L4T_ROOTFS_DIR}\/usr\/bin\/\"/g' nv_tegra/nv-apply-debs.sh && \
    sed -i 's/LC_ALL=C chroot . mount -t proc none \/proc/ /g' nv_tegra/nv-apply-debs.sh && \
    sed -i 's/umount ${L4T_ROOTFS_DIR}\/proc/ /g' nv_tegra/nv-apply-debs.sh && \
    sed -i 's/chroot . \//  /g' nv_tegra/nv-apply-debs.sh

echo "applying binaries"
./apply_binaries.sh -r / --target-overlay && cd ..
rm -rf Linux_for_Tegra

echo "adding kernel module config"
echo "/usr/lib/aarch64-linux-gnu/tegra" > /etc/ld.so.conf.d/nvidia-tegra.conf && ldconfig
