#!/bin/bash
set -o errexit

[[ $UID == 0 ]] || { echo "You must be root to run this."; exit 1; }

set -x

wg_up() {
  iface="$1"
  suffix="${iface##wg-}"
  ip link del dev "$iface" 2>/dev/null || true
  ip link add dev "$iface" type wireguard
  wg_conf=/etc/wireguard/"$iface".conf
  read wg_ipv4 </etc/wireguard/"$iface".ipv4 || true
  wg syncconf "$iface" "$wg_conf"
  ip address add "$wg_ipv4" dev "$iface"
  ip link set up dev "$iface"
}

wg_up wg-calico

set +x

exec balena-idle
