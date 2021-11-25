#!/bin/sh

modprobe udp_tunnel
modprobe ip6_udp_tunnel
modprobe wireguard || {
  # If the kernel module wasn't available, we would have built it here
  insmod /wireguard/wireguard.ko || true
}

exec "$@"
