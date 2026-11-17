#!/usr/bin/env bash
# Laser printer emulator for the fixos printer digital twin.
#
# Runs in its own network namespace attached to the libvirt bridge, with a
# Brother OUI MAC address, so guests see a separate LAN host whose NetBIOS-style
# name (BRN<mac>) resolves nowhere - exactly the failure seen on a real
# Brother HL-L5200DW. Services:
#   631/tcp  IPP Everywhere (ippeveprinter, /ipp/print, DNS-SD disabled)
#   515/tcp  LPD sink          9100/tcp  raw socket sink
# Every received job is kept under $TWIN_DIR/spool/{ipp,lpd,raw}.
#
# Usage: sudo printer-emulator.sh up|down|status|jobs|stop-ipp|start-ipp
set -euo pipefail

NS=${TWIN_NS:-fixos-printer}
BRIDGE=${TWIN_BRIDGE:-virbr0}
MAC=${TWIN_PRINTER_MAC:-3c:2a:f4:00:00:01}
IP=${TWIN_PRINTER_IP:-192.168.122.50}
GW=${TWIN_GATEWAY:-192.168.122.1}
TWIN_DIR=${TWIN_DIR:-/var/lib/libvirt/images/fixos-twin}
SPOOL=$TWIN_DIR/spool
HERE=$(cd "$(dirname "$0")" && pwd)
HOST_VETH=vfxp0

start_ipp() {
  mkdir -p "$SPOOL/ipp"
  ip netns exec "$NS" ippeveprinter -r off -n "BRN${MAC//:/}" -p 631 \
    -M Brother -m "HL-L5200DW series" -l "fixos twin" \
    -f application/pdf,image/pwg-raster,image/urf,text/plain \
    -k -d "$SPOOL/ipp" "HL-L5200DW" >"$SPOOL/ippeveprinter.log" 2>&1 &
  echo $! >"$SPOOL/ipp.pid"
}

stop_ipp() {
  [[ -f $SPOOL/ipp.pid ]] && kill "$(cat "$SPOOL/ipp.pid")" 2>/dev/null || true
  rm -f "$SPOOL/ipp.pid"
}

up() {
  if ip netns list | grep -qw "$NS"; then
    echo "already up"
    return
  fi
  mkdir -p "$SPOOL"/{ipp,lpd,raw}
  ip netns add "$NS"
  # The printer must resolve its own name to bind; only inside its namespace.
  mkdir -p "/etc/netns/$NS"
  # ippeveprinter binds both families of its own name; give it a ULA too.
  printf '127.0.0.1 localhost\n%s BRN%s\nfd7a:f1c5::50 BRN%s\n' \
    "$IP" "${MAC//:/}" "${MAC//:/}" >"/etc/netns/$NS/hosts"
  ip link add "$HOST_VETH" type veth peer name eth0 netns "$NS"
  ip link set "$HOST_VETH" master "$BRIDGE" up
  ip -n "$NS" link set lo up
  ip -n "$NS" link set eth0 address "$MAC" up
  ip -n "$NS" addr add "$IP/24" dev eth0
  ip -n "$NS" addr add fd7a:f1c5::50/64 dev eth0 nodad
  ip -n "$NS" route add default via "$GW"
  start_ipp
  ip netns exec "$NS" python3 -I "$HERE/job_sink.py" "$SPOOL" \
    >"$SPOOL/sink.log" 2>&1 &
  echo $! >"$SPOOL/sink.pid"
  sleep 1
  status
}

down() {
  stop_ipp
  [[ -f $SPOOL/sink.pid ]] && kill "$(cat "$SPOOL/sink.pid")" 2>/dev/null || true
  rm -f "$SPOOL/sink.pid"
  ip link del "$HOST_VETH" 2>/dev/null || true
  ip netns del "$NS" 2>/dev/null || true
  rm -rf "/etc/netns/$NS"
  echo "down"
}

status() {
  echo "printer $IP mac $MAC name BRN${MAC//:/}" | tr '[:lower:]' '[:upper:]'
  ip netns exec "$NS" ss -ltn | awk 'NR>1{print "  listen", $4}'
}

jobs() {
  find "$SPOOL"/ipp "$SPOOL"/lpd "$SPOOL"/raw -type f -printf '%TY-%Tm-%Td %TH:%TM  %s  %p\n' | sort
}

case ${1:-status} in
  up) up ;;
  down) down ;;
  status) status ;;
  jobs) jobs ;;
  stop-ipp) stop_ipp ;;
  start-ipp) start_ipp ;;
  *) echo "usage: $0 up|down|status|jobs|stop-ipp|start-ipp" >&2; exit 2 ;;
esac
