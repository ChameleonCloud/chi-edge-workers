#!/bin/bash
# This script may look POSIX-compatible but it references
# compogen and printf "%q", which are both Bash-isms.
set -o errexit
set -o nounset
set -m

# Balena will mount a socket and set DOCKER_HOST to
# point to the socket path.
if [ -n "$DOCKER_HOST" ]; then
  mkdir -p /run/k3s/containerd
  ln -sf "${DOCKER_HOST##unix://}" /run/k3s/containerd/containerd.sock
  ln -sf "${DOCKER_HOST##unix://}" /var/run/docker.sock
fi

##############
# DISCLAIMER
##############
# Copied from 
# https://github.com/moby/moby/blob/ed89041433a031cafc0a0f19cfe573c31688d377/hack/dind#L28-L37
# Permission granted by Akihiro Suda <akihiro.suda.cz@hco.ntt.co.jp> (https://github.com/rancher/k3d/issues/493#issuecomment-827405962)
# Moby License Apache 2.0: https://github.com/moby/moby/blob/ed89041433a031cafc0a0f19cfe573c31688d377/LICENSE
#############
if [ -f /sys/fs/cgroup/cgroup.controllers ]; then
  # move the processes from the root group to the /init group,
  # otherwise writing subtree_control fails with EBUSY.
  mkdir -p /sys/fs/cgroup/init
  busybox xargs -rn1 < /sys/fs/cgroup/cgroup.procs > /sys/fs/cgroup/init/cgroup.procs || :
  # enable controllers
  sed -e 's/ / +/g' -e 's/^/+/' <"/sys/fs/cgroup/cgroup.controllers" >"/sys/fs/cgroup/cgroup.subtree_control"
fi

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
  if [ "$UDEV" == "on" ]; then
    if [ "$INITSYSTEM" != "on" ]; then
      if command -v udevd &>/dev/null; then
        unshare --net udevd --daemon &> /dev/null
      else
        unshare --net /lib/systemd/systemd-udevd --daemon &> /dev/null
      fi
      udevadm trigger &> /dev/null
    fi
  else
    if [ "$INITSYSTEM" == "on" ]; then
      systemctl mask systemd-udevd
    fi
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
  GREEN='\033[0;32m'
  echo -e "${GREEN}Systemd init system enabled."
  for var in $(compgen -e); do
    printf '%q=%q\n' "$var" "${!var}"
  done > /etc/docker.env
  echo 'source /etc/docker.env' >> ~/.bashrc

  printf '#!/bin/bash\n exec ' > /etc/balenaApp.sh
  printf '%q ' "$@" >> /etc/balenaApp.sh
  chmod +x /etc/balenaApp.sh

   mkdir -p /etc/systemd/system/balena.service.d
  cat <<EOF > /etc/systemd/system/balena.service.d/override.conf
[Service]
WorkingDirectory=$(pwd)
EOF

  sleep infinity &
  exec env DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket /sbin/init quiet systemd.show_status=0
}

init_non_systemd() {
  # trap the stop signal then send SIGTERM to user processes
  trap signal_handler SIGRTMIN+3 SIGTERM

  # echo error message, when executable file doesn't exist.
  if CMD=$(command -v "$1" 2>/dev/null); then
    shift
    "$CMD" "$@" &
    pid=$!
    wait "$pid"
    exit_code=$?
    fg &> /dev/null || exit "$exit_code"
  else
    echo "Command not found: $1"
    exit 1
  fi
}

INITSYSTEM=$(echo "$INITSYSTEM" | awk '{print tolower($0)}')

case "$INITSYSTEM" in
  '1' | 'true')
    INITSYSTEM='on'
  ;;
esac

if $PRIVILEGED; then
  # Only run this in privileged container
  mount_dev
  start_udev
fi

if [ "$INITSYSTEM" = "on" ]; then
  init_systemd "$@"
else
  init_non_systemd "$@"
fi
