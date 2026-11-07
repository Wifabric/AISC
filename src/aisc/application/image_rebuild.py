"""Selected-image rebuilds: verify, build separately, then publish the tag."""
from dataclasses import asdict
import json
from pathlib import Path
import re
from typing import Any, Optional
import uuid

from aisc.adapters.maintenance_lock import docker_maintenance_lock_at_root
from aisc.application.data_root import shared_root
from aisc.application.docker_lifecycle import _assert_image_operable, _cc_switch_for_rebuild
from aisc.application.image_reference import split_tagged_reference
from aisc.cli.build_progress_parser import BuildProgressParser
from aisc.cli.commands.build import _open_build_log, plan_build, prepare_build_argv
from aisc.domain.models import CliError


def _fail(message: str, code: str = 'AISC_ERR_BUILD_FAILED'):
    raise CliError(message=message, exit_code=6, error_code=code)


def _inspect(executor, ref: str, template: str = '{{.Id}}') -> str:
    result = executor.run_captured(['image', 'inspect', ref, '--format', template], timeout=15.0)
    if result.exit_code == 0 and (result.stdout or '').strip():
        return result.stdout.strip()
    detail = (result.stderr or result.stdout or '').strip()
    if not result.timed_out and ('no such image' in detail.lower() or 'no such object' in detail.lower()):
        return ''
    _fail(f'Cannot inspect image {ref}: {detail[:300]}', 'AISC_ERR_DOCKER_UNAVAILABLE')


def _references(executor, identity: str) -> list[tuple[str, bool]]:
    if not identity:
        return []
    result = executor.run_captured(['ps', '-a', '--filter', f'ancestor={identity}', '--format', '{{.ID}}'], timeout=15.0)
    if result.exit_code != 0:
        _fail('Cannot inspect containers referencing the image')
    ids = result.stdout.split()
    if not ids:
        return []
    # Docker's ancestor filter includes descendant images. Compare exact IDs.
    result = executor.run_captured(['container', 'inspect', *ids, '--format', '{{.Name}}\t{{.Image}}\t{{.State.Running}}'], timeout=30.0)
    if result.exit_code != 0:
        _fail('Container references changed; refresh and retry')
    refs = []
    for line in result.stdout.splitlines():
        fields = line.split('\t')
        if len(fields) != 3 or fields[2] not in ('true', 'false'):
            _fail('Cannot determine container running state')
        if fields[1] == identity:
            refs.append((fields[0].lstrip('/'), fields[2] == 'true'))
    return refs


def rebuild_check(executor, *, tag: str, expected_image_id: Optional[str] = None,
                  data_root: Optional[Path] = None) -> dict[str, Any]:
    try:
        split_tagged_reference(tag)
    except ValueError:
        _fail('Invalid image reference; expected repository:tag', 'AISC_ERR_USAGE')
    identity = _inspect(executor, tag)
    if expected_image_id is not None:
        short = expected_image_id.removeprefix('sha256:')
        matches = identity == expected_image_id or bool(identity and re.fullmatch(r'[0-9a-f]{12,64}', short)
            and identity.removeprefix('sha256:').startswith(short))
        if not matches:
            _fail('Image changed since selection; refresh and confirm again', 'AISC_ERR_IMAGE_REF_CONFLICT')
    if identity:
        _assert_image_operable(executor, image_id=identity, data_root=data_root, allow_in_use=True)
    refs = _references(executor, identity)
    return {'tag': tag, 'image_id': identity, 'exists': bool(identity),
            'containers': [name for name, _ in refs],
            'running_containers': [name for name, running in refs if running]}


def _require_stopped(state):
    if state['running_containers']:
        _fail('Stop these containers before rebuilding: ' + ', '.join(state['running_containers']),
              'AISC_ERR_IMAGE_IN_USE')


