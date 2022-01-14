#!/bin/bash
# This script may look POSIX-compatible but it references
# compogen and printf "%q", which are both Bash-isms.
set -o errexit
set -o nounset
set -m

## Privileged container check
dummy0_remove() {
  # clean the dummy0 link
  ip link delete dummy0 &> /dev/null || true
}
# This command only works in privileged container
dummy0_remove
if ip link add dummy0 type dummy &> /dev/null; then
  dummy0_remove
  PRIVILEGED=true
else
  PRIVILEGED=false
fi

# Send SIGTERM to child processes of PID 1.
signal_handler() {
  kill "$pid"
}

start_udev() {
  if [ "$UDEV" != "on" ]; then
    systemctl mask systemd-udevd
  fi
}

mount_dev() {
  tmp_dir='/tmp/tmpmount'
  mkdir -p "$tmp_dir"
  mount -t devtmpfs none "$tmp_dir"
  mkdir -p "$tmp_dir/shm"
  mount --move /dev/shm "$tmp_dir/shm"
  mkdir -p "$tmp_dir/mqueue"
  mount --move /dev/mqueue "$tmp_dir/mqueue"
  mkdir -p "$tmp_dir/pts"
  mount --move /dev/pts "$tmp_dir/pts"
  touch "$tmp_dir/console"
  mount --move /dev/console "$tmp_dir/console"
  umount /dev || true
  mount --move "$tmp_dir" /dev

  # Since the devpts is mounted with -o newinstance by Docker, we need to make
  # /dev/ptmx point to its ptmx.
  # ref: https://www.kernel.org/doc/Documentation/filesystems/devpts.txt
  ln -sf /dev/pts/ptmx /dev/ptmx

  mount -t debugfs nodev /sys/kernel/debug || true
}

init_systemd() {
  service="$1"
  shift
  GREEN='\033[0;32m'
  echo -e "${GREEN}Systemd init system enabled."
  for var in $(compgen -e); do
    printf '%q=%q\n' "$var" "${!var}"
  done > /etc/docker.env
  echo 'source /etc/docker.env' >> ~/.bashrc
  mkdir -p "/etc/systemd/system/${service}.service.d"
  cat <<EOF >"/etc/systemd/system/${service}.service.d/override.conf"
[Service]
WorkingDirectory=$(pwd)
EOF

  sleep infinity &
  exec env DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket /sbin/init quiet systemd.show_status=0
}

if $PRIVILEGED; then
  # Only run this in privileged container
  mount_dev
  start_udev
fi

init_systemd "$@"
