import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tomllib
from unittest import mock
import urllib.error

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'container/lib'))
import github_mcp_auth as auth
import default_mcp as default


@pytest.fixture
def layout(tmp_path):
    config, project, codex = [tmp_path/n for n in ('cc', 'project', 'codex')]
    for p in (config, project, codex): p.mkdir()
    with sqlite3.connect(config/'cc-switch.db') as db:
        db.execute('CREATE TABLE mcp_servers (id TEXT PRIMARY KEY,name TEXT,server_config TEXT,description TEXT,homepage TEXT,docs TEXT,tags TEXT,enabled_claude INTEGER,enabled_codex INTEGER)')
    default.synchronize(config_dir=config, project_dir=project, codex_config_dir=codex)
    return dict(config_dir=config, project_dir=project, codex_dir=codex)


def run(layout, op='github-auth-status', **request):
    return auth.handle(op, request, **layout)


def save(layout, agents, token='qa-only-not-a-real-token', **extra):
    return run(layout, 'github-auth-save', agents=agents, token=token, revision=run(layout)['revision'], **extra)


def snapshot(layout):
    with sqlite3.connect(layout['config_dir']/'cc-switch.db') as db:
        row = db.execute('SELECT server_config FROM mcp_servers WHERE id="github"').fetchone()[0]
    return (row, (layout['project_dir']/'.mcp.json').read_bytes(), (layout['codex_dir']/'config.toml').read_bytes())


def test_selected_engine_only_and_no_secret_in_results(layout):
    before = snapshot(layout)
    result = save(layout, ['claude'])
    after = snapshot(layout)
    assert before[2] == after[2]
    assert result['engines']['claude']['configured']
    assert not result['engines']['codex']['configured']
    assert 'qa-only' not in json.dumps(result)
    second = save(layout, ['codex'], token='qa-codex-only-value')
    assert snapshot(layout)[1] == after[1]
    assert all(e['configured'] and e['connection']=='not_verified' for e in second['engines'].values())
    document = tomllib.loads(snapshot(layout)[2].decode())
    assert document['mcp_servers']['github']['http_headers']['Authorization'] == 'Bearer qa-codex-only-value'
    assert 'bearer_token_env_var' not in document['mcp_servers']['github']


def test_restart_sync_preserves_auth_and_unrelated_configuration(layout):
    path = layout['codex_dir']/'config.toml'
    path.write_text('model="keep"\n'+path.read_text()+'startup_timeout_sec=44\n[features]\nkeep=true\n')
    claude = layout['project_dir']/'.mcp.json'
    doc=json.loads(claude.read_text());doc['mcpServers']['other']={'command':'echo'}
    doc['mcpServers']['github']['headers']={'X-Custom':'keep'}
    claude.write_text(json.dumps(doc))
    save(layout, ['claude','codex'])
    default.synchronize(config_dir=layout['config_dir'],project_dir=layout['project_dir'],codex_config_dir=layout['codex_dir'])
    codex = tomllib.loads(path.read_text())
    assert codex['model']=='keep' and codex['features']['keep']
    assert codex['mcp_servers']['github']['startup_timeout_sec']==44
    assert json.loads(claude.read_text())['mcpServers']['other']=={'command':'echo'}
    assert json.loads(claude.read_text())['mcpServers']['github']['headers']['X-Custom']=='keep'
    assert all(e['configured'] for e in run(layout)['engines'].values())


def test_conflict_and_custom_server_do_not_write(layout):
    old=run(layout)['revision']; save(layout,['claude'])
    before=snapshot(layout)
    with pytest.raises(auth.AuthError,match='CONFLICT'):
        run(layout,'github-auth-save',revision=old,agents=['codex'],token='qa-unused-token')
    assert snapshot(layout)==before
    with sqlite3.connect(layout['config_dir']/'cc-switch.db') as db:
        db.execute('UPDATE mcp_servers SET server_config=?', (json.dumps({'url':'https://custom.example/mcp'}),))
    before=snapshot(layout)
    with pytest.raises(auth.AuthError,match='CUSTOM_CONFIG'): save(layout,['claude'])
    assert snapshot(layout)==before


