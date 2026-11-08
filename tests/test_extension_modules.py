from contextlib import contextmanager
import copy
import json

import pytest

from aisc.application import extension_modules as modules
from aisc.domain.models import CliError


def member(kind='skills', identity='owner/repo:qa'):
    return {'kind': kind, 'identity': identity, 'name': identity}


def definition(identity='a', members=None):
    return {'id': identity, 'name': identity, 'members': members if members is not None else [member()]}


@pytest.fixture
def world(tmp_path, monkeypatch):
    state = {'skills': [], 'mcp': [], 'plugins': [], 'installs': [], 'removes': [], 'running': False}
    @contextmanager
    def scope(runtime, workspace, executor):
        yield None, 'qa-container', tmp_path / f'{runtime}.json'
    monkeypatch.setattr(modules, '_scope', scope)
    monkeypatch.setattr(modules, '_snapshot', lambda rid, ws, ex, kinds: {k: copy.deepcopy(state[k]) for k in set(kinds)})
    monkeypatch.setattr(modules, '_active', lambda *args: state['running'])
    def install(rid, ws, ex, m):
        state['installs'].append(m['identity'])
        if m['kind'] == 'skills':
            repo, directory = m['identity'].split(':')
            row = {'id': directory, 'name': directory, 'directory': directory, 'repo': repo}
        elif m['kind'] == 'plugins':
            row = {'id': m['identity'], 'name': m['identity'].split('@')[0], 'version': '1'}
        else:
            row = {'id': 'mcp-id', 'name': m['identity'].split('/')[-1], 'transport': 'http',
                   'auth_required': True, 'auth_configured': False}
        row['ownership_fingerprint'] = 'proof-of-original-content'
        state[m['kind']].append(row)
    monkeypatch.setattr(modules, '_install', install)
    def remove(rid, ws, ex, m, item_id):
        state['removes'].append(item_id)
        state[m['kind']] = [i for i in state[m['kind']] if i['id'] != item_id]
    monkeypatch.setattr(modules, '_remove', remove)
    state['path'] = tmp_path / 'runtime-a.json'
    return state


def plan(doc=None, action='apply', runtime='runtime-a'):
    return modules.module_plan(runtime, '/qa', {'definition': doc or definition(), 'action': action})


def step(prepared, index=0):
    return modules.module_step(prepared['runtime_id'], '/qa', {'plan_id': prepared['plan_id'], 'index': index})


def test_only_installs_missing_and_removes_last_module_reference(world):
    first = plan()
    assert first['rows'][0]['action'] == 'install'
    assert step(first)['status'] == 'installed'
    assert step(first)['status'] == 'installed'  # idempotent durable step
    assert step(plan(definition('b')))['status'] == 'retained'
    assert len(world['installs']) == 1
    assert step(plan(action='uninstall'))['reason'] == 'shared'
    assert world['removes'] == []
    assert step(plan(definition('b'), 'uninstall'))['status'] == 'removed'
    assert world['removes'] == ['qa']


def test_preinstalled_and_changed_assets_are_kept(world):
    world['skills'] = [{'id': 'qa', 'name': 'qa', 'directory': 'qa', 'repo': 'owner/repo'}]
    assert step(plan())['reason'] == 'preinstalled_or_changed'
    assert step(plan(action='uninstall'))['status'] == 'retained'
    assert world['installs'] == world['removes'] == []
    world['skills'].clear()
    assert step(plan())['status'] == 'installed'
    world['skills'][0]['enabled_claude'] = False
    assert step(plan(action='uninstall'))['reason'] == 'preinstalled_or_changed'
    assert world['removes'] == []


def test_mixed_members_and_mcp_auth_are_distinct_from_install_success(world):
    doc = definition(members=[member(), member('plugins', 'qa@market'), member('mcp', 'vendor/qa-mcp')])
    prepared = plan(doc)
    assert [step(prepared, i)['status'] for i in range(3)] == ['installed', 'installed', 'auth_required']
    uninstall = plan(doc, 'uninstall')
    assert [step(uninstall, i)['status'] for i in range(3)] == ['removed'] * 3


