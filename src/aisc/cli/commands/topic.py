"""Thin CLI adapter for topic-workshop application operations."""
import json
import sys

from aisc.application.topic import execute
from aisc.domain.models import CliError


def run(args):
    try:
        sources = json.loads(getattr(args, "sources_json", "[]"))
        form = {}
        if getattr(args, "input_json", None) == "-":
            payload = sys.stdin.read(256 * 1024 + 1)
            if len(payload) > 256 * 1024:
                raise ValueError("form too large")
            form = json.loads(payload)
            if not isinstance(form, dict):
                raise ValueError("form must be object")
    except (ValueError, TypeError) as exc:
        raise CliError(message="Invalid topic form JSON or sources-json file-path array",
                       exit_code=2, error_code="AISC_ERR_TOPIC") from exc
    return execute(args.topic_command, args.workspace,
                   id=getattr(args, "id", ""), title=form.get("title", getattr(args, "title", "")),
                   text=form.get("text", getattr(args, "text", "")), sources=form.get("sources", sources),
                   action=form.get("action", getattr(args, "action", "continue")))
