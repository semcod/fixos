#!/usr/bin/env bash
# Printer failure scenarios run inside a twin guest (as root).
# Each scenario breaks the print system, checks that `fixos printers`
# diagnoses it, applies `fixos printers --fix -y` and checks the repair.
set -uo pipefail

PRINTER_IP=${TWIN_PRINTER_IP:-192.168.122.50}
PRINTER_NAME=${TWIN_PRINTER_NAME:-BRN3C2AF4000001}
DEAD_IP=${TWIN_DEAD_IP:-192.168.122.51}
Q=twin
DEAD=twin-dead
PASS=0
FAIL=0
export LC_ALL=C.UTF-8

ok() { echo "  PASS  $*"; PASS=$((PASS + 1)); }
bad() { echo "  FAIL  $*"; FAIL=$((FAIL + 1)); }
check() { local msg=$1; shift; if "$@"; then ok "$msg"; else bad "$msg"; fi; }

# findings [extra args]: JSON findings of `fixos printers` as "queue|title|command" lines.
findings() {
  fixos printers --json "$@" 2>/dev/null | python3 -c '
import json, sys
text = sys.stdin.read()
data = json.loads(text[text.index("{"):])
for f in data["findings"]:
    print("|".join([f["data"].get("queue", "-"), f["title"], f["command"] or ""]))
'
}
has() { findings "${@:3}" | grep -F "$1|" | grep -qF "$2"; }
has_cmd() { findings "${@:3}" | grep -F "$1|" | grep -F "$2" | cut -d'|' -f3 | grep -q .; }
no_cmd() { ! has_cmd "$@"; }
clean() { ! findings | grep -qF "$1|"; }
fix() { fixos printers --fix -y "$@" >/tmp/fix.log 2>&1; }
uri() { lpstat -v "$1" 2>/dev/null | awk '{print $NF}'; }
forget_printer() { ip neigh flush to "$PRINTER_IP" >/dev/null 2>&1 || true; }
reset() { lpadmin -x "$Q" 2>/dev/null; lpadmin -p "$Q" -E -v "$1" 2>/dev/null; }

echo "## $(. /etc/os-release; echo "$PRETTY_NAME"), CUPS $(cups-config --version 2>/dev/null || lpstat -r)"
fixos --version | head -1

# Stuck-job scenario needs a job older than 5 minutes: start it first.
lpadmin -x "$DEAD" 2>/dev/null
lpadmin -p "$DEAD" -E -v "ipp://$DEAD_IP/ipp/print" 2>/dev/null
echo stuck | lp -d "$DEAD" >/dev/null
STUCK_SINCE=$SECONDS

echo "S1 unresolvable BRN name, printer not in ARP"
reset "lpd://$PRINTER_NAME/BINARY_P1"
forget_printer
check "diagnosed as unresolvable" has "$Q" "nie można rozwiązać nazwy"
check "no blind repair without a located address" no_cmd "$Q" "nie można rozwiązać nazwy"

echo "S2 --scan relocates the printer by MAC"
forget_printer
check "repair proposed after scan" has_cmd "$Q" "nie można rozwiązać nazwy" --scan

echo "S3 --fix repoints the queue to IPP Everywhere"
forget_printer
fix --scan
check "uri is ipp://$PRINTER_IP/ipp/print" test "$(uri "$Q")" = "ipp://$PRINTER_IP/ipp/print"
check "queue healthy after fix" clean "$Q"

echo "S4 test page reaches the emulator"
out=$(fixos printers --test-print "$Q" 2>/dev/null | grep 'Strona testowa')
check "fixos printers --test-print completes ($out)" grep -q zakończone <<<"$out"
job=$(awk '{print $3}' <<<"$out" | tr -d :)
check "CUPS job $job is in state completed" bash -c "ipptool -tv ipp://localhost/jobs/${job##*-} get-job-attributes.test | grep -q 'job-state (enum) = completed'"

for legacy in "lpd://$PRINTER_IP/BINARY_P1" "socket://$PRINTER_IP:9100"; do
  echo "S5 legacy raw queue $legacy on a driverless printer"
  reset "$legacy"
  check "diagnosed as outdated driver/protocol" has "$Q" "przestarzały"
  fix
  check "fixed to IPP Everywhere" test "$(uri "$Q")" = "ipp://$PRINTER_IP/ipp/print"
done

echo "S6 paused queue"
cupsdisable "$Q"
check "diagnosed as paused" has "$Q" "kolejka wstrzymana"
fix
check "queue enabled again" bash -c "lpstat -p $Q | grep -qv disabled"
check "queue healthy after fix" clean "$Q"

echo "S7 unreachable printer"
check "diagnosed as not responding" has "$DEAD" "nie odpowiada"

echo "S8 cups service stopped"
systemctl stop cups.socket cups.path cups >/dev/null 2>&1
check "diagnosed as stopped" bash -c "fixos printers 2>/dev/null | grep -q 'CUPS nie działa'"
fix
check "cups active after fix" systemctl is-active --quiet cups

echo "S9 job stuck for more than 5 minutes"
wait_for=$((310 - (SECONDS - STUCK_SINCE)))
if ((wait_for > 0)); then
  echo "  … waiting ${wait_for}s for the job to age"
  sleep "$wait_for"
fi
check "diagnosed as stuck job" has "$DEAD" "zablokowane zadania"
fix
check "dead queue has no pending jobs" test -z "$(lpstat -W not-completed -o "$DEAD")"

lpadmin -x "$DEAD"
lpadmin -x "$Q"
echo "RESULT pass=$PASS fail=$FAIL"
((FAIL == 0))
