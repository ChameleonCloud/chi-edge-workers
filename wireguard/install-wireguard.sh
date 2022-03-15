#!/bin/sh
set -o errexit

no_kmod() {
  echo "The target host device _should_ have kernel support. Skipping kernel module build."
  echo "Writing flag file"
  echo 0>$(pwd)/kmod_built
  install_tools
  exit 0
}

install_kmod() {
  local balena_images="https://files.balena-cloud.com/images"
  local km_source="$balena_images/$BALENA_MACHINE_NAME/$OS_VERSION".dev/kernel_modules_headers.tar.gz

  echo "Getting kernel modules from $km_source"
  local headers_tarball="$(echo "$km_source" | sed -e 's/+/%2B/')"
  curl -SsL -o headers.tar.gz "$headers_tarball"
  tar -xf headers.tar.gz

  if [ "$BALENA_MACHINE_NAME" = "jetson-nano" ]; then
    # Download missing header(s)
    mkdir -p kernel_modules_headers/arch/arm/include/asm/xen
    # Balena uses OE4T kernel per https://forums.balena.io/t/build-kernel-module-out-of-tree-for-jetson/295852/20
    curl -SsL -o kernel_modules_headers/arch/arm/include/asm/xen/hypervisor.h \
      https://raw.githubusercontent.com/OE4T/linux-tegra-4.9/oe4t-patches-l4t-r32.6/arch/arm/include/asm/xen/hypervisor.h
  fi

  echo "Getting Wireguard kernel source"
  git clone git://git.zx2c4.com/wireguard-linux-compat

  echo "Compiling kernel module"
  make -C kernel_modules_headers -j$(nproc) modules_prepare
  make -C kernel_modules_headers M=$(pwd)/wireguard-linux-compat/src -j$(nproc)
  cp wireguard-linux-compat/src/wireguard.ko .

  echo "Writing flag file"
  echo 1>$(pwd)/kmod_built
}

install_tools() {
  echo "Compiling tools"
  git clone git://git.zx2c4.com/wireguard-tools
  make -C $(pwd)/wireguard-tools/src -j$(nproc)
  mkdir -p $(pwd)/tools
  make -C $(pwd)/wireguard-tools/src DESTDIR=$(pwd)/tools install
}

case "$BALENA_MACHINE_NAME" in
  jetson-nano)
    OS_VERSION=2.85.2+rev4
    ;;
  raspberrypi3-64)
    OS_VERSION=2.80.3+rev1
    ;;
  raspberrypi4-64)
    no_kmod
    ;;
  *)
    echo "Unsupported device type '$BALENA_MACHINE_NAME'"
    exit 1
    ;;
esac

install_kmod
install_tools