def guarded_rebuild(executor, *, root: str, tag: str, expected_image_id: str,
                    no_cache: bool = True, pull: bool = False, emitter=None,
                    data_root: Optional[Path] = None) -> dict[str, Any]:
    lock_root = Path(data_root) if data_root else shared_root()
    temporary = 'aisc-rebuild:' + uuid.uuid4().hex
    warnings = []
    with docker_maintenance_lock_at_root(lock_root):
        state = rebuild_check(executor, tag=tag, expected_image_id=expected_image_id, data_root=lock_root)
        _require_stopped(state)
        old_id = state['image_id']
        cc_switch = _cc_switch_for_rebuild()
        if cc_switch is None:
            warnings.append('cc-switch not pinned; using the Dockerfile ARG fallback')
        plan = plan_build(Path(root), tag=temporary, no_cache=no_cache, pull=pull, dry_run=False, cc_switch=cc_switch)
        log_path = _open_build_log()
        parser = BuildProgressParser()
        if emitter:
            emitter.emit('build.start', {'image_tag': tag, 'log_path': str(log_path) if log_path else None})
            for warning in warnings:
                emitter.emit('build.warning', {'message': warning})
        def chunk(stream, text):
            if log_path:
                try:
                    with open(log_path, 'a', encoding='utf-8', errors='replace') as log:
                        log.write(text)
                except OSError:
                    pass
            if emitter:
                emitter.emit('build.output', {'stream': stream, 'chunk': text})
                for progress in parser.feed(text):
                    emitter.emit('build.progress', asdict(progress))
        try:
            argv = prepare_build_argv(plan, executor, emitter=emitter)
            result = executor.run_streaming_captured(argv, chunk, timeout=1800.0)
            if result.exit_code != 0 or result.timed_out or result.command_not_found:
                _fail('Build failed; original image preserved. See the build log.')
            new_id = _inspect(executor, temporary)
            if not new_id:
                _fail('Build produced no image; original image preserved')
            # Catch tag changes or newly started containers before publication.
            current = rebuild_check(executor, tag=tag, expected_image_id=old_id, data_root=lock_root)
            _require_stopped(current)
            tagged = executor.run_captured(['tag', new_id, tag], timeout=30.0)
            if tagged.exit_code != 0 or _inspect(executor, tag) != new_id:
                _fail('Cannot publish rebuilt image; refresh image state before retrying')
            action = 'not_found' if not old_id else 'unchanged'
            if old_id and old_id != new_id:
                # No force and no container deletion. A changed reference or
                # failed inspection is conservative: retain the old image.
                try:
                    remaining = _references(executor, old_id)
                    tags = json.loads(_inspect(executor, old_id, '{{json .RepoTags}}') or 'null')
                    if remaining:
                        action = 'kept_referenced'
                    elif tags:
                        action = 'kept_tagged'
                    else:
                        removed = executor.run_captured(['rmi', old_id], timeout=30.0)
                        action = 'removed' if removed.exit_code == 0 else 'kept_referenced'
                        if removed.exit_code != 0:
                            warnings.append('Rebuilt image is ready; old image could not be removed')
                except (CliError, ValueError):
                    action = 'kept_referenced'
                    warnings.append('Rebuilt image is ready; old image retained because cleanup could not be verified')
            payload = {'tag': tag, 'old_image_id': old_id, 'new_image_id': new_id,
                       'image_changed': old_id != new_id, 'old_image_action': action,
                       'failed': False, 'warnings': warnings}
            if emitter:
                emitter.emit('build.result', payload)
                for warning in warnings:
                    emitter.emit('build.warning', {'message': warning})
            return payload
        finally:
            # Only our unique temporary tag; never force or remove by image ID.
            try:
                cleanup = executor.run_captured(['rmi', temporary], timeout=30.0)
                detail = (cleanup.stderr or '').lower()
                if cleanup.exit_code != 0 and 'no such image' not in detail:
                    warning = f'Temporary build tag may remain: {temporary}'
                    warnings.append(warning)
                    if emitter:
                        emitter.emit('build.warning', {'message': warning})
            except Exception:
                # A cleanup failure must not hide the original build error.
                warnings.append(f'Temporary build tag may remain: {temporary}')