def test_failed_second_file_write_rolls_back_first_file_and_database(layout):
    before=snapshot(layout)
    with mock.patch.object(default,'_sync_codex',side_effect=OSError('qa-secret-must-not-leak')):
        with pytest.raises(auth.AuthError) as error: save(layout,['claude','codex'])
    assert error.value.code=='CONFIG_FAILED'
    assert 'qa-secret' not in str(error.value)
    assert snapshot(layout)==before


def test_corrupt_config_and_disabled_engine_are_preserved(layout):
    path=layout['codex_dir']/'config.toml';path.write_text('invalid = [')
    before=snapshot(layout)
    with pytest.raises(auth.AuthError): save(layout,['claude'])
    assert snapshot(layout)==before
    path.write_text('')
    with sqlite3.connect(layout['config_dir']/'cc-switch.db') as db:
        db.execute('UPDATE mcp_servers SET enabled_claude=0')
    before=snapshot(layout)
    with pytest.raises(auth.AuthError,match='DISABLED'): save(layout,['claude'])
    assert snapshot(layout)==before


def test_explicit_connection_check_is_read_only_redacted_and_rejects_redirects(layout):
    save(layout,['claude']); before=snapshot(layout)
    opener=mock.Mock();opener.open.side_effect=urllib.error.HTTPError(default.OFFICIAL_URL,401,'qa-secret',{},None)
    with mock.patch.object(auth.urllib.request,'build_opener',return_value=opener):
        state=run(layout,'github-auth-check',revision=run(layout)['revision'],agents=['claude','codex'])
    assert state['engines']['claude']['connection']=='auth_failed'
    assert state['engines']['codex']['connection']=='missing_config'
    assert 'qa-secret' not in json.dumps(state)
    assert snapshot(layout)==before
    assert auth._NoRedirect().redirect_request(None,None,302,'',{},'https://other.example') is None


def test_host_bridge_keeps_token_on_stdin_and_returns_only_status(layout):
    from aisc.application import extensions
    calls=[]
    executor=mock.Mock()
    def execute(argv,**kwargs):
        calls.append((argv,kwargs));return mock.Mock(exit_code=0,stderr='',stdout=json.dumps({'schema':extensions.PROTOCOL,'ok':True,'data':{'revision':'hash'}}))
    executor.run_captured.side_effect=execute
    with mock.patch.object(extensions,'resolve_running_container',return_value='qa'):
        result=extensions.extensions_github_auth('qa','github-auth-save',str(layout['project_dir']),{'token':'qa-secret'},executor)
    assert result=={'revision':'hash'}
    assert 'qa-secret' not in ' '.join(calls[0][0])
    assert json.loads(calls[0][1]['input_text'])=={'token':'qa-secret'}


def test_connection_result_is_discarded_when_configuration_changes_during_check(layout):
    save(layout, ['claude'])
    def changed(*args):
        path=layout['project_dir']/'.mcp.json'
        path.write_text(path.read_text()+'\n')
        return 'connected'
    with mock.patch.object(auth, '_check', side_effect=changed):
        with pytest.raises(auth.AuthError, match='CONFLICT'):
            run(layout,'github-auth-check',revision=run(layout)['revision'],agents=['claude'])


def test_nested_codex_headers_preserve_unrelated_values(layout):
    path=layout['codex_dir']/'config.toml'
    path.write_text(path.read_text()+'[mcp_servers.github.http_headers]\nX-Test="keep"\n[mcp_servers.other]\nurl="https://other.example"\n')
    save(layout,['codex'])
    doc=tomllib.loads(path.read_text())
    assert doc['mcp_servers']['github']['http_headers']['X-Test']=='keep'
    assert doc['mcp_servers']['other']['url']=='https://other.example'
