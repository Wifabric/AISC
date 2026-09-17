//! B3 (2.1.12): Docker resource admin panel — `aisc maintenance
//! docker-scan` / `docker-cleanup` / `docker-rebuild` behind typed Tauri
//! commands, extending the O7 cache card into a full "Docker 资源" group
//! (R1 ruling: productize the maintenance surface; the CLI contracts stay
//! installer-facing and untouched). The CLI owns every safety invariant
//! (ownership tiers, containers-before-images, no global prune, re-scan
//! before delete, maintenance lock); this layer is transport + envelope
//! validation only (cache.rs / doctor.rs pattern).
//!
//! Rebuild is LOCAL-ONLY in v1: `--root` must name the bundle root next to
//! the running exe (installed `$INSTDIR\aisc-bundle`; dev
//! `target\debug\aisc-bundle`) — a remote target's root lives on the remote
//! machine and is out of scope until the A-chain update orchestration.

use std::path::PathBuf;
use std::time::Duration;

use serde::{Deserialize, Serialize};
use serde_json::Value;
use tauri::AppHandle;

use crate::cli::run_control_target;
use crate::error::WorkbenchError;
use tokio_util::sync::CancellationToken;

/// Scan/cleanup are quick metadata passes; rebuild is a no-cache build
/// (the CLI itself budgets 1800s of docker build + validation + rmi).
const SCAN_TIMEOUT: Duration = Duration::from_secs(120);
const REBUILD_TIMEOUT: Duration = Duration::from_secs(2400);

/// Pure argv builders (unit-pinned, cache.rs style).
pub fn docker_scan_argv(context: &str) -> Vec<String> {
    vec![
        "maintenance".into(),
        "docker-scan".into(),
        "--context".into(),
        context.into(),
        "--format".into(),
        "json".into(),
    ]
}

pub fn docker_cleanup_argv(context: &str) -> Vec<String> {
    vec![
        "maintenance".into(),
        "docker-cleanup".into(),
        "--context".into(),
        context.into(),
        "--format".into(),
        "json".into(),
    ]
}

pub fn docker_rebuild_argv(root: &str) -> Vec<String> {
    vec![
        "maintenance".into(),
        "docker-rebuild".into(),
        "--root".into(),
        root.into(),
        "--format".into(),
        "json".into(),
    ]
}

/// One classified container/image row. Field names follow the CLI envelope
/// (snake_case projection); everything is optional-tolerant because the
/// scan schema is the CLI's contract, not ours.
#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct DockerResource {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub image: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub tag: String,
    #[serde(default)]
    pub ownership: String,
    #[serde(default)]
    pub reason: String,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct ScanBuckets {
    #[serde(default)]
    pub owned: Vec<DockerResource>,
    #[serde(default)]
    pub legacy_owned: Vec<DockerResource>,
    #[serde(default)]
    pub unverified: Vec<DockerResource>,
}

/// `aisc maintenance docker-scan` payload (aisc.docker-scan/v1).
#[derive(Debug, Clone, Serialize)]
pub struct DockerScanReport {
    #[serde(rename = "dockerAvailable")]
    pub docker_available: bool,
    #[serde(rename = "dockerReason")]
    pub docker_reason: String,
    pub containers: ScanBuckets,
    pub images: ScanBuckets,
    #[serde(rename = "danglingOwned")]
    pub dangling_owned: Vec<DockerResource>,
    pub warnings: Vec<String>,
}

/// One removed/not-found/failed bucket of NAMES (cleanup reports names).
#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct CleanupOutcome {
    #[serde(default)]
    pub removed: Vec<String>,
    #[serde(default)]
    pub not_found: Vec<String>,
    #[serde(default)]
    pub failed: Vec<String>,
}

/// `aisc maintenance docker-cleanup` payload (aisc.docker-cleanup/v1).
#[derive(Debug, Clone, Serialize)]
pub struct DockerCleanupReport {
    pub containers: CleanupOutcome,
    pub images: CleanupOutcome,
    #[serde(rename = "skippedUnverified")]
    pub skipped_unverified: Vec<String>,
    pub warnings: Vec<String>,
}

/// `aisc maintenance docker-rebuild` payload (aisc.docker-rebuild/v1).
/// Build failure PRESERVES the old image and reports failed=true.
#[derive(Debug, Clone, Serialize)]
pub struct DockerRebuildResult {
    pub tag: String,
    #[serde(rename = "newImageId")]
    pub new_image_id: String,
    #[serde(rename = "imageChanged")]
    pub image_changed: bool,
    #[serde(rename = "oldImageAction")]
    pub old_image_action: String,
    pub failed: bool,
    pub warnings: Vec<String>,
    #[serde(rename = "buildLogTail")]
    pub build_log_tail: String,
}

