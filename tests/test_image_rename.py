"""Renaming preserves image identity, other tags, and conflict boundaries."""
from unittest.mock import patch
import pytest
from aisc.application import docker_lifecycle as dl
from aisc.domain.models import CliError, ProcessResult

IMAGE = 'sha256:' + 'a' * 64
OTHER = 'sha256:' + 'b' * 64

class Docker:
    def __init__(self):
        self.refs = {'super-claude:old': IMAGE, 'super-claude:keep': IMAGE}
        self.calls = []
        self.remove_error = False
    def run_captured(self, argv, timeout=None):
        self.calls.append(argv)
        code, out, err = 0, '', ''
        if argv[:2] == ['image', 'inspect']:
            out = self.refs.get(argv[2], IMAGE if argv[2] == IMAGE else '')
            if not out: code, err = 1, 'Error: No such image: ' + argv[2]
        elif argv[0] == 'tag': self.refs[argv[2]] = self.refs.get(argv[1], argv[1])
        elif argv[0] == 'rmi':
            if self.remove_error: code, err = 1, 'image is in use'
            else: self.refs.pop(argv[1])
        return ProcessResult(exit_code=code, stdout=out, stderr=err,
                             command_not_found=False, timed_out=False)

def rename(docker, tmp_path, repository='registry.example:5000/team/image', tag='new'):
    with patch.object(dl, '_assert_image_operable', return_value={'id': IMAGE}):
        return dl.image_management_tag(docker, image_id=IMAGE, repository=repository,
            tag=tag, old_ref='super-claude:old', data_root=tmp_path)

def test_rename_only_removes_selected_tag(tmp_path):
    docker = Docker()
    result = rename(docker, tmp_path)
    assert docker.refs == {'super-claude:keep': IMAGE, 'registry.example:5000/team/image:new': IMAGE}
    assert result['warnings'] == []
    assert ['rmi', 'super-claude:old'] in docker.calls
    assert not any('-f' in args for args in docker.calls)

def test_conflict_and_stale_source_never_mutate(tmp_path):
    for stale in (False, True):
        docker = Docker()
        docker.refs['super-claude:old' if stale else 'registry.example:5000/team/image:new'] = OTHER
        before = dict(docker.refs)
        with pytest.raises(CliError): rename(docker, tmp_path)
        assert docker.refs == before
        assert not any(c[0] in ('tag', 'rmi') for c in docker.calls)

def test_same_name_is_noop(tmp_path):
    docker = Docker()
    rename(docker, tmp_path, 'super-claude', 'old')
    assert not any(c[0] in ('tag', 'rmi') for c in docker.calls)

def test_partial_rename_keeps_both_tags_and_warns(tmp_path):
    docker = Docker(); docker.remove_error = True
    result = rename(docker, tmp_path)
    assert docker.refs['super-claude:old'] == IMAGE
    assert docker.refs['registry.example:5000/team/image:new'] == IMAGE
    assert result['warnings']

def test_equivalent_docker_hub_name_never_removes_the_new_tag(tmp_path):
    docker = Docker()
    docker.refs['docker.io/library/super-claude:old'] = IMAGE
    rename(docker, tmp_path, 'docker.io/library/super-claude', 'old')
    assert not any(c[0] in ('tag', 'rmi') for c in docker.calls)

def test_unavailable_daemon_is_not_treated_as_missing_target(tmp_path):
    docker = Docker()
    original = docker.run_captured
    def inspect_fails(argv, timeout=None):
        if argv[:3] == ['image', 'inspect', 'registry.example:5000/team/image:new']:
            return ProcessResult(exit_code=1, stdout='', stderr='Cannot connect to daemon', command_not_found=False, timed_out=False)
        return original(argv, timeout)
    docker.run_captured = inspect_fails
    with pytest.raises(CliError): rename(docker, tmp_path)
    assert not any(c[0] in ('tag', 'rmi') for c in docker.calls)

def test_ownership_accepts_full_identity_from_short_docker_listing(tmp_path):
    short = '123456789abc'
    rows = [{'id': short, 'repository': 'super-claude', 'tag': 'old', 'ref': 'super-claude:old'}]
    with patch.object(dl, '_image_universe', return_value=rows), \
         patch.object(dl, '_filtered_image_ids', return_value=[short]):
        assert dl._assert_image_operable(Docker(), image_id='sha256:' + short + 'f' * 52,
            data_root=tmp_path, allow_in_use=True)['id'] == short
        for invalid in ('abc', 'f' * 52 + short):
            with pytest.raises(CliError):
                dl._assert_image_operable(Docker(), image_id=invalid,
                    data_root=tmp_path, allow_in_use=True)

@pytest.mark.parametrize('repository,tag', [('team/Upper','x'), ('host:bad/team/image','x'),
    ('repo','bad:tag'), ('repo','-bad'), ('repo','x'*129), ('repo@sha256:abc','x')])
def test_invalid_references_rejected_before_docker(tmp_path, repository, tag):
    docker = Docker()
    with pytest.raises(CliError): rename(docker, tmp_path, repository, tag)
    assert docker.calls == []
