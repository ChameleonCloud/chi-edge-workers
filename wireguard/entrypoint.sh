#!/bin/bash

OS_VERSION=$(echo "${BALENA_HOST_OS_VERSION}" | cut -d " " -f 2)
echo "OS Version is ${OS_VERSION}"

# These modules should exist in the host kernel
modprobe udp_tunnel
modprobe ip6_udp_tunnel

mod_dir="/kmods/ipip/${BALENA_DEVICE_TYPE}/${OS_VERSION}"
lsmod | grep -q ipip || {
	insmod "${mod_dir}/tunnel4.ko" || true
	insmod "${mod_dir}/ipip.ko" || true
}

mod_dir="/kmods/wireguard/${BALENA_DEVICE_TYPE}/${OS_VERSION}"
lsmod | grep -q wireguard || {
	# Load modules from device specific directory
	# If the kernel module wasn't available, we would have built it here
	insmod "${mod_dir}/wireguard.ko" || true
}

exec "$@"
