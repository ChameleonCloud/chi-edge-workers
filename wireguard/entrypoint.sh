#!/bin/sh

modprobe udp_tunnel
modprobe ip6_udp_tunnel
lsmod | grep -q wireguard || {
  # If the kernel module wasn't available, we would have built it here
  insmod /wireguard/wireguard.ko || true
}

exec "$@"
