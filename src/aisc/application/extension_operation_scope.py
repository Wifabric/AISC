"""Serialize host extension mutations and retain per-operation process identity."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import hashlib

from aisc.adapters.data_root_store import file_lock

_held = ContextVar('aisc_extension_locks', default=frozenset())
operation_marker = ContextVar('aisc_extension_operation_marker', default='')
expected_container = ContextVar('aisc_extension_expected_container', default='')
READ_OPS = frozenset({'list', 'skill-search', 'skill-describe', 'mcp-search', 'plugin-search',
                     'skill-repos-list', 'plugin-market-list', 'updates-check'})


@contextmanager
def mutation_scope(root, runtime_id):
    path = Path(root) / 'extension-operations' / (hashlib.sha256(runtime_id.encode()).hexdigest() + '.lock')
    key = str(path.resolve())
    if key in _held.get():
        yield
        return
    with file_lock(path, timeout=10.0, error_code='AISC_ERR_EXTENSIONS_BUSY'):
        token = _held.set(_held.get() | {key})
        try:
            yield
        finally:
            _held.reset(token)