def test_unknown_mcp_source_and_different_skill_source_never_overwrite(world):
    world['mcp'] = [{'id': 'existing', 'name': 'qa', 'url': 'https://other.example'}]
    doc = definition(members=[member('mcp', 'vendor/qa')])
    assert step(plan(doc))['reason'] == 'source_unknown'
    assert step(plan(doc))['reason'] == 'source_unknown'
    assert step(plan(doc, 'uninstall'))['status'] == 'retained'
    world['skills'] = [{'id': 'qa', 'name': 'qa', 'repo': 'different/repo', 'directory': 'qa'}]
    assert step(plan())['reason'] == 'source_conflict'
    assert world['installs'] == world['removes'] == []


def test_crash_record_blocks_live_process_then_recovers_without_claiming_ownership(world, monkeypatch):
    original = modules._install
    def crash(*args):
        original(*args)
        raise KeyboardInterrupt()
    monkeypatch.setattr(modules, '_install', crash)
    with pytest.raises(KeyboardInterrupt):
        step(plan())
    assert next(iter(json.loads(world['path'].read_text())['assets'].values()))['pending']
    world['running'] = True
    assert step(plan())['reason'] == 'operation_running'
    world['running'] = False
    assert step(plan())['reason'] == 'preinstalled_or_changed'
    assert step(plan(action='uninstall'))['status'] == 'retained'
    assert world['removes'] == []


def test_partial_failure_can_retry_only_missing_members(world, monkeypatch):
    original = modules._install
    def fail_plugin(*args):
        if args[-1]['kind'] == 'plugins':
            raise CliError('failure token=private', error_code='AISC_ERR_EXTENSIONS_CLI_ERROR')
        original(*args)
    monkeypatch.setattr(modules, '_install', fail_plugin)
    doc = definition(members=[member(), member('plugins', 'qa@market')])
    prepared = plan(doc)
    assert step(prepared, 0)['status'] == 'installed'
    assert step(prepared, 1)['status'] == 'failed'
    assert 'private' not in world['path'].read_text()
    monkeypatch.setattr(modules, '_install', original)
    retry = plan(doc)
    assert step(retry, 0)['status'] == 'retained'
    assert step(retry, 1)['status'] == 'installed'
    assert world['installs'] == ['owner/repo:qa', 'qa@market']


def test_changed_plan_does_not_silently_introduce_a_new_mutation(world):
    world['skills'] = [{'id': 'qa', 'name': 'qa', 'directory': 'qa', 'repo': 'owner/repo'}]
    prepared = plan()
    world['skills'].clear()
    assert step(prepared)['reason'] == 'state_changed'
    assert world['installs'] == []


def test_failed_removal_can_retry_when_original_owned_item_is_unchanged(world, monkeypatch):
    step(plan())
    original = modules._remove
    def fail(*args):
        raise CliError('temporary remove failure')
    monkeypatch.setattr(modules, '_remove', fail)
    assert step(plan(action='uninstall'))['status'] == 'failed'
    monkeypatch.setattr(modules, '_remove', original)
    assert step(plan(action='uninstall'))['status'] == 'removed'


def test_changed_content_or_legacy_missing_proof_never_grants_removal(world, monkeypatch):
    step(plan())
    world['skills'][0]['ownership_fingerprint'] = 'user-edited-content'
    assert step(plan(action='uninstall'))['status'] == 'retained'
    world['skills'].clear()
    original = modules._install
    def legacy(*args):
        original(*args)
        world['skills'][0].pop('ownership_fingerprint')
    monkeypatch.setattr(modules, '_install', legacy)
    assert step(plan())['reason'] == 'ownership_unavailable'
    assert step(plan(action='uninstall'))['status'] == 'retained'
    assert world['removes'] == []


def test_definition_edits_keep_historical_members_until_explicit_uninstall(world):
    step(plan())
    edited = definition(members=[])
    assert plan(edited)['rows'] == []
    removal = plan(edited, 'uninstall')
    assert len(removal['rows']) == 1
    assert step(removal)['status'] == 'removed'


def test_target_has_separate_ownership_and_history(world):
    step(plan())
    other = plan(runtime='runtime-b')
    assert step(other)['reason'] == 'preinstalled_or_changed'
    assert step(plan(action='uninstall', runtime='runtime-b'))['status'] == 'retained'
    assert world['removes'] == []
    assert modules.module_status('runtime-c', '/qa', {'module_id': 'a'}) == {'latest': None}


@pytest.mark.parametrize('raw', ['{broken', '{"schema_version":99}', '{"schema_version":1,"assets":[],"plans":{}}'])
def test_corrupt_state_cannot_be_overwritten(world, raw):
    world['path'].write_text(raw)
    with pytest.raises(CliError):
        plan()
    assert world['path'].read_text() == raw
    assert world['installs'] == world['removes'] == []


