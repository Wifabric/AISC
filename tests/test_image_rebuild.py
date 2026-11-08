import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from aisc.application.image_rebuild import rebuild_check, guarded_rebuild, cleanup_rebuild_tag
from aisc.domain.models import CliError, ImageInspectStatus, ProcessResult

OLD = 'sha256:' + 'a' * 64
NEW = 'sha256:' + 'b' * 64
REF = 'super-claude:qa'

class Docker:
    def __init__(self):
        self.refs = {REF: OLD, 'super-claude:keep': OLD}
        self.containers = []
        self.calls = []
        self.build_failure = False
        self.cancel = False
        self.during_build = None
    def inspect_image(self, ref):
        return SimpleNamespace(status=ImageInspectStatus.EXISTS, image_id=OLD)
    def run_captured(self, argv, timeout=None):
        self.calls.append(argv)
        out, err, code = '', '', 0
        if argv[:2] == ['image', 'inspect']:
            ref = argv[2]
            if argv[-1] == '{{json .RepoTags}}':
                out = json.dumps([r for r, i in self.refs.items() if i == ref])
            else:
                out = self.refs.get(ref, ref if ref in self.refs.values() else '')
                if not out: code, err = 1, 'No such image'
        elif argv[0] == 'ps':
            out = '\n'.join(c[0] for c in self.containers)
        elif argv[:2] == ['container', 'inspect']:
            out = '\n'.join(f'/{name}\t{identity}\t{str(running).lower()}' for name, identity, running in self.containers)
        elif argv[0] == 'tag': self.refs[argv[2]] = self.refs.get(argv[1], argv[1])
        elif argv[0] == 'rmi': self.refs.pop(argv[1], None)
        return ProcessResult(exit_code=code, stdout=out, stderr=err, command_not_found=False, timed_out=False)
    def run_streaming_captured(self, argv, on_chunk, timeout=None):
        self.calls.append(argv)
        on_chunk('stderr', '#1 [1/2] FROM scratch\n#1 DONE 0.1s\n')
        if self.during_build: self.during_build()
        if self.cancel: raise KeyboardInterrupt()
        if not self.build_failure:
            self.refs[argv[argv.index('-t') + 1]] = NEW
        return ProcessResult(exit_code=1 if self.build_failure else 0, stdout='', stderr='', command_not_found=False, timed_out=False)

class Events:
    def __init__(self): self.rows = []
    def emit(self, kind, data): self.rows.append((kind, data))

@pytest.fixture
def setup_rebuild(tmp_path):
    def plan(root, *, tag, no_cache, **kw):
        return SimpleNamespace(build_arg_node_image='node:22-slim', node_image_mirrors=(), pull=False,
            docker_argv=['build', '-t', tag, '--build-arg', 'NODE_IMAGE=node:22-slim',
                         *(['--no-cache'] if no_cache else []), str(root)])
    with patch('aisc.application.image_rebuild._assert_image_operable', return_value={'id': OLD}), \
         patch('aisc.application.image_rebuild._cc_switch_for_rebuild', return_value=None), \
         patch('aisc.application.image_rebuild.plan_build', side_effect=plan), \
         patch('aisc.application.image_rebuild._open_build_log', return_value=tmp_path / 'build.log'):
        yield tmp_path

def run(docker, root, **kw):
    return guarded_rebuild(docker, root=str(root), tag=REF, expected_image_id=OLD,
        data_root=root, **kw)

def test_precheck_reports_only_exact_image_containers(setup_rebuild):
    docker = Docker()
    docker.containers = [('running', OLD, True), ('stopped', OLD, False), ('descendant', NEW, True)]
    state = rebuild_check(docker, tag=REF)
    assert state['running_containers'] == ['running']
    assert state['containers'] == ['running', 'stopped']

def test_running_container_refuses_without_build_or_removal(setup_rebuild):
    docker = Docker(); docker.containers = [('working', OLD, True)]
    with pytest.raises(CliError) as error: run(docker, setup_rebuild)
    assert 'working' in error.value.message
    assert not any(c[0] in ('build', 'tag', 'rmi', 'stop', 'rm') for c in docker.calls)

@pytest.mark.parametrize('no_cache', [True, False])
def test_success_publishes_selected_ref_and_preserves_other_tags(setup_rebuild, no_cache):
    docker = Docker(); events = Events()
    result = run(docker, setup_rebuild, no_cache=no_cache, emitter=events)
    assert docker.refs == {REF: NEW, 'super-claude:keep': OLD}
    assert result['old_image_action'] == 'kept_tagged'
    build = next(c for c in docker.calls if c[0] == 'build')
    assert ('--no-cache' in build) == no_cache
    assert build[build.index('-t') + 1] != REF
    assert any(kind == 'build.output' for kind, _ in events.rows)
    assert any(kind == 'build.progress' for kind, _ in events.rows)
    start = next(data for kind, data in events.rows if kind == 'build.start')
    assert start['temporary_tag'] == build[build.index('-t') + 1]

