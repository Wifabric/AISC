//! Topic-workshop control plane; file policy stays in Python application/topic.
use crate::cli::{run_control_input_target, run_control_target};
use crate::error::WorkbenchError;
use serde_json::{json, Value};
use std::time::Duration;
use tauri::AppHandle;
use tokio_util::sync::CancellationToken;

fn topic_argv(workspace: &str, operation: &str, id: Option<&str>) -> Result<Vec<String>, WorkbenchError> {
    if !["list", "create", "show", "prepare", "check", "activate", "deactivate", "sync"].contains(&operation) {
        return Err(WorkbenchError::usage("unknown topic operation"));
    }
    let mut argv = vec!["topic".into(), operation.into(), "--workspace".into(),
                        workspace.into(), "--format".into(), "json".into()];
    if ["show", "prepare", "check", "activate"].contains(&operation) {
        let value = id.filter(|v| !v.is_empty())
            .ok_or_else(|| WorkbenchError::usage("topic id is required"))?;
        argv.push(format!("--id={value}"));
    }
    if ["create", "prepare"].contains(&operation) {
        argv.extend(["--input-json".into(), "-".into()]);
    }
    Ok(argv)
}

#[tauri::command]
pub async fn topic_call(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
    operation: String,
    id: Option<String>,
    title: Option<String>,
    text: Option<String>,
    sources: Option<Vec<String>>,
    action: Option<String>,
) -> Result<Value, WorkbenchError> {
    let argv = topic_argv(&workspace, &operation, id.as_deref())?;
    let target = crate::target::resolve_target_for(&app, &window).await?;
    let timeout = Duration::from_secs(30);
    let cancel = CancellationToken::new();
    let env = if ["create", "prepare"].contains(&operation.as_str()) {
        // User input travels over stdin, not a shell or process command line.
        let form = json!({"title": title.unwrap_or_default(), "text": text.unwrap_or_default(),
                          "sources": sources.unwrap_or_default(), "action": action.unwrap_or_else(|| "continue".into())});
        run_control_input_target(&target, argv, form.to_string(), timeout, cancel).await?
    } else {
        run_control_target(&target, argv, timeout, cancel).await?
    };
    if let Some(error) = env.errors.first() {
        let mut wb = WorkbenchError::map_aisc(&error.code);
        wb.message = error.message.clone();
        return Err(wb.with_detail(error.message.clone()));
    }
    if env.meta.exit_code != 0 {
        return Err(WorkbenchError::cli_protocol().with_detail("topic command failed without an error"));
    }
    env.data.ok_or_else(WorkbenchError::cli_protocol)
}