def test_module_cli_reads_structured_request_from_stdin(world, monkeypatch):
    import io
    from types import SimpleNamespace
    from aisc.cli.commands.extensions import cmd_extensions_module
    monkeypatch.setattr('sys.stdin', io.StringIO(json.dumps({'definition': definition(), 'action': 'apply'})))
    prepared = cmd_extensions_module(SimpleNamespace(extensions_command='module-plan', runtime_id='runtime-a', workspace='/qa'))
    assert prepared['rows'][0]['action'] == 'install'
    assert world['installs'] == []
    monkeypatch.setattr('sys.stdin', io.StringIO('[]'))
    with pytest.raises(CliError):
        cmd_extensions_module(SimpleNamespace(extensions_command='module-step', runtime_id='runtime-a', workspace='/qa'))


def test_module_cli_decodes_utf8_bytes_despite_windows_stdin_locale(world, monkeypatch):
    import io
    from types import SimpleNamespace
    from aisc.cli.commands.extensions import cmd_extensions_module
    item = definition()
    item['name'] = '科研模块 日本語 🧪'
    request = json.dumps({'definition': item, 'action': 'apply'}, ensure_ascii=False).encode('utf-8')
    monkeypatch.setattr('sys.stdin', io.TextIOWrapper(io.BytesIO(request), encoding='ascii', errors='surrogateescape'))
    result = cmd_extensions_module(SimpleNamespace(extensions_command='module-plan', runtime_id='runtime-a', workspace='/qa'))
    assert result['module_name'] == item['name']
    assert json.loads(world['path'].read_text(encoding='utf-8'))['plans'][result['plan_id']]['module_name'] == item['name']
    assert world['installs'] == []


def test_module_cli_rejects_invalid_utf8_before_mutation(world, monkeypatch):
    import io
    from types import SimpleNamespace
    from aisc.cli.commands.extensions import cmd_extensions_module
    monkeypatch.setattr('sys.stdin', io.TextIOWrapper(io.BytesIO(b'{"name":"\xff"}'), encoding='latin1'))
    with pytest.raises(CliError) as caught:
        cmd_extensions_module(SimpleNamespace(extensions_command='module-plan', runtime_id='runtime-a', workspace='/qa'))
    assert caught.value.error_code == 'AISC_ERR_USAGE'
    assert not world['path'].exists()
    assert world['installs'] == world['removes'] == []


def test_marker_and_container_identity_reach_real_adapter_bridge(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from aisc.application import extensions as ext
    from aisc.application.extension_operation_scope import operation_marker, expected_container
    calls = []
    def execute(argv, **kwargs):
        calls.append(argv)
        output = 'container-a' if argv[0] == 'container' else json.dumps({'schema': ext.PROTOCOL, 'ok': True})
        return SimpleNamespace(exit_code=0, stdout=output, stderr='')
    executor = SimpleNamespace(run_captured=execute)
    monkeypatch.setattr(ext, 'resolve_running_container', lambda *args: 'qa')
    marker = operation_marker.set('test-marker')
    target = expected_container.set('container-a')
    try:
        ext._exec_adapter('runtime-a', tmp_path, executor, 'plugin-install', item_id='qa@market')
        assert ['-e', 'AISC_MODULE_OPERATION_ID=test-marker'] == calls[-1][2:4]
        expected_container.set('container-b')
        with pytest.raises(CliError):
            ext._exec_adapter('runtime-a', tmp_path, executor, 'plugin-install', item_id='qa@market')
        assert len([argv for argv in calls if argv[0] == 'exec']) == 1
    finally:
        operation_marker.reset(marker)
        expected_container.reset(target)


def test_old_adapter_falls_back_only_to_read_only_unowned_snapshot(monkeypatch):
    calls = []
    def listing(rid, kind, workspace, executor, *, ownership=False):
        calls.append(ownership)
        if ownership:
            raise CliError('unsupported ownership', error_code=modules.ext.UNSUPPORTED_OP)
        return {'items': [{'id': 'old', 'name': 'old'}]}
    monkeypatch.setattr(modules.ext, 'extensions_list', listing)
    result = modules._snapshot('runtime-a', '/qa', None, ['skills'])
    assert calls == [True, False]
    assert 'ownership_fingerprint' not in result['skills'][0]