fn envelope_data(env: crate::cli::Envelope) -> Result<Value, WorkbenchError> {
    if let Some(err) = env.errors.first() {
        return Err(WorkbenchError::map_aisc(&err.code).with_detail(err.message.clone()));
    }
    if env.meta.command != "maintenance" {
        return Err(WorkbenchError::cli_protocol().with_detail(format!(
            "unexpected command: {}",
            env.meta.command
        )));
    }
    Ok(env.data.unwrap_or(Value::Null))
}

fn string_vec(value: &Value, key: &str) -> Vec<String> {
    value
        .get(key)
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_default()
}

fn buckets_from(value: &Value) -> ScanBuckets {
    let parse = |v: &Value| -> Vec<DockerResource> {
        v.as_array()
            .map(|a| {
                a.iter()
                    .filter_map(|e| serde_json::from_value(e.clone()).ok())
                    .collect()
            })
            .unwrap_or_default()
    };
    ScanBuckets {
        owned: parse(&value.get("owned").cloned().unwrap_or(Value::Null)),
        legacy_owned: parse(&value.get("legacy_owned").cloned().unwrap_or(Value::Null)),
        unverified: parse(&value.get("unverified").cloned().unwrap_or(Value::Null)),
    }
}

fn outcome_from(value: &Value) -> CleanupOutcome {
    CleanupOutcome {
        removed: string_vec(value, "removed"),
        not_found: string_vec(value, "not_found"),
        failed: string_vec(value, "failed"),
    }
}

/// Bundle root for rebuild: next to the running exe (`aisc-bundle/`), the
/// installed layout the NSIS installer passes as `--root $INSTDIR\aisc-bundle`
/// (installer.nsi:1636-1638) and the dev layout build-cli.ps1 syncs.
pub fn bundle_root_beside_exe() -> Result<PathBuf, WorkbenchError> {
    let exe = std::env::current_exe()
        .map_err(|e| WorkbenchError::usage(format!("current_exe: {e}")))?;
    let root = exe
        .parent()
        .ok_or_else(|| WorkbenchError::usage("exe has no parent dir"))?
        .join("aisc-bundle");
    if root.join("container").join("Dockerfile").is_file() {
        Ok(root)
    } else {
        Err(WorkbenchError::usage(format!(
            "bundle root not found beside exe: {} (expected container/Dockerfile)",
            root.display()
        )))
    }
}

/// Read-only ownership classification for the settings preview.
#[tauri::command]
pub async fn docker_scan(
    app: AppHandle,
    window: tauri::WebviewWindow,
    context: String,
) -> Result<DockerScanReport, WorkbenchError> {
    let target = crate::target::resolve_target_for(&app, &window).await?;
    let env = run_control_target(
        &target,
        docker_scan_argv(&context),
        SCAN_TIMEOUT,
        CancellationToken::new(),
    )
    .await?;
    let data = envelope_data(env)?;
    Ok(DockerScanReport {
        docker_available: data
            .get("docker")
            .and_then(|d| d.get("available"))
            .and_then(Value::as_bool)
            .unwrap_or(false),
        docker_reason: data
            .get("docker")
            .and_then(|d| d.get("reason"))
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_string(),
        containers: buckets_from(&data.get("containers").cloned().unwrap_or(Value::Null)),
        images: buckets_from(&data.get("images").cloned().unwrap_or(Value::Null)),
        dangling_owned: data
            .get("dangling_owned")
            .and_then(Value::as_array)
            .map(|a| {
                a.iter()
                    .filter_map(|e| serde_json::from_value(e.clone()).ok())
                    .collect()
            })
            .unwrap_or_default(),
        warnings: string_vec(&data, "warnings"),
    })
}

/// Remove owned/legacy containers+images (CLI owns the ordering + lock).
#[tauri::command]
pub async fn docker_cleanup(
    app: AppHandle,
    window: tauri::WebviewWindow,
    context: String,
) -> Result<DockerCleanupReport, WorkbenchError> {
    let target = crate::target::resolve_target_for(&app, &window).await?;
    let env = run_control_target(
        &target,
        docker_cleanup_argv(&context),
        Duration::from_secs(300),
        CancellationToken::new(),
    )
    .await?;
    let data = envelope_data(env)?;
    Ok(DockerCleanupReport {
        containers: outcome_from(&data.get("containers").cloned().unwrap_or(Value::Null)),
        images: outcome_from(&data.get("images").cloned().unwrap_or(Value::Null)),
        skipped_unverified: string_vec(&data, "skipped_unverified"),
        warnings: string_vec(&data, "warnings"),
    })
}

