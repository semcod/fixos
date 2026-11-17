"""LPD (RFC 1179, receive-job only) and raw 9100 job sink for the printer twin.

Usage: python3 job_sink.py SPOOL_DIR
Stores each job as SPOOL_DIR/{lpd,raw}/<timestamp>-<n>.bin.
"""

from __future__ import annotations

import itertools
import socketserver
import sys
import threading
import time
from pathlib import Path

SPOOL = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
_counter = itertools.count(1)


def _target(kind: str) -> Path:
    path = SPOOL / kind
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{time.strftime('%Y%m%d-%H%M%S')}-{next(_counter)}.bin"


class RawHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        data = self.rfile.read()
        if data:
            _target("raw").write_bytes(data)


class LpdHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        command = self.rfile.readline()
        if not command or command[0] != 0x02:  # only "receive a printer job"
            self.wfile.write(b"\x01")
            return
        self.wfile.write(b"\x00")
        payload = bytearray()
        while True:
            sub = self.rfile.readline()
            if not sub:
                break
            if sub[0] in (0x02, 0x03):  # control file / data file
                size = int(sub[1:].split(b" ", 1)[0])
                self.wfile.write(b"\x00")
                chunk = self.rfile.read(size + 1)  # file + trailing NUL
                if sub[0] == 0x03:
                    payload += chunk[:-1]
                self.wfile.write(b"\x00")
            else:
                self.wfile.write(b"\x00")
        if payload:
            _target("lpd").write_bytes(bytes(payload))


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    for port, handler in ((9100, RawHandler), (515, LpdHandler)):
        server = Server(("0.0.0.0", port), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"listening on {port}", flush=True)
    threading.Event().wait()


if __name__ == "__main__":
    main()
