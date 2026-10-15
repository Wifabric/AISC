//! Work Record / Collection IPC (v2.1.15 b6).
//!
//! Thin target-aware pass-through over `aisc work-record`. Collection policy
//! and cascade deletion live in the Python application layer; Rust owns only
//! argv construction, bounded transport, and wire compatibility.

use crate::cli::{Envelope, run_control_target};
use crate::conversation::ConversationSummary;
use crate::error::WorkbenchError;
use crate::runtime::envelope_error;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::time::Duration;
use tauri::AppHandle;
use tokio_util::sync::CancellationToken;

const WORK_RECORD_TIMEOUT: Duration = Duration::from_secs(30);
// Cascade deletion is serial and can remove multiple provider transcripts.
const WORK_RECORD_DELETE_TIMEOUT: Duration = Duration::from_secs(120);

fn base_argv(workspace: &str, command: &str) -> Vec<String> {
    vec![
        "work-record".into(),
        command.into(),
        "--workspace".into(),
        workspace.into(),
    ]
}

fn finish_argv(mut argv: Vec<String>) -> Vec<String> {
    argv.push("--format".into());
    argv.push("json".into());
    argv
}

fn work_record_list_argv(workspace: &str) -> Vec<String> {
    finish_argv(base_argv(workspace, "list"))
}

fn work_record_create_argv(workspace: &str, title: &str) -> Vec<String> {
    let mut argv = base_argv(workspace, "create");
    argv.extend(["--title".into(), title.into()]);
    finish_argv(argv)
}

fn work_record_rename_argv(workspace: &str, id: &str, title: &str) -> Vec<String> {
    let mut argv = base_argv(workspace, "rename");
    argv.extend(["--id".into(), id.into(), "--title".into(), title.into()]);
    finish_argv(argv)
}

fn work_record_activate_argv(workspace: &str, id: &str) -> Vec<String> {
    let mut argv = base_argv(workspace, "activate");
    argv.extend(["--id".into(), id.into()]);
    finish_argv(argv)
}

fn work_record_deactivate_argv(workspace: &str) -> Vec<String> {
    finish_argv(base_argv(workspace, "deactivate"))
}

fn work_record_archive_argv(workspace: &str, id: &str) -> Vec<String> {
    let mut argv = base_argv(workspace, "archive");
    argv.extend(["--id".into(), id.into()]);
    finish_argv(argv)
}

fn work_record_restore_argv(workspace: &str, id: &str) -> Vec<String> {
    let mut argv = base_argv(workspace, "restore");
    argv.extend(["--id".into(), id.into()]);
    finish_argv(argv)
}

fn work_record_add_member_argv(
    workspace: &str,
    id: &str,
    agent: &str,
    conversation_id: &str,
    runtime_id: Option<&String>,
) -> Vec<String> {
    let mut argv = base_argv(workspace, "add");
    argv.extend([
        "--id".into(),
        id.into(),
        "--agent".into(),
        agent.into(),
        "--conversation-id".into(),
        conversation_id.into(),
    ]);
    if let Some(runtime) = runtime_id {
        argv.extend(["--runtime-id".into(), runtime.clone()]);
    }
    finish_argv(argv)
}

fn work_record_remove_member_argv(
    workspace: &str,
    id: &str,
    agent: &str,
    conversation_id: &str,
) -> Vec<String> {
    let mut argv = base_argv(workspace, "remove");
    argv.extend([
        "--id".into(),
        id.into(),
        "--agent".into(),
        agent.into(),
        "--conversation-id".into(),
        conversation_id.into(),
    ]);
    finish_argv(argv)
}

fn push_values(argv: &mut Vec<String>, flag: &str, values: &[String]) {
    argv.push(flag.into());
    argv.extend(values.iter().cloned());
}

fn work_record_reorder_collections_argv(
    workspace: &str,
    collection_ids: &[String],
) -> Vec<String> {
    let mut argv = base_argv(workspace, "reorder-collections");
    push_values(&mut argv, "--ids", collection_ids);
    finish_argv(argv)
}

