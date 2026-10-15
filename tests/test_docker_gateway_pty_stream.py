"""b5 regression guards for the serve PTY stream pump.

The exec socket is an upgraded HTTP socket. A read timeout does not mean the
PTY ended; only a zero-byte read is EOF. These tests keep timeout/EINTR from
being mistaken for session death.
"""

from __future__ import annotations

import socket
import threading
import unittest

from aisc.adapters.docker_gateway import InteractiveStreamHandle


class ScriptedSocket:
    """Minimal duck-typed upgraded socket for InteractiveStreamHandle."""

    def __init__(self, reads):
        self.reads = list(reads)
        self.lock = threading.Lock()

    def recv(self, _size: int):
        with self.lock:
            if not self.reads:
                return b""
            read = self.reads.pop(0)
        if isinstance(read, Exception):
            raise read
        return read


class InteractivePumpStreamTests(unittest.TestCase):
    def _drain(self, sock):
        chunks: list[bytes] = []
        handle = InteractiveStreamHandle(None, "exec-1", sock, chunks.append)
        handle.join_pump(timeout=5)
        return handle, chunks

    def test_read_timeout_between_chunks_does_not_stop_pump(self) -> None:
        """A socket timeout is idle time, not EOF: later output must flow."""
        timeout = socket.timeout("upgraded socket inherited its read timeout")
        handle, chunks = self._drain(
            ScriptedSocket([b"first\n", timeout, b"second\n", b""])
        )

        self.assertEqual(chunks, [b"first\n", b"second\n"])
        self.assertIsNone(handle.error)
        self.assertTrue(handle._eof.is_set())

    def test_interrupted_read_does_not_stop_pump(self) -> None:
        """EINTR must retry the same blocking read instead of tearing down."""
        handle, chunks = self._drain(
            ScriptedSocket([b"first\n", InterruptedError(), b"second\n", b""])
        )

        self.assertEqual(chunks, [b"first\n", b"second\n"])
        self.assertIsNone(handle.error)
        self.assertTrue(handle._eof.is_set())

    def test_real_eof_still_ends_pump(self) -> None:
        handle, chunks = self._drain(ScriptedSocket([b"hello\n", b""]))

        self.assertEqual(chunks, [b"hello\n"])
        self.assertIsNone(handle.error)
        self.assertTrue(handle._eof.is_set())

    def test_explicit_stop_still_wakes_pump(self) -> None:
        class BlockedSocket:
            def __init__(self):
                self.released = threading.Event()

            def recv(self, _size: int):
                self.released.wait(timeout=5)
                return b""

            def close(self):
                self.released.set()

        sock = BlockedSocket()
        handle = InteractiveStreamHandle(None, "exec-1", sock, lambda _chunk: None)
        # Give the pump time to enter its blocking read, then detach.
        handle._stopped.wait(timeout=0.05)
        handle.kill()
        handle.join_pump(timeout=5)

        self.assertTrue(handle._eof.is_set())
        self.assertTrue(sock.released.is_set())
        self.assertIsNone(handle.error)


if __name__ == "__main__":
    unittest.main()