@pytest.mark.parametrize('cancel', [False, True])
def test_build_failure_or_cancel_keeps_original(setup_rebuild, cancel):
    docker = Docker(); docker.cancel = cancel; docker.build_failure = not cancel
    before = dict(docker.refs)
    with pytest.raises(KeyboardInterrupt if cancel else CliError): run(docker, setup_rebuild)
    assert docker.refs == before
    assert not any(c[0] == 'tag' for c in docker.calls)

def test_stale_reference_refuses_before_build(setup_rebuild):
    docker = Docker(); docker.refs[REF] = NEW
    with pytest.raises(CliError): run(docker, setup_rebuild)
    assert not any(c[0] == 'build' for c in docker.calls)

def test_container_started_during_build_prevents_publication(setup_rebuild):
    docker = Docker()
    docker.during_build = lambda: docker.containers.append(('started-late', OLD, True))
    with pytest.raises(CliError): run(docker, setup_rebuild)
    assert docker.refs == {REF: OLD, 'super-claude:keep': OLD}

def test_stopped_container_preserves_old_image(setup_rebuild):
    docker = Docker(); del docker.refs['super-claude:keep']
    docker.containers = [('stopped', OLD, False)]
    result = run(docker, setup_rebuild)
    assert result['old_image_action'] == 'kept_referenced'
    assert ['rmi', OLD] not in docker.calls

def test_missing_image_is_build_and_expected_absence_is_enforced(setup_rebuild):
    docker = Docker(); docker.refs.clear()
    result = guarded_rebuild(docker, root=str(setup_rebuild), tag=REF,
        expected_image_id='', data_root=setup_rebuild)
    assert result['new_image_id'] == NEW
    assert result['old_image_action'] == 'not_found'
    with pytest.raises(CliError):
        rebuild_check(docker, tag=REF, expected_image_id='')

def test_reference_changed_during_build_is_not_overwritten(setup_rebuild):
    docker = Docker()
    docker.during_build = lambda: docker.refs.update({REF: 'sha256:' + 'c' * 64})
    with pytest.raises(CliError): run(docker, setup_rebuild)
    assert docker.refs[REF] == 'sha256:' + 'c' * 64
    assert not any(c[0] == 'tag' for c in docker.calls)

@pytest.mark.parametrize('failure', ['', 'unverified', 'builder'])
def test_guarded_rebuild_uses_verified_mirror_fallback_before_publication(setup_rebuild, failure):
    digest = 'sha256:' + 'd' * 64
    base_id = 'sha256:' + 'c' * 64
    first = 'first.example/node:22-slim@' + digest
    fallback = 'fallback.example/node:22-slim@' + digest
    local = 'aisc-node-base:' + digest.replace(':', '-')

    class PinnedDocker(Docker):
        def __init__(self):
            super().__init__()
            self.bases = {}
        def inspect_image(self, ref):
            return SimpleNamespace(status=ImageInspectStatus.EXISTS if ref in self.bases else ImageInspectStatus.MISSING,
                                   image_id=self.bases.get(ref, {}).get('Id', ''))
        def run_captured(self, argv, timeout=None):
            if argv == ['context', 'show']:
                self.calls.append(argv)
                return ProcessResult(exit_code=0, stdout='desktop-linux\n')
            if argv == ['buildx', 'inspect', 'desktop-linux']:
                self.calls.append(argv)
                driver = 'remote' if failure == 'builder' else 'docker'
                return ProcessResult(exit_code=0, stdout=f'Driver: {driver}\nEndpoint: desktop-linux\n')
            if argv[0] == 'pull':
                self.calls.append(argv)
                if argv[1] != fallback:
                    return ProcessResult(exit_code=1, stderr='first mirror unavailable')
                self.bases[fallback] = {'Id': base_id, 'RepoDigests': [] if failure == 'unverified' else ['node@' + digest]}
                return ProcessResult(exit_code=0)
            if argv[:2] == ['image', 'inspect'] and len(argv) == 3:
                self.calls.append(argv)
                doc = self.bases.get(argv[2])
                return ProcessResult(exit_code=0 if doc else 1, stdout=json.dumps([doc]) if doc else '[]')
            if argv[:2] == ['tag', base_id]:
                self.calls.append(argv)
                self.bases[argv[2]] = self.bases[fallback]
                return ProcessResult(exit_code=0)
            return super().run_captured(argv, timeout)

    def pinned_plan(root, *, tag, no_cache, pull, **kw):
        return SimpleNamespace(build_arg_node_image=first, node_image_mirrors=('fallback.example',), pull=pull,
            docker_argv=['build', '--pull', '-t', tag, '--build-arg', 'NODE_IMAGE=' + first,
                         *(['--no-cache'] if no_cache else []), str(root)])
    docker = PinnedDocker(); events = Events()
    with patch('aisc.application.image_rebuild.plan_build', side_effect=pinned_plan):
        if failure:
            with pytest.raises(CliError): run(docker, setup_rebuild, pull=True, emitter=events)
            assert docker.refs == {REF: OLD, 'super-claude:keep': OLD}
            assert not any(c[0] in ('build', 'tag') for c in docker.calls)
        else:
            result = run(docker, setup_rebuild, pull=True, emitter=events)
            build = next(c for c in docker.calls if c[0] == 'build')
            assert [c for c in docker.calls if c[0] == 'pull'] == [['pull', first], ['pull', fallback]]
            assert build[1:3] == ['--builder', 'desktop-linux']
            assert 'NODE_IMAGE=' + local in build and '--pull' not in build and '--no-cache' in build
            assert result['new_image_id'] == NEW and docker.refs['super-claude:keep'] == OLD
            assert any(kind == 'build.output' and fallback in data['chunk'] for kind, data in events.rows)


