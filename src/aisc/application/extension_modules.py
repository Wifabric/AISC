"""Durable, conservative orchestration of existing extension operations.

Plans are confirmed snapshots; each step rechecks the real target. Ownership
is earned only by a completed, verified install, never inferred after a crash.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid

from aisc.adapters.docker_ import RealDockerExecutor
from aisc.application import extensions as ext
from aisc.application.extension_operation_scope import expected_container, mutation_scope, operation_marker
from aisc.domain.models import CliError


def _error(message, code='AISC_ERR_EXTENSIONS_MODULE_STATE'):
    raise CliError(message=message, exit_code=1, error_code=code)


def _key(member):
    return member['kind'] + ':' + member['identity']


def _member(value):
    if not isinstance(value, dict) or value.get('kind') not in ('skills', 'mcp', 'plugins'):
        _error('Invalid module member', 'AISC_ERR_USAGE')
    identity = value.get('identity')
    if not isinstance(identity, str) or not identity or len(identity) > 2048 or any(c.isspace() or ord(c) < 32 for c in identity):
        _error('Invalid module member identity', 'AISC_ERR_USAGE')
    if value['kind'] == 'skills' and (':' not in identity or '/' not in identity.split(':')[0]):
        _error('Skills require repository:directory identity', 'AISC_ERR_USAGE')
    if value['kind'] == 'plugins' and '@' not in identity:
        _error('Plugins require name@marketplace identity', 'AISC_ERR_USAGE')
    return {'kind': value['kind'], 'identity': identity, 'name': str(value.get('name') or identity)[:512]}


def _definition(value):
    if not isinstance(value, dict) or not isinstance(value.get('id'), str) or not 1 <= len(value['id']) <= 128:
        _error('Invalid module definition ID', 'AISC_ERR_USAGE')
    members = value.get('members')
    if not isinstance(members, list) or len(members) > 200:
        _error('Invalid module member list', 'AISC_ERR_USAGE')
    return {'id': value['id'], 'name': str(value.get('name') or value['id'])[:512],
            'members': list({_key(m): m for m in map(_member, members)}.values())}


def _load(path):
    if not path.exists():
        return {'schema_version': 1, 'assets': {}, 'plans': {}}
    try:
        if path.stat().st_size > 8_000_000:
            raise ValueError('oversized')
        doc = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(doc, dict) or doc.get('schema_version') != 1:
            raise ValueError('unsupported schema')
        if not isinstance(doc.get('assets'), dict) or not isinstance(doc.get('plans'), dict):
            raise ValueError('invalid tables')
        for key, asset in doc['assets'].items():
            if (not isinstance(asset, dict) or _key(_member(asset.get('member'))) != key
                    or type(asset.get('owned')) is not bool or not isinstance(asset.get('modules'), list)
                    or not all(isinstance(m, str) for m in asset['modules'])):
                raise ValueError('invalid asset')
        for plan in doc['plans'].values():
            if not isinstance(plan, dict) or not isinstance(plan.get('rows'), list) or plan.get('action') not in ('apply', 'uninstall'):
                raise ValueError('invalid plan')
        return doc
    except (ValueError, OSError, CliError) as exc:
        _error('Module operation state is unreadable; original file preserved. ' + type(exc).__name__)


def _save(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='module-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(doc, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def _scope(runtime_id, workspace, executor):
    try:
        if uuid.UUID(runtime_id).version != 4:
            raise ValueError()
    except (ValueError, AttributeError):
        _error('Invalid runtime UUID', 'AISC_ERR_USAGE')
    root = ext._registry_root(workspace)
    executor = executor or RealDockerExecutor()
    with mutation_scope(root, runtime_id):
        container = ext.resolve_running_container(runtime_id, executor, root)
        inspected = executor.run_captured(['container', 'inspect', container, '--format', '{{.Id}}'], timeout=15.0)
        identity = inspected.stdout.strip()
        if inspected.exit_code != 0 or not identity:
            _error('Cannot verify runtime container identity')
        path = root / 'extension-operations' / (hashlib.sha256((runtime_id + ':' + identity).encode()).hexdigest() + '.json')
        token = expected_container.set(identity)
        try:
            yield executor, container, path
        finally:
            expected_container.reset(token)


def _snapshot(runtime_id, workspace, executor, kinds):
    snapshots = {}
    for kind in sorted(set(kinds)):
        try:
            snapshots[kind] = ext.extensions_list(runtime_id, kind, workspace, executor, ownership=True)['items']
        except CliError as exc:
            if exc.error_code != ext.UNSUPPORTED_OP:
                raise
            # Read-only legacy fallback; lack of proof never grants deletion.
            snapshots[kind] = ext.extensions_list(runtime_id, kind, workspace, executor)['items']
    return snapshots


def _fingerprint(item):
    # Only a hash is persisted. No MCP configuration/header/env values are
    # returned by list, and this whitelist also excludes descriptive text.
    keys = ('id', 'repo', 'directory', 'source', 'sources', 'conflict', 'version',
            'installed_at', 'created_at', 'updated_at', 'git_commit_sha', 'transport',
            'url', 'command', 'args', 'enabled_claude', 'enabled_codex',
            'auth_required', 'auth_claude_configured', 'auth_codex_configured', 'ownership_fingerprint')
    return hashlib.sha256(json.dumps({k: item[k] for k in keys if k in item}, sort_keys=True).encode()).hexdigest()


def _match(member, items, asset):
    identity = member['identity']
    if asset.get('item_id'):
        found = [i for i in items if i.get('id') == asset['item_id']]
        if len(found) == 1:
            if member['kind'] == 'skills' and f"{found[0].get('repo', '')}:{found[0].get('directory') or found[0].get('id', '')}" != identity:
                return found[0], 'ambiguous'
            return found[0], 'recorded'
    if member['kind'] == 'skills':
        exact = [i for i in items if f"{i.get('repo', '')}:{i.get('directory') or i.get('id', '')}" == identity]
        name = identity.split(':', 1)[1].rsplit('/', 1)[-1]
    elif member['kind'] == 'plugins':
        exact = [i for i in items if i.get('id') == identity]
        name = identity.split('@', 1)[0]
    else:
        exact = []  # Legacy MCP snapshots cannot prove a market identity.
        name = identity.rsplit('/', 1)[-1]
    if len(exact) == 1:
        return exact[0], 'exact'
    collisions = [i for i in items if i.get('name') == name or i.get('id') == name
                  or str(i.get('directory', '')).rsplit('/', 1)[-1] == name]
    return (collisions[0], 'ambiguous') if collisions else (None, 'missing')


def _active(executor, container, marker):
    # Inspect only whether OUR random marker exists in process environments;
    # never return any environment contents or credentials to the host/UI.
    script = """import pathlib,sys