/// No-cache rebuild of the workstation image from the LOCAL bundle root.
#[tauri::command]
pub async fn docker_rebuild(app: AppHandle) -> Result<DockerRebuildResult, WorkbenchError> {
    let root = bundle_root_beside_exe()?;
    // The argv carries --root (the bundle beside the exe); the CLI itself is
    // resolved through the canonical pin/auto-select path, exactly like the
    // NSIS installer's silent call resolves its bundled copy.
    let exe = crate::session::resolve_cli(&app).await?;
    let target = crate::cli::CliTarget::Local(exe);
    let env = run_control_target(
        &target,
        docker_rebuild_argv(&root.display().to_string()),
        REBUILD_TIMEOUT,
        CancellationToken::new(),
    )
    .await?;
    let data = envelope_data(env)?;
    let s = |k: &str| {
        data.get(k)
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_string()
    };
    Ok(DockerRebuildResult {
        tag: s("tag"),
        new_image_id: s("new_image_id"),
        image_changed: data
            .get("image_changed")
            .and_then(Value::as_bool)
            .unwrap_or(false),
        old_image_action: s("old_image_action"),
        failed: data.get("failed").and_then(Value::as_bool).unwrap_or(true),
        warnings: string_vec(&data, "warnings"),
        build_log_tail: s("build_log_tail"),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scan_argv_pins_context_and_json() {
        assert_eq!(
            docker_scan_argv("upgrade"),
            vec![
                "maintenance",
                "docker-scan",
                "--context",
                "upgrade",
                "--format",
                "json"
            ]
        );
    }

    #[test]
    fn cleanup_argv_pins_context_and_json() {
        assert_eq!(
            docker_cleanup_argv("uninstall"),
            vec![
                "maintenance",
                "docker-cleanup",
                "--context",
                "uninstall",
                "--format",
                "json"
            ]
        );
    }

    #[test]
    fn rebuild_argv_carries_root() {
        assert_eq!(
            docker_rebuild_argv(r"C:\app\aisc-bundle"),
            vec![
                "maintenance",
                "docker-rebuild",
                "--root",
                r"C:\app\aisc-bundle",
                "--format",
                "json"
            ]
        );
    }

    #[test]
    fn scan_buckets_parse_the_cli_envelope() {
        let data: Value = serde_json::json!({
            "docker": {"available": true, "reason": "ok"},
            "containers": {
                "owned": [
                    {"id": "c1", "name": "aisc-wb-1", "image": "super-claude:latest",
                     "status": "Exited (0)", "ownership": "owned", "reason": "label"}
                ],
                "legacy_owned": [],
                "unverified": [{"id": "c2", "name": "aisc-lookalike", "ownership": "unverified"}]
            },
            "images": {"owned": [{"id": "sha256:aa", "tag": "latest", "name": "super-claude:latest"}],
                       "legacy_owned": [], "unverified": []},
            "dangling_owned": [{"id": "sha256:dd"}],
            "warnings": ["w1"]
        });
        let buckets = buckets_from(&data["containers"]);
        assert_eq!(buckets.owned.len(), 1);
        assert_eq!(buckets.owned[0].name, "aisc-wb-1");
        assert_eq!(buckets.unverified.len(), 1);
        assert_eq!(
            serde_json::from_value::<DockerResource>(data["dangling_owned"][0].clone())
                .unwrap()
                .id,
            "sha256:dd"
        );
        assert_eq!(string_vec(&data, "warnings"), vec!["w1"]);
    }

    #[test]
    fn cleanup_outcome_parses_name_buckets() {
        let data: Value = serde_json::json!({
            "removed": ["aisc-wb-1"], "not_found": [], "failed": ["stubborn"]
        });
        let o = outcome_from(&data);
        assert_eq!(o.removed, vec!["aisc-wb-1"]);
        assert!(o.not_found.is_empty());
        assert_eq!(o.failed, vec!["stubborn"]);
    }

    #[test]
    fn tolerates_null_and_missing_sections() {
        assert!(buckets_from(&Value::Null).owned.is_empty());
        assert!(outcome_from(&Value::Null).removed.is_empty());
        assert!(string_vec(&Value::Null, "warnings").is_empty());
    }
}
