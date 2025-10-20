#!/bin/bash
set -o errexit

abort() {
  echo "$@"
  exit 1
}

[[ $UID == 0 ]] || abort "You must be root to run this."

set -x

wg_up() {
  local iface="$1"
  local suffix="${iface##wg-}"
  local wg_conf=/etc/wireguard/"$iface".conf
  if [[ ! -f "$wg_conf" ]]; then
    abort "No wireguard configuration found."
  fi
  ip link del dev "$iface" 2>/dev/null || true
  ip link add dev "$iface" type wireguard

  read wg_ipv4 </etc/wireguard/"$iface".ipv4 || true
  wg syncconf "$iface" "$wg_conf"
  ip address add "$wg_ipv4" dev "$iface"
  ip link set up dev "$iface"
}

wg_up wg-calico

set +x

while true  
do  
  wg show
  sleep 60
done
