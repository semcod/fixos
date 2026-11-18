from __future__ import annotations

import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from tests.twin.printers.job_sink import LpdHandler, RawHandler, Server


class _SyncServer(Server):
    daemon_threads = False
    block_on_close = True


@contextmanager
def _running_sink(handler_cls, spool_dir: Path) -> Iterator[tuple[str, int]]:
    server = _SyncServer(("127.0.0.1", 0), handler_cls, spool_dir=spool_dir)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    )
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield str(host), int(port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _spool_files(spool_dir: Path, kind: str) -> list[Path]:
    folder = spool_dir / kind
    if not folder.exists():
        return []
    return sorted(folder.glob("*.bin"))


def test_raw_sink_stores_binary_and_ignores_empty_connection(tmp_path: Path):
    with _running_sink(RawHandler, tmp_path) as addr:
        with socket.create_connection(addr, timeout=3) as sock:
            sock.shutdown(socket.SHUT_WR)
            assert sock.recv(1) == b""

        payload = b"\x1b%-12345X@PJL INFO ID\r\n\x00\xffPCL"
        with socket.create_connection(addr, timeout=3) as sock:
            sock.sendall(payload)
            sock.shutdown(socket.SHUT_WR)
            assert sock.recv(1) == b""

    files = _spool_files(tmp_path, "raw")
    assert len(files) == 1
    assert files[0].read_bytes() == payload


def test_lpd_valid_binary_payload_ignores_hostile_client_filename(tmp_path: Path):
    ctrl = b"Hhost\nPuser\n"
    data = b"\x00\x01\xfe\xffPJL-BINARY\n"
    with (
        _running_sink(LpdHandler, tmp_path) as addr,
        socket.create_connection(addr, timeout=3) as sock,
    ):
        sock.sendall(b"\x02BINARY_P1\n")
        assert sock.recv(1) == b"\x00"

        sock.sendall(f"\x02{len(ctrl)} ../../etc/passwd\n".encode("ascii"))
        assert sock.recv(1) == b"\x00"
        sock.sendall(ctrl + b"\x00")
        assert sock.recv(1) == b"\x00"

        sock.sendall(f"\x03{len(data)} ../escape.bin\n".encode("ascii"))
        assert sock.recv(1) == b"\x00"
        sock.sendall(data + b"\x00")
        assert sock.recv(1) == b"\x00"

        sock.shutdown(socket.SHUT_WR)
        assert sock.recv(1) == b""

    files = _spool_files(tmp_path, "lpd")
    assert len(files) == 1
    assert files[0].parent == tmp_path / "lpd"
    assert files[0].read_bytes() == data


def test_lpd_multiple_data_files_are_concatenated_in_order(tmp_path: Path):
    part1 = b"HEADER\n"
    part2 = b"BODY-12345"
    with (
        _running_sink(LpdHandler, tmp_path) as addr,
        socket.create_connection(addr, timeout=3) as sock,
    ):
        sock.sendall(b"\x02lp\n")
        assert sock.recv(1) == b"\x00"

        for idx, part in enumerate((part1, part2), start=1):
            sock.sendall(f"\x03{len(part)} dfA00{idx}host\n".encode("ascii"))
            assert sock.recv(1) == b"\x00"
            sock.sendall(part + b"\x00")
            assert sock.recv(1) == b"\x00"

        sock.shutdown(socket.SHUT_WR)
        assert sock.recv(1) == b""

    files = _spool_files(tmp_path, "lpd")
    assert len(files) == 1
    assert files[0].read_bytes() == part1 + part2


def test_lpd_unsupported_top_level_command_is_rejected(tmp_path: Path):
    with (
        _running_sink(LpdHandler, tmp_path) as addr,
        socket.create_connection(addr, timeout=3) as sock,
    ):
        sock.sendall(b"\x09BINARY_P1\n")
        assert sock.recv(1) == b"\x01"

    assert _spool_files(tmp_path, "lpd") == []


def test_lpd_truncated_data_and_missing_terminator_rejected_without_corrupting_prior_job(
    tmp_path: Path,
):
    ctrl = b"Hclient\nPtom\n"
    valid_payload = b"COMPLETE-JOB-01"

    with _running_sink(LpdHandler, tmp_path) as addr:
        # 1. Complete valid transaction first
        with socket.create_connection(addr, timeout=3) as sock:
            sock.sendall(b"\x02BINARY_P1\n")
            assert sock.recv(1) == b"\x00"
            sock.sendall(f"\x02{len(ctrl)} cfA001client\n".encode("ascii"))
            assert sock.recv(1) == b"\x00"
            sock.sendall(ctrl + b"\x00")
            assert sock.recv(1) == b"\x00"
            sock.sendall(f"\x03{len(valid_payload)} dfA001client\n".encode("ascii"))
            assert sock.recv(1) == b"\x00"
            sock.sendall(valid_payload + b"\x00")
            assert sock.recv(1) == b"\x00"
            sock.shutdown(socket.SHUT_WR)
            assert sock.recv(1) == b""

        # 2. Exact PLF-21825 reproduction: declare 8-byte data file, send 3 bytes ("abc"),
        # omit trailing NUL, and close write side. Must NAK (\x01) and create NO new job.
        with socket.create_connection(addr, timeout=3) as sock:
            sock.sendall(b"\x02BINARY_P1\n")
            assert sock.recv(1) == b"\x00"
            sock.sendall(f"\x02{len(ctrl)} cfA002client\n".encode("ascii"))
            assert sock.recv(1) == b"\x00"
            sock.sendall(ctrl + b"\x00")
            assert sock.recv(1) == b"\x00"
            sock.sendall(b"\x038 dfA002client\n")
            assert sock.recv(1) == b"\x00"
            sock.sendall(b"abc")
            sock.shutdown(socket.SHUT_WR)
            assert sock.recv(1) == b"\x01"

        # 3. Full declared length (8 bytes) followed by non-NUL terminator ('X') -> NAK
        with socket.create_connection(addr, timeout=3) as sock:
            sock.sendall(b"\x02BINARY_P1\n")
            assert sock.recv(1) == b"\x00"
            sock.sendall(b"\x038 dfA003client\n")
            assert sock.recv(1) == b"\x00"
            sock.sendall(b"12345678X")
            assert sock.recv(1) == b"\x01"

        # 4. Multi-file transaction where file 1 succeeds and file 2 is truncated -> no job saved
        with socket.create_connection(addr, timeout=3) as sock:
            sock.sendall(b"\x02BINARY_P1\n")
            assert sock.recv(1) == b"\x00"
            sock.sendall(b"\x034 dfA004client\n")
            assert sock.recv(1) == b"\x00"
            sock.sendall(b"PART\x00")
            assert sock.recv(1) == b"\x00"
            sock.sendall(b"\x0310 dfB004client\n")
            assert sock.recv(1) == b"\x00"
            sock.sendall(b"SHORT")
            sock.shutdown(socket.SHUT_WR)
            assert sock.recv(1) == b"\x01"

    files = _spool_files(tmp_path, "lpd")
    assert len(files) == 1
    assert files[0].read_bytes() == valid_payload