fn work_record_reorder_members_argv(
    workspace: &str,
    id: &str,
    member_keys: &[String],
) -> Vec<String> {
    let mut argv = base_argv(workspace, "reorder-members");
    argv.extend(["--id".into(), id.into()]);
    push_values(&mut argv, "--member-keys", member_keys);
    finish_argv(argv)
}

fn work_record_reorder_unfiled_argv(
    workspace: &str,
    member_keys: &[String],
) -> Vec<String> {
    let mut argv = base_argv(workspace, "reorder-unfiled");
    push_values(&mut argv, "--member-keys", member_keys);
    finish_argv(argv)
}

fn work_record_move_member_argv(
    workspace: &str,
    from_id: &str,
    to_id: Option<&str>,
    member_key: &str,
    destination_order: Option<&Vec<String>>,
) -> Vec<String> {
    let mut argv = base_argv(workspace, "move");
    argv.extend(["--from-id".into(), from_id.into()]);
    if let Some(to) = to_id {
        argv.extend(["--to-id".into(), to.into()]);
    }
    argv.extend(["--member-key".into(), member_key.into()]);
    if let Some(order) = destination_order {
        push_values(&mut argv, "--destination-order", order);
    }
    finish_argv(argv)
}

fn work_record_delete_argv(workspace: &str, id: &str) -> Vec<String> {
    let mut argv = base_argv(workspace, "delete");
    argv.extend(["--id".into(), id.into()]);
    finish_argv(argv)
}

fn work_record_reconcile_argv(workspace: &str) -> Vec<String> {
    finish_argv(base_argv(workspace, "reconcile"))
}

