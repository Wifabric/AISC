"""Filesystem rename with the Explorer's no-overwrite contract."""
from __future__ import annotations

import ctypes
import errno
import os
import sys


def rename_no_replace(source: str, destination: str) -> None:
    source = os.path.abspath(source)
    destination = os.path.abspath(destination)
    # Check the source even for a no-op; lexists also accepts symlinks.
    os.lstat(source)
    if source == destination:
        return
    if os.path.lexists(destination):
        source_parent, source_name = os.path.split(source)
        destination_parent, destination_name = os.path.split(destination)
        # On a case-insensitive volume both spellings resolve to one entry.
        # samefile alone would incorrectly accept distinct hard-link names.
        case_alias = (
            source_name.casefold() == destination_name.casefold()
            and os.path.samefile(source_parent, destination_parent)
            and destination_name not in os.listdir(destination_parent)
            and os.path.samefile(source, destination)
        )
        if case_alias:
            os.rename(source, destination)
            return
        raise FileExistsError(errno.EEXIST, "destination already exists", destination)
    if os.name == "nt":
        # Windows os.rename refuses an existing destination, including a
        # destination created after the check above.
        os.rename(source, destination)
        return

    libc = ctypes.CDLL(None, use_errno=True)
    src, dst = os.fsencode(source), os.fsencode(destination)
    if sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        rename = libc.renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                           ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        result = rename(-100, src, -100, dst, 1)  # AT_FDCWD, RENAME_NOREPLACE
    elif sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        rename = libc.renamex_np
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        result = rename(src, dst, 4)  # RENAME_EXCL
    else:
        raise OSError(errno.ENOTSUP, "exclusive rename is unavailable", destination)
    if result != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), destination)
