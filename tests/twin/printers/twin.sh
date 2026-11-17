#!/usr/bin/env bash
# fixos printer digital twin: Linux guests + laser printer emulator.
#
#   sudo twin.sh up        start emulator, create/boot guests, install fixos
#   sudo twin.sh test      run scenarios.sh in every guest, print summary
#   sudo twin.sh down      stop guests and emulator (keep disks)
#   sudo twin.sh destroy   remove guests and their overlay disks
#
# Base images are expected in $TWIN_DIR (see README.md). Guests use thin
# overlays so the whole twin needs ~4 GB beyond the base images.
set -euo pipefail

TWIN_DIR=${TWIN_DIR:-/var/lib/libvirt/images/fixos-twin}
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
CONN=qemu:///system
KEY=$TWIN_DIR/id_twin
declare -A IMAGES=(
  [fixos-twin-ubuntu]="ubuntu-24.04.img ubuntu24.04"
  [fixos-twin-fedora]="fedora-43.qcow2 fedora-unknown"
)
GUESTS=(${TWIN_GUESTS:-fixos-twin-ubuntu fixos-twin-fedora})

vsh() { virsh -q -c "$CONN" "$@"; }

guest_ip() {
  vsh domifaddr "$1" --source lease 2>/dev/null | awk '/ipv4/{split($4,a,"/");print a[1];exit}'
}

ssh_g() {
  local ip=$1
  shift
  ssh -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o LogLevel=ERROR -o ConnectTimeout=5 "twin@$ip" "$@"
}

seed() {
  local name=$1 dir=$TWIN_DIR/$1
  mkdir -p "$dir"
  cat >"$dir/user-data" <<EOF
#cloud-config
hostname: $name
users:
  - name: twin
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys: ["$(cat "$KEY.pub")"]
package_update: false
EOF
  printf 'instance-id: %s\nlocal-hostname: %s\n' "$name" "$name" >"$dir/meta-data"
  cloud-localds "$dir/seed.iso" "$dir/user-data" "$dir/meta-data"
}

create() {
  local name=$1 base os
  read -r base os <<<"${IMAGES[$name]}"
  [[ -f $TWIN_DIR/$base ]] || { echo "missing base image $TWIN_DIR/$base" >&2; exit 1; }
  seed "$name"
  qemu-img create -q -f qcow2 -F qcow2 -b "$TWIN_DIR/$base" "$TWIN_DIR/$name/disk.qcow2" 10G
  virt-install --connect "$CONN" --name "$name" --memory 2048 --vcpus 2 \
    --osinfo "$os" --import --noautoconsole --graphics none \
    --disk "$TWIN_DIR/$name/disk.qcow2,bus=virtio" \
    --disk "$TWIN_DIR/$name/seed.iso,device=cdrom" \
    --network network=default,model=virtio >/dev/null
}

wait_ssh() {
  local name=$1 ip=""
  for _ in $(seq 1 90); do
    ip=$(guest_ip "$name")
    if [[ -n $ip ]] && ssh_g "$ip" true 2>/dev/null; then
      echo "$ip"
      return
    fi
    sleep 4
  done
  echo "timeout waiting for $name" >&2
  return 1
}

provision() {
  local name=$1 ip=$2
  ssh_g "$ip" 'sudo cloud-init status --wait >/dev/null 2>&1 || true
    if command -v apt-get >/dev/null; then
      sudo DEBIAN_FRONTEND=noninteractive apt-get -qq update &&
      sudo DEBIAN_FRONTEND=noninteractive apt-get -qq install -y --no-install-recommends \
        cups cups-client cups-ipp-utils python3-venv >/dev/null
    else
      sudo dnf -q install -y cups cups-client cups-ipptool python3 >/dev/null
    fi
    sudo systemctl enable --now cups >/dev/null 2>&1
    sudo python3 -m venv /opt/fixos'
  # Package the working tree so the twin tests the checkout, not only HEAD.
  tar -C "$REPO" -czf "$TWIN_DIR/fixos-src.tar.gz" --exclude=.git --exclude=.venv \
    --exclude=venv --exclude='__pycache__' --exclude=.worktrees \
    fixos pyproject.toml setup.py README.md LICENSE MANIFEST.in VERSION
  scp -q -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o LogLevel=ERROR "$TWIN_DIR/fixos-src.tar.gz" "$HERE/scenarios.sh" "twin@$ip:/tmp/"
  ssh_g "$ip" 'rm -rf /tmp/fixos-src && mkdir /tmp/fixos-src &&
    tar -C /tmp/fixos-src -xzf /tmp/fixos-src.tar.gz &&
    sudo /opt/fixos/bin/pip -q install /tmp/fixos-src &&
    sudo ln -sf /opt/fixos/bin/fixos /usr/local/bin/fixos && fixos --version'
}

up() {
  [[ -f $KEY ]] || ssh-keygen -q -t ed25519 -N '' -C fixos-twin -f "$KEY"
  "$HERE/printer-emulator.sh" up
  for name in "${GUESTS[@]}"; do
    if ! vsh dominfo "$name" >/dev/null 2>&1; then
      create "$name"
    elif [[ $(vsh domstate "$name") != running ]]; then
      vsh start "$name" >/dev/null
    fi
  done
  for name in "${GUESTS[@]}"; do
    ip=$(wait_ssh "$name")
    echo "$name $ip"
    provision "$name" "$ip"
  done
}

test_all() {
  local rc=0
  for name in "${GUESTS[@]}"; do
    ip=$(guest_ip "$name")
    echo "=================== $name ($ip)"
    scp -q -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      -o LogLevel=ERROR "$HERE/scenarios.sh" "twin@$ip:/tmp/"
    before=$(find "$TWIN_DIR/spool/ipp" -type f | wc -l)
    ssh_g "$ip" 'sudo bash /tmp/scenarios.sh' | tee "$TWIN_DIR/$name/result.txt" || rc=1
    after=$(find "$TWIN_DIR/spool/ipp" -type f | wc -l)
    if ((after > before)); then
      echo "  PASS  emulator stored $((after - before)) new IPP job(s) from $name"
    else
      echo "  FAIL  emulator received no IPP job from $name"
      rc=1
    fi
  done
  echo "=================== emulator spool (rc=$rc)"
  "$HERE/printer-emulator.sh" jobs
  return $rc
}

down() {
  for name in "${GUESTS[@]}"; do vsh destroy "$name" >/dev/null 2>&1 || true; done
  "$HERE/printer-emulator.sh" down
}

destroy() {
  down
  for name in "${GUESTS[@]}"; do
    vsh undefine "$name" --nvram >/dev/null 2>&1 || vsh undefine "$name" >/dev/null 2>&1 || true
    rm -rf "${TWIN_DIR:?}/$name"
  done
}

case ${1:-} in
  up) up ;;
  test) test_all ;;
  down) down ;;
  destroy) destroy ;;
  *) echo "usage: $0 up|test|down|destroy" >&2; exit 2 ;;
esac