needle=('AISC_MODULE_OPERATION_ID='+sys.argv[1]).encode()
active=False
for proc in pathlib.Path('/proc').iterdir():
 if not proc.name.isdigit(): continue
 try: active = active or needle in (proc/'environ').read_bytes().split(b'\\0')
 except FileNotFoundError: pass
 except PermissionError: sys.exit(2)
print('running' if active else 'finished')
"""
    result = executor.run_captured(['exec', container, 'python3', '-c', script, marker], timeout=15.0)
    if result.exit_code != 0 or result.stdout.strip() not in ('running', 'finished'):
        _error('Cannot determine whether the previous module operation is still running')
    return result.stdout.strip() == 'running'


def _reconcile(doc, snapshots, executor, container):
    for asset in doc['assets'].values():
        pending = asset.get('pending')
        if not pending or asset['member']['kind'] not in snapshots:
            continue
        if _active(executor, container, pending['marker']):
            continue
        # The child finished, but completion was not durably acknowledged.
        # Never infer deletion authority from a post-crash installed item.
        item, _ = _match(asset['member'], snapshots[asset['member']['kind']], asset)
        # A failed removal may leave the previously owned, unchanged item.
        # Retain that existing proof so the removal can be retried. An
        # interrupted INSTALL never gains ownership from its later presence.
        asset['owned'] = bool(pending['action'] == 'remove' and asset.get('owned')
                              and item and asset.get('fingerprint') == _fingerprint(item))
        asset['item_id'] = item.get('id') if item else None
        asset['fingerprint'] = _fingerprint(item) if item else None
        asset.pop('pending', None)


def _decision(member, module_id, action, doc, items):
    asset = doc['assets'].get(_key(member), {})
    item, match = _match(member, items, asset)
    row = {'member': member, 'key': _key(member), 'status': 'planned',
           'action': 'retain', 'reason': '', 'auth_required': bool(item and item.get('auth_required') and not item.get('auth_configured'))}
    if asset.get('pending'):
        row.update(action='blocked', reason='operation_running')
    elif action == 'apply':
        if item is None:
            row.update(action='install', reason='missing')
        elif match == 'ambiguous' and member['kind'] != 'mcp':
            row.update(action='blocked', reason='source_conflict')
        else:
            owned = asset.get('owned') and asset.get('fingerprint') == _fingerprint(item)
            row['reason'] = 'already_managed' if owned else ('source_unknown' if match == 'ambiguous' else 'preinstalled_or_changed')
    elif module_id not in asset.get('modules', []):
        row.update(action='retain', reason='not_owned')
    elif any(m != module_id for m in asset['modules']):
        row.update(action='release', reason='shared')
    elif item is None:
        row.update(action='release', reason='already_absent')
    elif asset.get('owned') and asset.get('fingerprint') == _fingerprint(item) and not item.get('conflict'):
        row.update(action='remove', reason='exclusive_owned')
    else:
        row.update(action='release', reason='preinstalled_or_changed')
    return row


def module_plan(runtime_id, workspace, request, executor=None):
    definition = _definition(request.get('definition'))
    action = request.get('action')
    if action not in ('apply', 'uninstall'):
        _error('Invalid module action', 'AISC_ERR_USAGE')
    with _scope(runtime_id, workspace, executor) as (executor, container, path):
        doc = _load(path)
        members = {_key(m): m for m in definition['members']}
        if action == 'uninstall':
            members.update({key: a['member'] for key, a in doc['assets'].items() if definition['id'] in a['modules']})
        snapshots = _snapshot(runtime_id, workspace, executor, [m['kind'] for m in members.values()])
        _reconcile(doc, snapshots, executor, container)
        rows = [_decision(m, definition['id'], action, doc, snapshots[m['kind']]) for m in members.values()]
        plan_id = str(uuid.uuid4())
        plan = {'plan_id': plan_id, 'module_id': definition['id'], 'module_name': definition['name'],
                'action': action, 'rows': rows, 'runtime_id': runtime_id}
        # Keep a bounded history; pending assets remain independently durable.
        while len(doc['plans']) >= 40:
            del doc['plans'][next(iter(doc['plans']))]
        doc['plans'][plan_id] = plan
        _save(path, doc)
        return plan


def _install(runtime_id, workspace, executor, member):
    if member['kind'] == 'skills':
        return ext.extensions_skill_install(runtime_id, member['identity'], workspace, executor)
    if member['kind'] == 'plugins':
        return ext.extensions_plugin_install(runtime_id, member['identity'], workspace, executor)
    return ext.extensions_call_raw(runtime_id, 'mcp-market-install', workspace, executor, item_id=member['identity'])


def _remove(runtime_id, workspace, executor, member, item_id):
    if member['kind'] == 'plugins':
        return ext.extensions_plugin_uninstall(runtime_id, item_id, workspace, executor)
    return ext.extensions_delete(runtime_id, member['kind'], item_id, workspace, executor)


def module_step(runtime_id, workspace, request, executor=None):
    with _scope(runtime_id, workspace, executor) as (executor, container, path):
        doc = _load(path)
        plan = doc['plans'].get(request.get('plan_id'))
        index = request.get('index')
        if not plan or type(index) is not int or not 0 <= index < len(plan['rows']):
            _error('Module plan expired or invalid; prepare again', 'AISC_ERR_USAGE')
        previous = plan['rows'][index]
        if previous['status'] != 'planned':
            return previous
        member = previous['member']
        key, kind, module_id = _key(member), member['kind'], plan['module_id']
        snapshots = _snapshot(runtime_id, workspace, executor, [kind])
        _reconcile(doc, snapshots, executor, container)
        row = _decision(member, module_id, plan['action'], doc, snapshots[kind])
        if row['action'] in ('install', 'remove') and row['action'] != previous['action']:
            row.update(action='blocked', reason='state_changed')
        asset = doc['assets'].setdefault(key, {'member': member, 'owned': False, 'modules': []})
        item, match = _match(member, snapshots[kind], asset)
        if asset.get('owned') and (not item or asset.get('fingerprint') != _fingerprint(item)):
            asset['owned'] = False
        if row['action'] == 'blocked':
            row['status'] = 'blocked'
        elif row['action'] in ('retain', 'release'):
            if plan['action'] == 'apply':
                asset['modules'] = sorted(set(asset['modules'] + [module_id]))
                asset['item_id'] = item.get('id') if item else None
                # Preserve ambiguity across plans; never turn a same-name MCP
                # into a verified market binding just because we retained it.
                if match == 'ambiguous':
                    asset['item_id'] = None
                row['status'] = 'auth_required' if row['auth_required'] else 'retained'
            else:
                asset['modules'] = [m for m in asset['modules'] if m != module_id]
                row['status'] = 'retained' if item else 'absent'
        else:
            marker = str(uuid.uuid4())
            asset['pending'] = {'marker': marker, 'action': row['action']}
            row['status'] = 'pending'
            plan['rows'][index] = row
            _save(path, doc)
            token = operation_marker.set(marker)
            try:
                if row['action'] == 'install':
                    _install(runtime_id, workspace, executor, member)
                else:
                    _remove(runtime_id, workspace, executor, member, item['id'])
                after = _snapshot(runtime_id, workspace, executor, [kind])[kind]
                actual, relation = _match(member, after, asset)
                if row['action'] == 'install':
                    before_ids = {i['id'] for i in snapshots[kind]}
                    if not actual or actual['id'] in before_ids:
                        _error('Install did not produce a uniquely identifiable new member')
                    asset.update(owned=bool(actual.get('ownership_fingerprint')), item_id=actual['id'], fingerprint=_fingerprint(actual),
                                 modules=sorted(set(asset['modules'] + [module_id])))
                    if not asset['owned']:
                        row['reason'] = 'ownership_unavailable'
                    row['auth_required'] = bool(actual.get('auth_required') and not actual.get('auth_configured'))
                    row['status'] = 'auth_required' if row['auth_required'] else 'installed'
                else:
                    if any(i.get('id') == item['id'] for i in after):
                        _error('Remove did not remove the selected member')
                    asset.update(owned=False, item_id=None, fingerprint=None,
                                 modules=[m for m in asset['modules'] if m != module_id])
                    row['status'] = 'removed'
                asset.pop('pending', None)
            except Exception as exc:
                # Keep pending durable until the target process and real state
                # can be reconciled. Do not store potentially secret CLI output.
                row['status'] = 'unknown'
                row['reason'] = getattr(exc, 'error_code', None) or 'AISC_ERR_EXTENSIONS_EXEC_FAILED'
                try:
                    after = _snapshot(runtime_id, workspace, executor, [kind])
                    _reconcile(doc, after, executor, container)
                    if not asset.get('pending'):
                        row['status'] = 'failed'
                except Exception:
                    pass
            finally:
                operation_marker.reset(token)
        plan['rows'][index] = row
        _save(path, doc)
        return row


def module_status(runtime_id, workspace, request, executor=None):
    with _scope(runtime_id, workspace, executor) as (_, _, path):
        doc = _load(path)
        plans = [p for p in doc['plans'].values() if p['module_id'] == request.get('module_id')]
        return {'latest': plans[-1] if plans else None}
