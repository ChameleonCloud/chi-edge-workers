#!/bin/bash

set -euo pipefail

if [ -z "${L4T_BSP_URL:-}" ]; then
  echo "L4T_BSP_URL must be set"
  exit 1
fi

echo "downloading binaries"
wget "${L4T_BSP_URL}" -O l4t_bsp.tbz2
tar -xf l4t_bsp.tbz2
rm -f l4t_bsp.tbz2

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
