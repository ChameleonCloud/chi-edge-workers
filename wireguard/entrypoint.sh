#!/bin/bash

OS_VERSION=$(echo "${BALENA_HOST_OS_VERSION}" | cut -d " " -f 2)
echo "OS Version is ${OS_VERSION}"

# These modules should exist in the host kernel
modprobe udp_tunnel
modprobe ip6_udp_tunnel
modprobe ip_tunnel

if [ "${BALENA_DEVICE_TYPE}" != "raspberrypi4-64" ] && [ "${BALENA_DEVICE_TYPE}" != "raspberrypi5" ]; then
    # balena r36.4 kernel lacks CONFIG_IP_NF_RAW; without this, Calico Felix
    # panics on the missing 'raw' iptables table. Harmlessly no-ops on r32
    # (file will not exist; insmod fails into `|| true`).
    lsmod | grep -q '^iptable_raw ' || \
        insmod "/kmods/iptable_raw/${BALENA_DEVICE_TYPE}/${OS_VERSION}/iptable_raw.ko" || true

    mod_dir="/kmods/ipip/${BALENA_DEVICE_TYPE}/${OS_VERSION}"
    lsmod | grep -q ipip || {
        insmod "${mod_dir}/tunnel4.ko" || true
        insmod "${mod_dir}/ipip.ko" || true
    }
fi

mod_dir="/kmods/wireguard/${BALENA_DEVICE_TYPE}/${OS_VERSION}"
lsmod | grep -q wireguard || {
	# Load modules from device specific directory
	# If the kernel module wasn't available, we would have built it here
	insmod "${mod_dir}/wireguard.ko" || true
}

exec "$@"
