"""Configure the owned GitHub MCP using the existing SQLite/live config store.

No credential reads cross the adapter boundary. Tokens arrive on stdin, never
argv; only selected engines are changed. Connection checks are explicit reads.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tomllib
import urllib.request
import urllib.error

import default_mcp as default


class AuthError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _files(project, codex):
    return {'claude': project / '.mcp.json', 'codex': codex / 'config.toml'}


def _read(path):
    if path.is_symlink():
        raise AuthError('CUSTOM_CONFIG')
    if not path.exists():
        return None
    if path.stat().st_size > 4_000_000:
        raise AuthError('CONFIG_INVALID')
    return path.read_bytes()


def _row(connection, config_dir):
    row = connection.execute('SELECT server_config,enabled_claude,enabled_codex,tags FROM mcp_servers WHERE id=?', ('github',)).fetchone()
    if not row:
        raise AuthError('NOT_FOUND')
    server = json.loads(row[0])
    if not isinstance(server, dict) or server.get('url') != default.OFFICIAL_URL or not (
        (config_dir/default.MARKER_FILE).is_file() or default.DEFAULT_TAG in default._tags(row[3])
    ):
        raise AuthError('CUSTOM_CONFIG')
    return row, server


def _live(agent, raw):
    doc = (json.loads(raw) if agent == 'claude' else tomllib.loads(raw.decode('utf-8'))) if raw else {}
    item = doc.get('mcpServers' if agent == 'claude' else 'mcp_servers', {}).get('github', {})
    if not isinstance(item, dict) or (item and item.get('url') != default.OFFICIAL_URL):
        raise AuthError('CUSTOM_CONFIG')
    return item


def _revision(row, files):
    digest = hashlib.sha256(json.dumps(list(row), sort_keys=True).encode())
    for agent, raw in sorted(files.items()):
        digest.update(agent.encode() + b'\0' + (raw or b''))
    return digest.hexdigest()


def _authorization(agent, item):
    headers = item.get('headers' if agent == 'claude' else 'http_headers') or {}
    value = headers.get('Authorization', '') if isinstance(headers, dict) else ''
    if value:
        return str(value)
    if agent == 'codex':
        name = item.get('bearer_token_env_var')
        token = os.environ.get(name, '') if isinstance(name, str) else ''
        return 'Bearer '+token if token.strip() else ''
    return ''


def _state(row, files):
    return {'revision': _revision(row, files), 'engines': {
        agent: {'enabled': bool(row[index+1]), 'configured': bool(_authorization(agent, _live(agent, files[agent]))),
                'connection': 'not_verified'} for index,agent in enumerate(('claude','codex'))}}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _check(agent, item):
    authorization = _authorization(agent, item)
    if not authorization:
        return 'missing_config'
    request = urllib.request.Request(default.OFFICIAL_URL, method='POST',
        headers={'Authorization': authorization, 'Content-Type':'application/json',
                 'Accept':'application/json, text/event-stream'},
        data=json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize','params':{
            'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'aisc-config-check','version':'1'}}}).encode())
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=10) as response:
            raw = response.read(1_000_001).decode('utf-8')
        payloads = [raw] if raw.lstrip().startswith('{') else [line[5:].strip() for line in raw.splitlines() if line.startswith('data:')]
        for payload in payloads:
            result = json.loads(payload)
            if isinstance(result, dict) and result.get('id') == 1 and isinstance(result.get('result'), dict) and result['result'].get('protocolVersion'):
                return 'connected'
        return 'protocol_error'
    except urllib.error.HTTPError as exc:
        return 'auth_failed' if exc.code == 401 else 'access_denied' if exc.code == 403 else 'http_error'
    except (OSError, ValueError, urllib.error.URLError):
        return 'connection_failed'


def handle(op, request, *, config_dir, project_dir, codex_dir):
    """Return only flags/revision/stable result codes, never token-bearing data."""
    if not (config_dir/'cc-switch.db').is_file():
        raise AuthError('NOT_FOUND')
    paths = _files(project_dir, codex_dir)
    connection = sqlite3.connect(config_dir/'cc-switch.db', timeout=10)
    try:
        if op == 'github-auth-save':
            connection.execute('BEGIN IMMEDIATE')
        row, server = _row(connection, config_dir)
        snapshots = {agent: _read(path) for agent,path in paths.items()}
        state = _state(row, snapshots)
        if op == 'github-auth-status':
            return state
        agents = request.get('agents')
        if not isinstance(agents, list) or not agents or any(a not in paths for a in agents):
            raise AuthError('INVALID_REQUEST')
        agents = list(dict.fromkeys(agents))
        if request.get('revision') != state['revision']:
            raise AuthError('CONFLICT')
        if op == 'github-auth-check':
            for agent in agents:
                state['engines'][agent]['connection'] = _check(agent, _live(agent, snapshots[agent])) if state['engines'][agent]['enabled'] else 'disabled'
            current_row, _ = _row(connection, config_dir)
            if _revision(current_row, {agent: _read(path) for agent,path in paths.items()}) != state['revision']:
                raise AuthError('CONFLICT')
            return state
        if op != 'github-auth-save':
            raise AuthError('INVALID_REQUEST')
        token = request.get('token')
        if not isinstance(token, str) or not 8 <= len(token) <= 4096 or any(c.isspace() or ord(c)<32 or ord(c)>126 for c in token):
            raise AuthError('INVALID_REQUEST')
        for agent in agents:
            if not state['engines'][agent]['enabled']:
                raise AuthError('DISABLED')
            key = 'headers' if agent == 'claude' else 'http_headers'
            headers = dict(server.get(key) or {})
            headers.update(_live(agent, snapshots[agent]).get(key) or {})
            headers['Authorization'] = 'Bearer '+token
            server[key] = headers
        changed = []
        try:
            for agent in agents:
                # Detect an external editor between preflight and each write.
                if _read(paths[agent]) != snapshots[agent]:
                    raise AuthError('CONFLICT')
                changed.append(agent)
                if agent == 'claude':
                    default._sync_claude(project_dir, server, True)
                else:
                    default._sync_codex(codex_dir, server, True)
            connection.execute('UPDATE mcp_servers SET server_config=? WHERE id=?', (json.dumps(server), 'github'))
            new_row, _ = _row(connection, config_dir)
            result = _state(new_row, {agent: _read(path) for agent,path in paths.items()})
            connection.commit()
        except Exception:
            connection.rollback()
            for agent in changed:
                raw = snapshots[agent]
                if raw is None:
                    paths[agent].unlink(missing_ok=True)
                else:
                    default._atomic_write(paths[agent], raw.decode('utf-8'), mode=0o600)
            raise
        return result
    except AuthError:
        raise
    except Exception:
        # JSON/SQLite/filesystem/network errors can contain credentials. Keep
        # the public error stable and deliberately omit raw exception text.
        raise AuthError('CONFIG_FAILED') from None
    finally:
        connection.close()
