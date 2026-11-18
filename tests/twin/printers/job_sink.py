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
from typing import BinaryIO

SPOOL = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
_counter = itertools.count(1)


def _target(kind: str, spool_dir: Path | None = None) -> Path:
    root = spool_dir if spool_dir is not None else SPOOL
    path = root / kind
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{time.strftime('%Y%m%d-%H%M%S')}-{next(_counter)}.bin"


def _read_exact(stream: BinaryIO, count: int) -> bytes:
    """Read up to ``count`` bytes from ``stream``, looping until EOF or full."""
    buf = bytearray()
    while len(buf) < count:
        piece = stream.read(count - len(buf))
        if not piece:
            break
        buf.extend(piece)
    return bytes(buf)


class RawHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        data = self.rfile.read()
        if data:
            spool_dir = getattr(self.server, "spool_dir", SPOOL)
            _target("raw", spool_dir).write_bytes(data)


class LpdHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        command = self.rfile.readline()
        if (
            not command
            or not command.endswith(b"\n")
            or command[0] != 0x02  # only "receive a printer job"
        ):
            self.wfile.write(b"\x01")
            return
        self.wfile.write(b"\x00")
        payload = bytearray()
        has_data_file = False
        while True:
            sub = self.rfile.readline()
            if not sub:
                break
            if not sub.endswith(b"\n"):
                self.wfile.write(b"\x01")
                return
            code = sub[0]
            if code == 0x01:  # abort job
                payload.clear()
                has_data_file = False
                self.wfile.write(b"\x00")
                continue
            if code in (0x02, 0x03):  # control file / data file
                parts = sub[1:].strip().split(b" ", 1)
                try:
                    size = int(parts[0])
                except (ValueError, IndexError):
                    self.wfile.write(b"\x01")
                    return
                if size < 0:
                    self.wfile.write(b"\x01")
                    return
                self.wfile.write(b"\x00")
                chunk = _read_exact(self.rfile, size + 1)  # file + trailing NUL
                if len(chunk) != size + 1 or chunk[-1:] != b"\x00":
                    self.wfile.write(b"\x01")
                    return
                if code == 0x03:
                    payload.extend(chunk[:-1])
                    has_data_file = True
                self.wfile.write(b"\x00")
            else:
                self.wfile.write(b"\x01")
                return
        if has_data_file and payload:
            spool_dir = getattr(self.server, "spool_dir", SPOOL)
            _target("lpd", spool_dir).write_bytes(bytes(payload))


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[socketserver.BaseRequestHandler],
        spool_dir: Path | None = None,
    ) -> None:
        self.spool_dir = spool_dir if spool_dir is not None else SPOOL
        super().__init__(server_address, RequestHandlerClass)


def main() -> None:
    for port, handler in ((9100, RawHandler), (515, LpdHandler)):
        server = Server(("0.0.0.0", port), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"listening on {port}", flush=True)
    threading.Event().wait()


if __name__ == "__main__":
    main()