// -- wire types (TS mirrors live in workbench/src/types/index.ts) --

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRecordMember {
    #[serde(default)]
    pub member_key: String,
    #[serde(default)]
    pub agent: String,
    #[serde(default)]
    pub conversation_id: String,
    #[serde(default)]
    pub runtime_id: Option<String>,
    #[serde(default)]
    pub source: String,
    #[serde(default)]
    pub added_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRecordCollection {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub created_at: Option<String>,
    #[serde(default)]
    pub updated_at: Option<String>,
    #[serde(default)]
    pub archived_at: Option<String>,
    #[serde(default)]
    pub members: Vec<WorkRecordMember>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRecordListResult {
    #[serde(default)]
    pub schema_version: String,
    #[serde(default)]
    pub active_collection_id: Option<String>,
    #[serde(default)]
    pub collections: Vec<WorkRecordCollection>,
    #[serde(default)]
    pub unfiled: Vec<ConversationSummary>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRecordCollectionResult {
    #[serde(default)]
    pub collection: Option<WorkRecordCollection>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRecordActiveResult {
    #[serde(default)]
    pub active_collection_id: Option<String>,
    #[serde(default)]
    pub previous_collection_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRecordMemberResult {
    #[serde(default)]
    pub member: Option<WorkRecordMember>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRecordRemoveResult {
    #[serde(default)]
    pub removed: bool,
    #[serde(default)]
    pub member_key: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRecordCollectionsResult {
    #[serde(default)]
    pub collections: Vec<WorkRecordCollection>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRecordUnfiledResult {
    #[serde(default)]
    pub unfiled: Vec<ConversationSummary>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRecordMoveResult {
    #[serde(default)]
    pub member: Option<WorkRecordMember>,
    #[serde(default)]
    pub member_key: Option<String>,
    #[serde(default)]
    pub collection_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRecordDeleteFailure {
    #[serde(default)]
    pub member_key: String,
    #[serde(default)]
    pub agent: String,
    #[serde(default)]
    pub conversation_id: Option<String>,
    #[serde(default)]
    pub stage: String,
    #[serde(default)]
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRecordDeleteResult {
    #[serde(default)]
    pub deleted: bool,
    #[serde(default)]
    pub collection_id: String,
    #[serde(default)]
    pub terminated_session_ids: Vec<String>,
    #[serde(default)]
    pub deleted_members: Vec<WorkRecordMember>,
    #[serde(default)]
    pub failed_members: Vec<WorkRecordDeleteFailure>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRecordReconcileResult {
    #[serde(default)]
    pub schema_version: String,
    #[serde(default)]
    pub added: Vec<String>,
    #[serde(default)]
    pub active_collection_id: Option<String>,
    #[serde(default)]
    pub collections: Vec<WorkRecordCollection>,
    #[serde(default)]
    pub observed_provider_keys: Vec<String>,
}

async fn run_work_record<T>(
    workspace: &str,
    app: &AppHandle,
    window: &tauri::WebviewWindow,
    argv: Vec<String>,
    timeout: Duration,
    operation: &'static str,
) -> Result<T, WorkbenchError>
where
    T: serde::de::DeserializeOwned,
{
    let target = crate::target::resolve_target_for_workspace(app, window, workspace).await?;
    let env: Envelope =
        run_control_target(&target, argv, timeout, CancellationToken::new()).await?;
    if let Some(e) = envelope_error(&env) {
        return Err(e);
    }
    let data = env.data.unwrap_or(Value::Null);
    serde_json::from_value::<T>(data)
        .map_err(|e| WorkbenchError::cli_protocol().with_detail(format!("{operation} parse: {e}")))
}

#[tauri::command]
pub async fn work_record_list(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
) -> Result<WorkRecordListResult, WorkbenchError> {
    let argv = work_record_list_argv(&workspace);
    run_work_record(&workspace,&app, &window, argv, WORK_RECORD_TIMEOUT, "work record list").await
}

#[tauri::command]
pub async fn work_record_create(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
    title: String,
) -> Result<WorkRecordCollectionResult, WorkbenchError> {
    let argv = work_record_create_argv(&workspace, &title);
    run_work_record(
        &workspace,
        &app,
        &window,
        argv,
        WORK_RECORD_TIMEOUT,
        "work record create",
    )
    .await
}

#[tauri::command]
pub async fn work_record_rename(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
    id: String,
    title: String,
) -> Result<WorkRecordCollectionResult, WorkbenchError> {
    let argv = work_record_rename_argv(&workspace, &id, &title);
    run_work_record(
        &workspace,
        &app,
        &window,
        argv,
        WORK_RECORD_TIMEOUT,
        "work record rename",
    )
    .await
}

#[tauri::command]
pub async fn work_record_activate(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
    id: String,
) -> Result<WorkRecordActiveResult, WorkbenchError> {
    let argv = work_record_activate_argv(&workspace, &id);
    run_work_record(
        &workspace,
        &app,
        &window,
        argv,
        WORK_RECORD_TIMEOUT,
        "work record activate",
    )
    .await
}

#[tauri::command]
pub async fn work_record_deactivate(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
) -> Result<WorkRecordActiveResult, WorkbenchError> {
    let argv = work_record_deactivate_argv(&workspace);
    run_work_record(
        &workspace,
        &app,
        &window,
        argv,
        WORK_RECORD_TIMEOUT,
        "work record deactivate",
    )
    .await
}

#[tauri::command]
pub async fn work_record_archive(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
    id: String,
) -> Result<WorkRecordCollectionResult, WorkbenchError> {
    let argv = work_record_archive_argv(&workspace, &id);
    run_work_record(
        &workspace,
        &app,
        &window,
        argv,
        WORK_RECORD_TIMEOUT,
        "work record archive",
    )
    .await
}

#[tauri::command]
pub async fn work_record_restore(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
    id: String,
) -> Result<WorkRecordCollectionResult, WorkbenchError> {
    let argv = work_record_restore_argv(&workspace, &id);
    run_work_record(
        &workspace,
        &app,
        &window,
        argv,
        WORK_RECORD_TIMEOUT,
        "work record restore",
    )
    .await
}

#[tauri::command]
pub async fn work_record_add_member(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
    id: String,
    agent: String,
    conversation_id: String,
    runtime_id: Option<String>,
) -> Result<WorkRecordMemberResult, WorkbenchError> {
    let argv = work_record_add_member_argv(
        &workspace,
        &id,
        &agent,
        &conversation_id,
        runtime_id.as_ref(),
    );
    run_work_record(&workspace,&app, &window, argv, WORK_RECORD_TIMEOUT, "work record add").await
}

#[tauri::command]
pub async fn work_record_remove_member(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
    id: String,
    agent: String,
    conversation_id: String,
) -> Result<WorkRecordRemoveResult, WorkbenchError> {
    let argv = work_record_remove_member_argv(&workspace, &id, &agent, &conversation_id);
    run_work_record(
        &workspace,
        &app,
        &window,
        argv,
        WORK_RECORD_TIMEOUT,
        "work record remove",
    )
    .await
}

#[tauri::command]
pub async fn work_record_reorder_collections(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
    ids: Vec<String>,
) -> Result<WorkRecordCollectionsResult, WorkbenchError> {
    let argv = work_record_reorder_collections_argv(&workspace, &ids);
    run_work_record(&workspace, &app, &window, argv, WORK_RECORD_TIMEOUT, "work record reorder collections").await
}

#[tauri::command]
pub async fn work_record_reorder_members(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
    id: String,
    member_keys: Vec<String>,
) -> Result<WorkRecordCollectionResult, WorkbenchError> {
    let argv = work_record_reorder_members_argv(&workspace, &id, &member_keys);
    run_work_record(&workspace, &app, &window, argv, WORK_RECORD_TIMEOUT, "work record reorder members").await
}

#[tauri::command]
pub async fn work_record_reorder_unfiled(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
    member_keys: Vec<String>,
) -> Result<WorkRecordUnfiledResult, WorkbenchError> {
    let argv = work_record_reorder_unfiled_argv(&workspace, &member_keys);
    run_work_record(&workspace, &app, &window, argv, WORK_RECORD_TIMEOUT, "work record reorder unfiled").await
}

#[tauri::command]
pub async fn work_record_move_member(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
    from_id: String,
    to_id: Option<String>,
    member_key: String,
    destination_order: Option<Vec<String>>,
) -> Result<WorkRecordMoveResult, WorkbenchError> {
    let argv = work_record_move_member_argv(
        &workspace, &from_id, to_id.as_deref(), &member_key, destination_order.as_ref(),
    );
    run_work_record(&workspace, &app, &window, argv, WORK_RECORD_TIMEOUT, "work record move member").await
}

#[tauri::command]
pub async fn work_record_delete(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
    id: String,
) -> Result<WorkRecordDeleteResult, WorkbenchError> {
    let argv = work_record_delete_argv(&workspace, &id);
    run_work_record(
        &workspace,
        &app,
        &window,
        argv,
        WORK_RECORD_DELETE_TIMEOUT,
        "work record delete",
    )
    .await
}

#[tauri::command]
pub async fn work_record_reconcile(
    app: AppHandle,
    window: tauri::WebviewWindow,
    workspace: String,
) -> Result<WorkRecordReconcileResult, WorkbenchError> {
    let argv = work_record_reconcile_argv(&workspace);
    run_work_record(
        &workspace,
        &app,
        &window,
        argv,
        WORK_RECORD_TIMEOUT,
        "work record reconcile",
    )
    .await
}
// v2.1.15 b6 Work Record IPC tests — written first for red TDD.

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn list_argv_shape() {
        let argv = work_record_list_argv("C:/ws");
        assert_eq!(argv[0], "work-record");
        assert_eq!(argv[1], "list");
        assert_eq!(
            argv[argv.iter().position(|x| x == "--workspace").unwrap() + 1],
            "C:/ws"
        );
        assert_eq!(argv.last().map(String::as_str), Some("json"));
    }

    #[test]
    fn crud_argv_shapes() {
        let argv = work_record_create_argv("C:/ws", "Feature");
        assert_eq!(argv[1], "create");
        assert_eq!(
            argv[argv.iter().position(|x| x == "--title").unwrap() + 1],
            "Feature"
        );
        let argv = work_record_rename_argv("C:/ws", "id-1", "Renamed");
        assert_eq!(argv[1], "rename");
        assert_eq!(
            argv[argv.iter().position(|x| x == "--id").unwrap() + 1],
            "id-1"
        );
        assert_eq!(
            argv[argv.iter().position(|x| x == "--title").unwrap() + 1],
            "Renamed"
        );
        for (argv, command) in [
            (work_record_activate_argv("C:/ws", "id-1"), "activate"),
            (work_record_archive_argv("C:/ws", "id-1"), "archive"),
            (work_record_restore_argv("C:/ws", "id-1"), "restore"),
            (work_record_delete_argv("C:/ws", "id-1"), "delete"),
            (work_record_reconcile_argv("C:/ws"), "reconcile"),
        ] {
            assert_eq!(argv[1], command);
            assert!(argv.contains(&"--workspace".to_string()));
            assert_eq!(argv.last().map(String::as_str), Some("json"));
        }
        assert!(
            work_record_delete_argv("C:/ws", "id-1")
                .iter()
                .all(|arg| arg != "--force" && arg != "--yes")
        );
    }

    #[test]
    fn member_argv_shapes() {
        let runtime = Some("runtime-1".to_string());
        let add = work_record_add_member_argv(
            "C:/ws",
            "id-1",
            "codex",
            "01a04ca9-d3f6-7021-b9e7-50d48d818c65",
            runtime.as_ref(),
        );
        assert_eq!(add[1], "add");
        for (flag, value) in [
            ("--id", "id-1"),
            ("--agent", "codex"),
            ("--conversation-id", "01a04ca9-d3f6-7021-b9e7-50d48d818c65"),
            ("--runtime-id", "runtime-1"),
        ] {
            assert_eq!(add[add.iter().position(|x| x == flag).unwrap() + 1], value);
        }
        let remove = work_record_remove_member_argv(
            "C:/ws",
            "id-1",
            "claude",
            "c8931e67-2321-492d-8557-4158e3ef2ee7",
        );
        assert_eq!(remove[1], "remove");
        assert!(!remove.contains(&"--force".to_string()));
    }

    #[test]
    fn order_and_move_argv_shapes() {
        let collections = work_record_reorder_collections_argv(
            "C:/ws", &["id-2".into(), "id-1".into()],
        );
        assert_eq!(collections[1], "reorder-collections");
        assert!(collections.contains(&"--ids".into()));
        assert!(collections.contains(&"id-2".into()));
        let members = work_record_reorder_members_argv(
            "C:/ws", "id-1", &["codex:b".into(), "codex:a".into()],
        );
        assert_eq!(members[1], "reorder-members");
        assert!(members.contains(&"--member-keys".into()));
        let unfiled = work_record_reorder_unfiled_argv(
            "C:/ws", &["codex:b".into(), "codex:a".into()],
        );
        assert_eq!(unfiled[1], "reorder-unfiled");
        let moved = work_record_move_member_argv(
            "C:/ws", "from-1", Some("to-1"), "codex:a",
            Some(&vec!["codex:a".into(), "codex:b".into()]),
        );
        assert_eq!(moved[1], "move");
        for flag in ["--from-id", "--to-id", "--member-key", "--destination-order"] {
            assert!(moved.contains(&flag.to_string()));
        }
    }

    #[test]
    fn wire_structs_tolerate_missing_optional_fields() {
        let list: WorkRecordListResult = serde_json::from_value(serde_json::json!({})).unwrap();
        assert!(list.collections.is_empty());
        assert!(list.unfiled.is_empty());
        assert!(list.active_collection_id.is_none());
        let delete: WorkRecordDeleteResult = serde_json::from_value(serde_json::json!({
            "failed_members": [{"member_key":"codex:id","stage":"delete","reason":"locked"}]
        }))
        .unwrap();
        assert!(!delete.deleted); // missing bool tolerates to serde bool default
        assert_eq!(delete.failed_members.len(), 1);
        assert_eq!(delete.failed_members[0].stage, "delete");
    }
}
