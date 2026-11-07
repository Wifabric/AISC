#!/usr/bin/env python3
"""Idempotent registration for the official hosted GitHub MCP server.

The cc-switch SQLite database remains the extension SSOT. This helper owns only
the fresh ``github`` row that AISC creates; a pre-existing row (or a live
``github`` entry without an SSOT row) is treated as user configuration and is
never replaced.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import tempfile
import tomllib
import datetime
from pathlib import Path
from typing import Any, TextIO

SERVER_ID = "github"
DEFAULT_TAG = "aisc-default"
MARKER_FILE = ".aisc-default-github-mcp.json"
OFFICIAL_URL = "https://api.githubcopilot.com/mcp/"
DEFAULT_TOKEN_ENV = "GITHUB_PAT_TOKEN"
DEFAULT_CONFIG = {
    "url": OFFICIAL_URL,
    "bearer_token_env_var": DEFAULT_TOKEN_ENV,
}
DESCRIPTION = "GitHub 官方 MCP：管理仓库、Issues、PR、Actions 等 GitHub 上下文。"
HOMEPAGE = "https://github.com/github/github-mcp-server"
DOCS = "https://github.com/github/github-mcp-server#remote-github-mcp-server"
_CODEX_TABLE = re.compile(
    r"(?ms)^\[mcp_servers\.github\]\s*\n.*?(?=^\[|\Z)"
)


def _marker_path(config_dir: Path) -> Path:
    return config_dir / MARKER_FILE


def _write_marker(config_dir: Path) -> None:
    _atomic_write(
        _marker_path(config_dir),
        json.dumps({
            "schema": "aisc.default-mcp/v1",
            "server_id": SERVER_ID,
            "url": OFFICIAL_URL,
        }, indent=2) + "\n",
        mode=0o600,
    )


def _connect(config_dir: Path) -> sqlite3.Connection:
    return sqlite3.connect(config_dir / "cc-switch.db", timeout=10)


def _tags(value: Any) -> list[str]:
    if not isinstance(value, str):
        return []
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def _read_row(config_dir: Path) -> tuple[Any, ...] | None:
    connection = _connect(config_dir)
    try:
        return connection.execute(
            "SELECT server_config, enabled_claude, enabled_codex, tags "
            "FROM mcp_servers WHERE id=?",
            (SERVER_ID,),
        ).fetchone()
    finally:
        connection.close()


def _insert_default(config_dir: Path) -> None:
    connection = _connect(config_dir)
    try:
        connection.execute(
            "INSERT INTO mcp_servers ("
            "id, name, server_config, description, homepage, docs, tags,"
            "enabled_claude, enabled_codex"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)",
            (
                SERVER_ID, "GitHub", json.dumps(DEFAULT_CONFIG, separators=(",", ":")),
                DESCRIPTION, HOMEPAGE, DOCS, f"{DEFAULT_TAG},{SERVER_ID}",
            ),
        )
        connection.commit()
        _write_marker(config_dir)
    finally:
        connection.close()

def _json_document(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _live_has_custom(project_dir: Path, codex_config_dir: Path) -> bool:
    claude = _json_document(project_dir / ".mcp.json").get("mcpServers")
    if isinstance(claude, dict) and SERVER_ID in claude:
        return True
    codex_path = codex_config_dir / "config.toml"
    try:
        text = codex_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(_CODEX_TABLE.search(text))


def _atomic_write(path: Path, text: str, *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                         dir=path.parent, prefix=path.name+'.', delete=False) as output:
            temporary = Path(output.name)
            if mode is not None:
                os.chmod(temporary, mode)
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _sync_claude(project_dir: Path, server: dict[str, Any], enabled: bool) -> None:
    path = project_dir / ".mcp.json"
    document = _json_document(path)
    servers = document.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
    if enabled:
        entry = dict(servers.get(SERVER_ID) or {})
        entry.update(type="http", url=str(server.get("url", "")))
        headers = server.get("headers")
        if isinstance(headers, dict) and headers:
            entry["headers"] = headers
        servers[SERVER_ID] = entry
    else:
        servers.pop(SERVER_ID, None)
    if servers:
        document["mcpServers"] = servers
    else:
        document.pop("mcpServers", None)
    if document:
        _atomic_write(path, json.dumps(document, indent=2, ensure_ascii=False) + "\n", mode=0o600)
    elif path.exists():
        path.unlink()


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_value(value: Any) -> str:
    if isinstance(value, str):
        return _toml_string(value)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, list):
        return '[' + ', '.join(_toml_value(v) for v in value) + ']'
    if isinstance(value, dict):
        return '{ ' + ', '.join(_toml_string(k)+' = '+_toml_value(v) for k, v in value.items()) + ' }'
    raise ValueError('Unsupported MCP TOML value')


def _codex_text(text: str, server: dict[str, Any], enabled: bool) -> str:
    document = tomllib.loads(text)
    existing = document.get('mcp_servers', {}).get(SERVER_ID, {})
    # Replace only this server's table/subtables; unrelated text stays intact.
    header = re.compile(r'^\s*\[mcp_servers\.(?:github|"github"|\'github\')(?:\.[^\]]+)?\]\s*(?:#.*)?$')
    lines, dropping, found = [], False, False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith('['):
            dropping = bool(header.match(line.strip()))
            found = found or dropping
        if not dropping:
            lines.append(line)
    if existing and not found:
        raise ValueError('Unsupported GitHub MCP table layout; preserve custom configuration')
    output = ''.join(lines).rstrip('\n') + '\n'
    if enabled:
        entry = dict(existing)
        entry['url'] = str(server.get('url', ''))
        headers = server.get('http_headers')
        if isinstance(headers, dict) and headers.get('Authorization'):
            entry['http_headers'] = headers
            entry.pop('bearer_token_env_var', None)
        else:
            entry['bearer_token_env_var'] = server.get('bearer_token_env_var') or DEFAULT_TOKEN_ENV
        output += '\n[mcp_servers.github]\n' + ''.join(f'{k if re.fullmatch("[A-Za-z0-9_-]+", k) else _toml_string(k)} = {_toml_value(v)}\n' for k,v in entry.items())
    tomllib.loads(output)
    return output


def _sync_codex(codex_config_dir: Path, server: dict[str, Any], enabled: bool) -> None:
    path = codex_config_dir / "config.toml"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    _atomic_write(path, _codex_text(text, server, enabled), mode=0o600)


def synchronize(
    *,
    config_dir: Path,
    project_dir: Path,
    codex_config_dir: Path,
    log: TextIO | None = None,
) -> str:
    """Register/sync the AISC-owned default; return an explicit ownership result."""

    row = _read_row(config_dir)
    marker = _marker_path(config_dir).is_file()
    installed = False
    if row is None:
        if marker:
            _sync_claude(project_dir, {}, False)
            _sync_codex(codex_config_dir, {}, False)
            return "deleted"
        if _live_has_custom(project_dir, codex_config_dir):
            return "custom-live"
        _insert_default(config_dir)
        row = _read_row(config_dir)
        installed = True

    assert row is not None
    server_json, enabled_claude, enabled_codex, tag_text = row
    if not marker:
        if DEFAULT_TAG not in _tags(tag_text):
            return "custom"
        _write_marker(config_dir)
    try:
        server = json.loads(server_json) if server_json else {}
    except (TypeError, ValueError):
        server = {}
    if not isinstance(server, dict) or server.get("url") != OFFICIAL_URL:
        return "custom-config"

    _sync_claude(project_dir, server, bool(enabled_claude))
    _sync_codex(codex_config_dir, server, bool(enabled_codex))
    return "installed" if installed else "synced"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument("--codex-config-dir", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    started = int(time.time())
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("a", encoding="utf-8") as log:
        try:
            result = synchronize(
                config_dir=args.config_dir,
                project_dir=args.project_dir,
                codex_config_dir=args.codex_config_dir,
                log=log,
            )
            print(f"{started} default github mcp: {result}", file=log)
            print(result)
            return 0
        except Exception:
            import traceback
            traceback.print_exc(file=log)
            print("failed")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
