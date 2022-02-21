#!/bin/bash
set -o errexit

[[ $UID == 0 ]] || { echo "You must be root to run this."; exit 1; }

mkdir -p /etc/wireguard
if [ "$WIREGUARD_PURGE" = "1" ]; then
  rm -f /etc/wireguard/*
fi

wg_up() {
  iface="$1"
  suffix="${iface##wg-}"
  ip link del dev "$iface" 2>/dev/null || true
  ip link add dev "$iface" type wireguard
  wg_conf=/etc/wireguard/"$iface".conf

  if [ ! -f "$wg_conf" ]; then
    echo "Generating $suffix Wireguard config from env:"
    env | grep WIREGUARD_ | grep "$suffix"

    # Read configuration from env vars
    privkey_env="WIREGUARD_PRIVATE_KEY_${suffix}"
    privkey="${!privkey_env:-$(wg genkey)}"
    peerkey_env="WIREGUARD_PEER_PUBLIC_KEY_${suffix}"
    peerkey="${!peerkey_env}"
    peerendpoint_env="WIREGUARD_PEER_ENDPOINT_${suffix}"
    peerendpoint="${!peerendpoint_env}"
    peerallowedips_env="WIREGUARD_PEER_ALLOWED_IPS_${suffix}"
    peerallowedips="${!peerallowedips_env}"
    peerroute_env="WIREGUARD_PEER_ROUTE_${suffix}"
    peerroute="${!peerroute_env}"

    cat >"$wg_conf" <<EOF
[Interface]
PrivateKey = $privkey
#MTU = 1420
#PostUp = ip route add $peerroute;

[Peer]
PublicKey = $peerkey
#PresharedKey = <peerpsk; not yet defined>
AllowedIPs = $peerallowedips
Endpoint = $peerendpoint
PersistentKeepalive = 15
EOF
    cat "$wg_conf"
  fi

  wg syncconf "$iface" "$wg_conf"

  echo "Generated conf:"
  wg showconf "$iface"

  ipv4_env="WIREGUARD_IPV4_${suffix}"
  ipv4="${!ipv4_env}"
  ip address add "$ipv4" dev "$iface"
  ip link set up dev "$iface"
}

wg_up wg-calico

exec balena-idle
