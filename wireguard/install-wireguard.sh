#!/bin/sh
set -o errexit

env | grep BALENA_

no_kmod() {
  echo 0>$(pwd)/kmod_built
  mkdir -p $(pwd)/tools
  exit 0
}

if modprobe wireguard 2>/dev/null; then
  echo "Native Wireguard support detected, not building kernel module."
  no_kmod
elif [ "$BALENA_MACHINE_NAME" = "raspberrypi4-64" ]; then
  echo "Raspberry Pi 4 (64-bit OS) detected. This host device _should_ "
  echo "have kernel support, but it was not detected in the build host. "
  echo "Exiting and assuming that things will 'just work' on the device."
  no_kmod
else
  echo "No native Wireguard support detected, building kernal module from source."
fi

VERSION="${BALENA_HOST_OS_VERSION#balenaOS }".dev

git clone https://git.zx2c4.com/wireguard-linux-compat
git clone https://git.zx2c4.com/wireguard-tools

balena_images="https://files.balena-cloud.com/images"
km_source="$balena_images/$BALENA_MACHINE_NAME/$VERSION/kernel_modules_headers.tar.gz"
echo "Getting kernel modules from $km_source"
headers_tarball="$(echo "$km_source" | sed -e 's/+/%2B/')"
curl -SsL -o headers.tar.gz "$headers_tarball"
tar -xf headers.tar.gz

make -C kernel_modules_headers -j$(nproc) modules_prepare
make -C kernel_modules_headers M=$(pwd)/wireguard-linux-compat/src -j$(nproc)
cp wireguard-linux-compat/src/wireguard.ko .

make -C $(pwd)/wireguard-tools/src -j$(nproc)
mkdir -p $(pwd)/tools
make -C $(pwd)/wireguard-tools/src DESTDIR=$(pwd)/tools install
echo 1>$(pwd)/kmod_built