def test_cli_cache_switch_and_expected_identity():
    from aisc.cli.main import _build_parser
    parser = _build_parser()
    base = ['maintenance', 'docker-rebuild', '--root', 'bundle', '--guarded', '--expected-image-id', '', '--events']
    assert parser.parse_args(base).no_cache is True
    assert parser.parse_args(base + ['--use-cache']).no_cache is False
    assert parser.parse_args(base).expected_image_id == ''
    with pytest.raises(SystemExit): parser.parse_args(base + ['--use-cache', '--no-cache'])

@pytest.mark.parametrize('failure', [False, True])
def test_guarded_cli_emits_build_terminal_protocol(tmp_path, monkeypatch, capsys, failure):
    from aisc.cli.main import main
    monkeypatch.setenv('AISC_DATA_ROOT', str(tmp_path / 'data'))
    with patch('aisc.application.image_rebuild.guarded_rebuild') as build:
        build.return_value = {'new_image_id': NEW, 'old_image_action': 'kept_tagged'}
        if failure:
            build.side_effect = CliError(message='old reference changed', exit_code=6, error_code='AISC_ERR_IMAGE_REF_CONFLICT')
        with pytest.raises(SystemExit) as result:
            main(['maintenance', 'docker-rebuild', '--root', str(tmp_path), '--tag', REF,
                  '--guarded', '--expected-image-id', OLD, '--events'])
    assert result.value.code == (6 if failure else 0)
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert events[-1]['type'] == ('build.failed' if failure else 'build.complete')
    assert events[-1]['command'] == 'build'
    assert len(events) == 1


TEMP = 'aisc-rebuild:' + 'c' * 32


def test_hard_cancel_cleanup_removes_only_operation_tag_and_is_idempotent(tmp_path):
    docker = Docker()
    docker.refs.update({TEMP: NEW, 'other:retained': NEW, 'aisc-rebuild:' + 'd' * 32: NEW})
    docker.containers = [('untouched', OLD, False)]
    before = dict(docker.refs)
    result = cleanup_rebuild_tag(docker, tag=TEMP, data_root=tmp_path)
    assert result['action'] == 'removed'
    del before[TEMP]
    assert docker.refs == before
    assert docker.containers == [('untouched', OLD, False)]
    assert cleanup_rebuild_tag(docker, tag=TEMP, data_root=tmp_path)['action'] == 'absent'
    assert [c for c in docker.calls if c[0] not in ('image',)] == [['rmi', TEMP]]


@pytest.mark.parametrize('tag', [REF, OLD, 'aisc-rebuild:short', 'aisc-rebuild:' + 'C' * 32, 'other/' + TEMP])
def test_cleanup_rejects_non_operation_references_without_docker_calls(tmp_path, tag):
    docker = Docker()
    with pytest.raises(CliError) as error:
        cleanup_rebuild_tag(docker, tag=tag, data_root=tmp_path)
    assert error.value.error_code == 'AISC_ERR_USAGE'
    assert docker.calls == []


@pytest.mark.parametrize('failure', ['rmi', 'inspect', 'still_present'])
def test_cleanup_failure_is_visible_and_never_force_removes(tmp_path, failure):
    class FailingDocker(Docker):
        def run_captured(self, argv, timeout=None):
            if (argv[0] == 'rmi' and failure in ('rmi', 'still_present')) or (argv[0] == 'image' and failure == 'inspect'):
                self.calls.append(argv)
                return ProcessResult(exit_code=0 if failure == 'still_present' else 1, stderr='daemon unavailable')
            return super().run_captured(argv, timeout)
    docker = FailingDocker(); docker.refs[TEMP] = NEW
    before = dict(docker.refs)
    with pytest.raises(CliError): cleanup_rebuild_tag(docker, tag=TEMP, data_root=tmp_path)
    assert docker.refs == before
    assert not any('-f' in c or '--force' in c or c[0] in ('tag', 'rm', 'stop', 'prune') for c in docker.calls)


def test_cleanup_cli_routes_only_exact_tag(tmp_path, monkeypatch, capsys):
    from aisc.cli.main import main
    monkeypatch.setenv('AISC_DATA_ROOT', str(tmp_path))
    with patch('aisc.application.image_rebuild.cleanup_rebuild_tag', return_value={'tag': TEMP, 'action': 'absent'}) as cleanup:
        with pytest.raises(SystemExit) as result:
            main(['maintenance', 'docker-rebuild-cleanup', '--tag', TEMP, '--format', 'json'])
        assert result.value.code == 0
        assert cleanup.call_args.kwargs == {'tag': TEMP}
    assert json.loads(capsys.readouterr().out)['data']['action'] == 'absent'
