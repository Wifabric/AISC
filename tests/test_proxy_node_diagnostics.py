from types import SimpleNamespace
from unittest.mock import patch

import pytest

from aisc.cli.commands.network import cmd_proxy_nodes
from aisc.domain.models import CliError, ProcessResult


@pytest.mark.parametrize(("probe_exit", "expected"), [
    (10, "AISC_ERR_PROXY_IMAGE"),
    (11, "AISC_ERR_PROXY_CONFIG"),
    (12, "AISC_ERR_PROXY_SOCKET"),
    (0, "AISC_ERR_NETWORK_PROXY_CONTROL"),
])
def test_failed_node_query_reports_the_running_containers_state(tmp_path, probe_exit, expected):
    args = SimpleNamespace(workspace=tmp_path, runtime_id="test", action="list", group="", node="")
    with patch("aisc.adapters.docker_.RealDockerExecutor") as docker, \
         patch("aisc.application.runtime.resolve_running_container", return_value="test-runtime"), \
         patch("aisc.application.data_root.workspace_state_dir", return_value=tmp_path):
        executor = docker.return_value
        executor.run_captured.side_effect = [ProcessResult(exit_code=1), ProcessResult(exit_code=probe_exit)]
        with pytest.raises(CliError) as error:
            cmd_proxy_nodes(args)
        assert error.value.error_code == expected
        assert executor.run_captured.call_args.args[0][:2] == ["exec", "test-runtime"]
