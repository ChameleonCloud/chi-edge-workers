#!/bin/sh
set -o errexit

env | grep BALENA_

if modprobe wireguard 2>/dev/null; then
  echo "Native Wireguard support detected, not building kernel module."
  exit 0
else
  echo "No native Wireguard support detected, building kernal module from source."
fi

case "$BALENA_MACHINE_NAME" in
  raspberrypi3-64)
    VERSION=2.80.3+rev1.dev
    ;;
  *)
    echo "Unsupported machine '$BALENA_MACHINE_NAME'"
    exit 1
    ;;
esac

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
make -C $(pwd)/wireguard-tools/src -j$(nproc)
mkdir -p $(pwd)/tools
make -C $(pwd)/wireguard-tools/src DESTDIR=$(pwd)/tools install
