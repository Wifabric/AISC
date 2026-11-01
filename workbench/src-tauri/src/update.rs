//! A7 (0.1.0, D-8 ruling 自研): Workbench self-update — the light path.
//!
//! check → download (sha256-verified, progress events, nothing lands on
//! failure) → the UI collects the user's confirmation → the NSIS installer
//! opens normally through the Windows shell, after Explorer selects it.
//! Only successful launches allow the app to exit so files can be replaced.
//! The installer already chains
//! the full upgrade semantics (PATH takeover + maintenance scan/cleanup/
//! rebuild), so this module deliberately does NOT re-implement any of it
//! — that was the whole argument against tauri-plugin-updater (D-8).
//!
//! Channel (D-8, 2026-09-19): preview-first — releases are published from
//! develop as prereleases (`vX.Y.Z-preview.N`); finals only on explicit
//! request. The picker ranks by (semver, final > preview, preview number).
//! The payload is the Workbench NSIS ONLY (`AISC-Workbench-*-setup.exe`);
//! the CLI rides inside it (pip is the other CLI channel).
//! Transport: reqwest + system proxy (WinINET probe, subscription.rs
//! pattern — same-stack reuse, no new deps).

use std::io::Read as _;
use std::path::{Path, PathBuf};
use std::time::Duration;

use serde::{Deserialize, Serialize};
use tauri::AppHandle;
use tauri::Emitter;

use crate::error::WorkbenchError;
use crate::update_health::{record_attempt, UpdateOutcome, UpdateRoute, UpdateTransport};

const RELEASES_URL: &str = "https://api.github.com/repos/Wifabric/AISC/releases?per_page=30";
const RELEASES_ATOM_URL: &str = "https://github.com/Wifabric/AISC/releases.atom";
const UPDATE_ERROR_NETWORK: &str = "app.update/network";

fn update_error(message: impl Into<String>) -> WorkbenchError {
    WorkbenchError::usage(crate::error::redact(&message.into()))
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateInfo {
    pub current: String,
    pub latest: Option<String>,
    pub update_available: bool,
    pub setup_url: Option<String>,
    pub sha256_url: Option<String>,
    pub release_url: Option<String>,
    /// b15: the Workbench GUI and bundled CLI have independent version lines.
    /// One installer upgrades both, but each current/latest pair is reported.
    pub cli_current: Option<String>,
    pub cli_latest: Option<String>,
    pub cli_update_available: bool,
    pub note: String,
}

/// `0.1.0-dev` == `0.1.0.dev0` (the dash form is the Workbench app-version
/// convention; the four-piece contract only demands normalized equality).
pub fn normalize_version(v: &str) -> String {
    if let Some(stem) = v.strip_suffix("-dev") {
        format!("{stem}.dev0")
    } else {
        v.to_string()
    }
}

fn client_builder(proxy: Option<&str>) -> Result<reqwest::Client, WorkbenchError> {
    let mut builder = reqwest::Client::builder()
        .user_agent("aisc-workbench-selfupdate")
        .connect_timeout(Duration::from_secs(10))
        .read_timeout(Duration::from_secs(60));
    if let Some(proxy) = proxy {
        let proxy = reqwest::Proxy::all(proxy)
            .map_err(|_| update_error("app.update/proxy: invalid system proxy configuration"))?;
        builder = builder.proxy(proxy);
    } else {
        builder = builder.no_proxy();
    }
    builder
        .build()
        .map_err(|e| update_error(format!("http client: {e}")))
}

fn client() -> Result<reqwest::Client, WorkbenchError> {
    client_builder(crate::subscription::system_http_proxy().as_deref())
}

/// Network strategies in priority order. A stale/clash proxy must not make
/// GitHub permanently unreachable; a direct connection must not be skipped in
/// environments where the proxy is required. Try both, with bounded retries.
fn update_clients() -> Result<Vec<(reqwest::Client, UpdateTransport)>, WorkbenchError> {
    match crate::subscription::system_http_proxy() {
        Some(proxy) => Ok(vec![
            (client_builder(Some(&proxy))?, UpdateTransport::SystemProxy),
            (client_builder(None)?, UpdateTransport::Direct),
        ]),
        None => Ok(vec![(client_builder(None)?, UpdateTransport::Direct)]),
    }
}

fn err_chain(error: &dyn std::error::Error) -> String {
    let mut out = error.to_string();
    let mut source = error.source();
    while let Some(next) = source {
        out.push_str(&format!(": {next}"));
        source = next.source();
    }
    out
}

fn github_url_candidates(url: &str) -> Vec<String> {
    let mut candidates = vec![url.to_string()];
    if url.starts_with("https://api.github.com/") {
        // ghfast.top returns 403 for API paths; gh-proxy.com has been
        // verified to proxy GitHub's JSON API without rewriting the body.
        candidates.push(format!("https://gh-proxy.com/{url}"));
    } else if url.starts_with("https://github.com/")
        || url.starts_with("https://raw.githubusercontent.com/")
    {
        candidates.push(format!("https://ghfast.top/{url}"));
        candidates.push(format!("https://gh-proxy.com/{url}"));
    }
    candidates
}

async fn get_with_fallback(
    url: &str,
    headers: reqwest::header::HeaderMap,
) -> Result<reqwest::Response, WorkbenchError> {
    let clients = update_clients()?;
    let candidates = github_url_candidates(url);
    get_candidates(&clients, &candidates, headers, record_attempt).await
}

async fn get_candidates(
    clients: &[(reqwest::Client, UpdateTransport)],
    candidates: &[String],
    headers: reqwest::header::HeaderMap,
    mut observe: impl FnMut(&str, UpdateRoute, UpdateTransport, UpdateOutcome, Duration),
) -> Result<reqwest::Response, WorkbenchError> {
    let mut errors = Vec::new();
    let mut last_response: Option<reqwest::Response> = None;
    // Attempt-major order matters: on the first pass a reachable mirror gets
    // a chance before a flaky direct URL is retried. HTTP failures are not
    // returned immediately, so a direct 403 can still reach the API mirror.
    for attempt in 0..3 {
        for (index, candidate) in candidates.iter().enumerate() {
            let route = if index == 0 {
                UpdateRoute::Direct
            } else {
                UpdateRoute::Mirror
            };
            for (client, transport) in clients {
                let start = std::time::Instant::now();
                let response = client
                    .get(candidate.as_str())
                    .headers(headers.clone())
                    .send()
                    .await;
                let outcome = match &response {
                    Ok(response) if response.status().is_success() => {
                        UpdateOutcome::HeadersReceived
                    }
                    Ok(response) => UpdateOutcome::HttpError(response.status().as_u16()),
                    Err(error) if error.is_timeout() => UpdateOutcome::Timeout,
                    Err(_) => UpdateOutcome::NetworkError,
                };
                observe(candidate, route, *transport, outcome, start.elapsed());
                match response {
                    Ok(response) if response.status().is_success() => return Ok(response),
                    Ok(response) => {
                        let status = response.status();
                        errors.push(format!(
                            "attempt {} {}: HTTP {}",
                            attempt + 1,
                            candidate,
                            status
                        ));
                        last_response = Some(response);
                    }
                    Err(e) => errors.push(format!(
                        "attempt {} {}: {}",
                        attempt + 1,
                        candidate,
                        err_chain(&e)
                    )),
                }
            }
        }
        if attempt < 2 {
            tokio::time::sleep(Duration::from_millis(300)).await;
        }
    }
    if let Some(response) = last_response {
        return Ok(response);
    }
    Err(update_error(format!(
        "{UPDATE_ERROR_NETWORK}: {}",
        errors.join(" | ")
    )))
}

fn gh_headers() -> reqwest::header::HeaderMap {
    let mut h = reqwest::header::HeaderMap::new();
    h.insert("Accept", "application/vnd.github+json".parse().unwrap());
    if let Ok(token) = std::env::var("AISC_GH_API_TOKEN") {
        if !token.is_empty() {
            if let Ok(v) = format!("Bearer {token}").parse() {
                h.insert("Authorization", v);
            }
        }
    }
    h
}

/// Current Workbench version (tauri package info), normalized for compare.
fn current_version(app: &AppHandle) -> String {
    normalize_version(&app.package_info().version.to_string())
}

/// Pure: given release JSON entries, pick the newest final tag and its
/// setup/.sha256 asset URLs. (Unit-tested without network.)
/// D-8.8: the preview channel IS the default release channel — tags are
/// `vX.Y.Z` (final) or `vX.Y.Z-preview.N`. Ordering key: (semver, final
/// beats preview, higher preview number).
pub fn parse_tag(tag: &str) -> Option<((u64, u64, u64), bool, u64)> {
    let body = tag.strip_prefix('v').unwrap_or(tag);
    let (base, preview) = match body.split_once("-preview") {
        Some((b, n)) => (
            b,
            Some(if n.is_empty() {
                "1"
            } else {
                n.trim_start_matches('.')
            }),
        ),
        None => (body, None),
    };
    let mut it = base.split('.');
    let major: u64 = it.next()?.parse().ok()?;
    let minor: u64 = it.next()?.parse().ok()?;
    let patch: u64 = it.next()?.parse().ok()?;
    if it.next().is_some() {
        return None; // 4+ segments = not a version we understand
    }
    let preview_n: u64 = match preview {
        Some(n) => n.parse().ok()?,
        None => 0,
    };
    Some(((major, minor, patch), preview.is_none(), preview_n))
}

fn version_key(tag: &str) -> ((u64, u64, u64), bool, u64) {
    parse_tag(tag).unwrap_or(((0, 0, 0), false, 0))
}

pub fn pick_latest(releases: &serde_json::Value) -> Option<(String, String, String, String)> {
    let arr = releases.as_array()?;
    let mut best_tag: Option<&str> = None;
    let mut best_key: Option<((u64, u64, u64), bool, u64)> = None;
    for rel in arr {
        let tag = rel.get("tag_name").and_then(|t| t.as_str()).unwrap_or("");
        let key = version_key(tag);
        if key.0 == (0, 0, 0) {
            continue; // unparsable tag = channel noise, not a failure
        }
        if best_key.as_ref().is_none_or(|bk| key > *bk) {
            best_key = Some(key);
            best_tag = Some(tag);
        }
    }
    let tag = best_tag?;
    let rel = arr
        .iter()
        .find(|r| r.get("tag_name").and_then(|t| t.as_str()) == Some(tag))?;
    let mut setup = None;
    let mut sha = None;
    for asset in rel
        .get("assets")
        .and_then(|a| a.as_array())
        .unwrap_or(&vec![])
    {
        let name = asset.get("name").and_then(|n| n.as_str()).unwrap_or("");
        let url = asset
            .get("browser_download_url")
            .and_then(|u| u.as_str())
            .unwrap_or("");
        // D-8: the Workbench NSIS is the self-update payload. The CLI Inno
        // installer (AISC-<ver>-windows-x86_64-setup.exe in old releases,
        // aisc-cli-<ver>-installer.exe since) must never match — CLI
        // updates ride pip / the Workbench installer's bundled sidecar.
        if name.starts_with("AISC-Workbench-") && name.ends_with("-setup.exe") {
            setup = Some(url.to_string());
        } else if name.starts_with("AISC-Workbench-") && name.ends_with("-setup.exe.sha256") {
            sha = Some(url.to_string());
        }
    }
    let release_url = rel
        .get("html_url")
        .and_then(|u| u.as_str())
        .unwrap_or("")
        .to_string();
    let tag = tag.strip_prefix('v').unwrap_or(tag).to_string();
    Some((tag, setup?, sha?, release_url))
}

fn release_download_urls(tag: &str) -> (String, String, String) {
    let tagged = if tag.starts_with('v') {
        tag.to_string()
    } else {
        format!("v{tag}")
    };
    let version = tagged.strip_prefix('v').unwrap_or(&tagged);
    let base = format!(
        "https://github.com/Wifabric/AISC/releases/download/{tagged}/AISC-Workbench-{version}-setup"
    );
    (
        format!("{base}.exe"),
        format!("{base}.exe.sha256"),
        format!("https://github.com/Wifabric/AISC/releases/tag/{tagged}"),
    )
}

pub fn pick_latest_atom(xml: &str) -> Option<(String, String, String, String)> {
    let mut best_tag: Option<&str> = None;
    let mut best_key: Option<((u64, u64, u64), bool, u64)> = None;
    for entry in xml.split("<entry>").skip(1) {
        let entry = entry.split("</entry>").next().unwrap_or_default();
        let Some(id) = entry
            .split("<id>")
            .nth(1)
            .and_then(|rest| rest.split("</id>").next())
        else {
            continue;
        };
        let Some(tag) = id.rsplit('/').next() else {
            continue;
        };
        let key = version_key(tag);
        if key.0 == (0, 0, 0) {
            continue;
        }
        if best_key.as_ref().is_none_or(|current| key > *current) {
            best_key = Some(key);
            best_tag = Some(tag);
        }
    }
    let tag = best_tag?;
    let latest = tag.strip_prefix('v').unwrap_or(tag).to_string();
    let (setup, sha, page) = release_download_urls(tag);
    Some((latest, setup, sha, page))
}

fn version_gt(a: &str, b: &str) -> bool {
    version_key(a) > version_key(b)
}

fn cli_version_gt(a: &str, b: &str) -> bool {
    fn key(value: &str) -> ((u64, u64, u64), u8, u64) {
        let value = value.trim().trim_start_matches('v');
        let parts: Vec<&str> = value.split('.').collect();
        let major = parts.first().and_then(|v| v.parse().ok()).unwrap_or(0);
        let minor = parts.get(1).and_then(|v| v.parse().ok()).unwrap_or(0);
        let patch = parts.get(2).and_then(|v| v.parse().ok()).unwrap_or(0);
        let suffix = if parts.len() > 3 {
            Some(parts[3..].join("."))
        } else {
            None
        };
        let (kind, pre) = match suffix.as_deref() {
            Some(suffix) if suffix.starts_with("dev") => (1u8, suffix[3..].parse().unwrap_or(0)),
            _ => (0u8, 0),
        };
        ((major, minor, patch), kind, pre)
    }
    key(a) > key(b)
}

fn combined_update_available(
    gui_update: bool,
    cli_current: Option<&str>,
    cli_latest: Option<&str>,
) -> bool {
    let cli_update = match (cli_current, cli_latest) {
        (Some(current), Some(latest)) => cli_version_gt(latest, current),
        _ => false,
    };
    gui_update || cli_update
}

fn cli_version_from_envelope(stdout: &[u8]) -> Option<String> {
    let value: serde_json::Value = serde_json::from_slice(stdout).ok()?;
    let version = value
        .get("data")?
        .get("cli_version")
        .or_else(|| value.get("data")?.get("version"))?
        .as_str()?
        .trim()
        .to_string();
    Some(version).filter(|version| !version.is_empty())
}

fn local_cli_version(app: &AppHandle) -> Option<String> {
    let exe = std::env::current_exe().ok()?;
    let dir = exe.parent()?;
    let name = if cfg!(windows) { "aisc.exe" } else { "aisc" };
    let sidecar = dir.join(name);
    if !sidecar.is_file() {
        return None;
    }
    let mut command = std::process::Command::new(&sidecar);
    command.args(["version", "--format", "json"]);
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000);
    }
    let output = command.output().ok()?;
    if !output.status.success() {
        return None;
    }
    cli_version_from_envelope(&output.stdout)
}

async fn bundled_cli_version(latest_tag: &str) -> Result<String, WorkbenchError> {
    let url =
        format!("https://raw.githubusercontent.com/Wifabric/AISC/v{latest_tag}/src/aisc/VERSION");
    let response = get_with_fallback(&url, gh_headers()).await?;
    if !response.status().is_success() {
        return Err(update_error(format!(
            "{UPDATE_ERROR_NETWORK}: bundled CLI HTTP {}",
            response.status()
        )));
    }
    let text = response
        .text()
        .await
        .map_err(|e| update_error(format!("{UPDATE_ERROR_NETWORK}: bundled CLI body: {e}")))?;
    let version = text.trim().to_string();
    if version.is_empty() {
        return Err(update_error(format!(
            "{UPDATE_ERROR_NETWORK}: bundled CLI VERSION is empty"
        )));
    }
    Ok(version)
}

/// Check for a newer FINAL release. Network failures degrade to a
/// note-carrying UpdateInfo (a check must never crash the menu), except
/// when a hard error object is needed by tests.
#[tauri::command]
pub async fn app_check_update(app: AppHandle) -> Result<UpdateInfo, WorkbenchError> {
    let current = current_version(&app);
    let cli_current = local_cli_version(&app);

    // GitHub's unauthenticated API has a 60/hour limit and field users have
    // already hit HTTP 403. The Atom feed is public, current, and not subject
    // to that core quota; use it first and keep the API as fallback only.
    let atom_candidate = match get_with_fallback(RELEASES_ATOM_URL, gh_headers()).await {
        Ok(response) if response.status().is_success() => response
            .text()
            .await
            .ok()
            .and_then(|xml| pick_latest_atom(&xml)),
        _ => None,
    };

    let releases = if atom_candidate.is_some() {
        None
    } else {
        match get_with_fallback(RELEASES_URL, gh_headers()).await {
            Ok(response) if response.status().is_success() => match response.text().await {
                Ok(text) => match serde_json::from_str::<serde_json::Value>(&text) {
                    Ok(body) => Some(body),
                    Err(e) => {
                        return Ok(UpdateInfo {
                            current,
                            latest: None,
                            update_available: false,
                            setup_url: None,
                            sha256_url: None,
                            release_url: None,
                            cli_current,
                            cli_latest: None,
                            cli_update_available: false,
                            note: format!("{UPDATE_ERROR_NETWORK}: releases body: {e}"),
                        })
                    }
                },
                Err(e) => {
                    return Ok(UpdateInfo {
                        current,
                        latest: None,
                        update_available: false,
                        setup_url: None,
                        sha256_url: None,
                        release_url: None,
                        cli_current,
                        cli_latest: None,
                        cli_update_available: false,
                        note: format!("{UPDATE_ERROR_NETWORK}: releases body: {e}"),
                    })
                }
            },
            Ok(response) => {
                return Ok(UpdateInfo {
                    current,
                    latest: None,
                    update_available: false,
                    setup_url: None,
                    sha256_url: None,
                    release_url: None,
                    cli_current,
                    cli_latest: None,
                    cli_update_available: false,
                    note: format!(
                        "{UPDATE_ERROR_NETWORK}: releases HTTP {}",
                        response.status()
                    ),
                })
            }
            Err(e) => {
                return Ok(UpdateInfo {
                    current,
                    latest: None,
                    update_available: false,
                    setup_url: None,
                    sha256_url: None,
                    release_url: None,
                    cli_current,
                    cli_latest: None,
                    cli_update_available: false,
                    note: format!(
                        "check failed (network strategies exhausted): {}",
                        e.technical_detail.unwrap_or_default()
                    ),
                })
            }
        }
    };

    let picked = if let Some(candidate) = atom_candidate {
        Some(candidate)
    } else {
        let Some(body) = releases else {
            unreachable!("releases is Some on the only fallthrough path");
        };
        pick_latest(&body)
    };
    let Some((latest, setup, sha, page)) = picked else {
        return Ok(UpdateInfo {
            current,
            latest: None,
            update_available: false,
            setup_url: None,
            sha256_url: None,
            release_url: None,
            cli_current,
            cli_latest: None,
            cli_update_available: false,
            note: "no published Workbench release with setup assets available".into(),
        });
    };

    let cli_latest = match bundled_cli_version(&latest).await {
        Ok(version) => Some(version),
        Err(e) => {
            let version = e.technical_detail.unwrap_or_default();
            return Ok(UpdateInfo {
                current: current.clone(),
                latest: Some(latest.clone()),
                // The target installer is still available. CLI target version
                // is unknown, but a GUI update can proceed safely.
                update_available: version_gt(&latest, &current),
                setup_url: Some(setup),
                sha256_url: Some(sha),
                release_url: Some(page),
                cli_current,
                cli_latest: None,
                cli_update_available: false,
                note: format!("bundled CLI check failed: {version}"),
            });
        }
    };
    let cli_update_available =
        combined_update_available(false, cli_current.as_deref(), cli_latest.as_deref());
    let update_available = combined_update_available(
        version_gt(&latest, &current),
        cli_current.as_deref(),
        cli_latest.as_deref(),
    );
    Ok(UpdateInfo {
        current,
        latest: Some(latest),
        update_available,
        setup_url: Some(setup),
        sha256_url: Some(sha),
        release_url: Some(page),
        cli_current,
        cli_latest,
        cli_update_available,
        note: String::new(),
    })
}
fn update_staging_dir() -> PathBuf {
    std::env::temp_dir().join("aisc-workbench-update")
}

/// b1: the staged installer is named after the TARGET version (it used to
/// carry the current version, which misled debugging after upgrades). Only
/// filename-safe chars survive the filter; a degenerate input falls back to
/// the current version.
fn staging_path(app: &AppHandle, target: &str) -> PathBuf {
    let dir = update_staging_dir();
    let _ = std::fs::create_dir_all(&dir);
    let safe: String = target
        .trim_start_matches('v')
        .chars()
        .filter(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '-'))
        .collect();
    let name = if safe.is_empty() {
        current_version(app)
    } else {
        safe
    };
    dir.join(format!("workbench-setup-{name}.exe"))
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DownloadResult {
    pub path: String,
    pub sha256: String,
    pub size: u64,
}


/// Receipt for an installer that this app downloaded and SHA256-verified.
/// Cleanup happens only after a later app version starts; a cancelled or failed
/// installer leaves both files intact for retry/diagnosis.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct StagedUpdateReceipt {
    schema_version: u32,
    target: String,
    installer: String,
    sha256: String,
    size: u64,
}

fn installer_receipt_path(installer: &Path) -> PathBuf {
    let name = installer
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or_default();
    installer.with_file_name(format!("{name}.receipt.json"))
}

fn valid_update_version(value: &str) -> bool {
    !value.is_empty()
        && value
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '.' | '-'))
}

fn write_staged_update_receipt(
    installer: &Path,
    target_version: &str,
    result: &DownloadResult,
) -> std::io::Result<()> {
    let target = target_version.trim().trim_start_matches('v');
    let installer_name = installer
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or_default();
    let expected_name = format!("workbench-setup-{target}.exe");
    if !valid_update_version(target) || installer_name != expected_name {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "update receipt target/installer mismatch",
        ));
    }
    if result.sha256.len() != 64 || !result.sha256.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "update receipt digest invalid",
        ));
    }
    let receipt = StagedUpdateReceipt {
        schema_version: 1,
        target: target.to_string(),
        installer: installer_name.to_string(),
        sha256: result.sha256.to_ascii_lowercase(),
        size: result.size,
    };
    let bytes = serde_json::to_vec_pretty(&receipt)?;
    crate::storage::atomic_replace(&installer_receipt_path(installer), &bytes)
}

fn sha256_file_sync(path: &Path) -> std::io::Result<String> {
    let mut file = std::fs::File::open(path)?;
    let mut hasher = sha2_compatible::Hasher::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = file.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
    }
    Ok(hasher.hex())
}

/// Return installer paths deleted after a verified successful upgrade.
/// Receipt paths are deliberately constrained to this staging directory.
fn cleanup_completed_update_staging(dir: &Path, current_version: &str) -> Vec<PathBuf> {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return Vec::new();
    };
    let mut deleted = Vec::new();
    for entry in entries.flatten() {
        let receipt_path = entry.path();
        if !receipt_path
            .file_name()
            .and_then(|value| value.to_str())
            .is_some_and(|value| value.ends_with(".exe.receipt.json"))
        {
            continue;
        }
        let Ok(bytes) = std::fs::read(&receipt_path) else {
            continue;
        };
        let Ok(receipt) = serde_json::from_slice::<StagedUpdateReceipt>(&bytes) else {
            continue;
        };
        let target = receipt.target.trim().trim_start_matches('v');
        if receipt.schema_version != 1
            || !valid_update_version(target)
            || receipt.installer != format!("workbench-setup-{target}.exe")
            || !receipt.installer.chars().all(|ch| {
                ch.is_ascii_alphanumeric() || matches!(ch, '.' | '-' | '_')
            })
            || !version_gt(current_version, target)
        {
            continue;
        }
        let installer = dir.join(&receipt.installer);
        if !installer.is_file() {
            let _ = std::fs::remove_file(&receipt_path);
            continue;
        }
        let Ok(metadata) = installer.metadata() else {
            continue;
        };
        if metadata.len() != receipt.size
            || sha256_file_sync(&installer)
                .map(|digest| digest != receipt.sha256)
                .unwrap_or(true)
        {
            continue;
        }
        if std::fs::remove_file(&installer).is_ok() {
            let _ = std::fs::remove_file(&receipt_path);
            deleted.push(installer);
        }
    }
    deleted
}

pub(crate) fn cleanup_completed_updates(app: &AppHandle) {
    let current = current_version(app);
    let deleted = cleanup_completed_update_staging(&update_staging_dir(), &current);
    if !deleted.is_empty() {
        crate::logging::append_event(
            "info",
            "app",
            "update_staging_cleanup",
            None,
            serde_json::json!({
                "currentVersion": current,
                "deletedCount": deleted.len(),
            }),
        );
    }
}

/// Owns just one request's temporary file. Never remove the shared destination:
/// a concurrent request may already have published a verified installer there.
struct UpdateStaging {
    path: PathBuf,
    file: Option<tokio::fs::File>,
}

impl UpdateStaging {
    async fn create(
        dest: &std::path::Path,
        request_id: Option<&str>,
    ) -> Result<Self, WorkbenchError> {
        let request: String = request_id
            .unwrap_or("download")
            .chars()
            .filter(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_'))
            .take(64)
            .collect();
        // UUID also isolates omitted, reused, empty, or sanitized-identical IDs.
        let path = dest.with_extension(format!("{request}.{}.part", uuid::Uuid::new_v4()));
        let file = tokio::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)
            .await
            .map_err(|e| update_error(format!("staging create: {e}")))?;
        Ok(Self {
            path,
            file: Some(file),
        })
    }
}

impl Drop for UpdateStaging {
    fn drop(&mut self) {
        // Close before unlinking on Windows, including early stream/write errors.
        drop(self.file.take());
        let _ = std::fs::remove_file(&self.path);
    }
}

async fn stage_update_response(
    mut resp: reqwest::Response,
    dest: &std::path::Path,
    expected: &str,
    request_id: Option<&str>,
    mut progress: impl FnMut(serde_json::Value),
) -> Result<DownloadResult, WorkbenchError> {
    use tokio::io::AsyncWriteExt;
    let total = resp.content_length().unwrap_or(0);
    let mut staging = UpdateStaging::create(dest, request_id).await?;
    let mut hasher = sha2_compatible::Hasher::new();
    let mut downloaded = 0_u64;
    while let Some(chunk) = resp
        .chunk()
        .await
        .map_err(|e| update_error(format!("{UPDATE_ERROR_NETWORK}: {e}")))?
    {
        hasher.update(&chunk);
        staging
            .file
            .as_mut()
            .expect("staging file open")
            .write_all(&chunk)
            .await
            .map_err(|e| update_error(format!("staging write: {e}")))?;
        downloaded += chunk.len() as u64;
        progress(
            serde_json::json!({"downloaded": downloaded, "total": total, "requestId": request_id}),
        );
    }
    staging
        .file
        .as_mut()
        .expect("staging file open")
        .flush()
        .await
        .map_err(|e| update_error(format!("staging flush: {e}")))?;
    drop(staging.file.take());
    let actual = hasher.hex();
    if actual != expected {
        return Err(update_error(format!(
            "sha256 mismatch: expected {expected:.16}..., got {actual:.16}... — download discarded"
        )));
    }
    tokio::fs::rename(&staging.path, dest)
        .await
        .map_err(|e| update_error(format!("staging rename: {e}")))?;
    Ok(DownloadResult {
        path: dest.display().to_string(),
        sha256: actual,
        size: downloaded,
    })
}

/// Stream the setup.exe to a staging file, verify against the .sha256
/// sidecar, emit `update://progress` {downloaded,total,requestId} along the way.
/// On failure only this request's incomplete file is removed; other verified
/// installers and concurrent downloads are left intact.
#[tauri::command]
pub async fn app_download_update(
    app: AppHandle,
    setup_url: String,
    sha256_url: String,
    target_version: String,
    request_id: Option<String>,
) -> Result<DownloadResult, WorkbenchError> {
    let sidecar = get_with_fallback(&sha256_url, gh_headers()).await?;
    if !sidecar.status().is_success() {
        return Err(update_error(format!(
            "{UPDATE_ERROR_NETWORK}: sha256 sidecar HTTP {}",
            sidecar.status()
        )));
    }
    let sidecar_text = sidecar
        .text()
        .await
        .map_err(|e| update_error(format!("{UPDATE_ERROR_NETWORK}: {e}")))?;
    let expected = sidecar_text
        .split_whitespace()
        .next()
        .unwrap_or("")
        .to_ascii_lowercase();
    if expected.len() != 64 || !expected.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err(update_error("sha256 sidecar malformed"));
    }

    let resp = get_with_fallback(&setup_url, gh_headers()).await?;
    if !resp.status().is_success() {
        return Err(update_error(format!(
            "{UPDATE_ERROR_NETWORK}: setup download HTTP {}",
            resp.status()
        )));
    }
    let dest = staging_path(&app, &target_version);
    let result = stage_update_response(
        resp,
        &dest,
        &expected,
        request_id.as_deref(),
        |progress| {
            let _ = app.emit("update://progress", progress);
        },
    )
    .await?;
    if let Err(e) = write_staged_update_receipt(&dest, &target_version, &result) {
        return Err(update_error(format!("update receipt write failed: {e}")));
    }
    Ok(result)
}

/// Injectable launch sequence. Errors retain the app, including shell/UAC
/// cancellation. A successful launch does not mean installation has completed.
fn run_explicit_install(
    windows: bool,
    setup_path: &str,
    check_file: impl FnOnce(&str) -> Result<(), String>,
    explorer_select: impl FnOnce(&str) -> Result<(), String>,
    shell_open: impl FnOnce(&str) -> Result<(), String>,
    exit: impl FnOnce(),
) -> Result<(), String> {
    if !windows {
        return Err("app.update/manual-install: this platform requires manual installation".into());
    }
    check_file(setup_path)?;
    explorer_select(setup_path)?;
    shell_open(setup_path)?;
    exit();
    Ok(())
}

#[cfg(windows)]
fn windows_shell_open_with(
    file: &std::ffi::OsStr,
    parameters: Option<&std::ffi::OsStr>,
    execute: impl FnOnce(&mut windows_sys::Win32::UI::Shell::SHELLEXECUTEINFOW) -> (i32, u32),
) -> std::io::Result<()> {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::UI::Shell::{SEE_MASK_FLAG_NO_UI, SEE_MASK_NOASYNC, SHELLEXECUTEINFOW};
    use windows_sys::Win32::UI::WindowsAndMessaging::SW_SHOWNORMAL;

    let wide = |value: &std::ffi::OsStr| -> std::io::Result<Vec<u16>> {
        let mut value: Vec<_> = value.encode_wide().collect();
        if value.contains(&0) {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                "shell path contains NUL",
            ));
        }
        value.push(0);
        Ok(value)
    };
    let verb = wide(std::ffi::OsStr::new("open"))?;
    let file = wide(file)?;
    let parameters = parameters.map(wide).transpose()?;
    // All unused handles/pointers may be null. Buffers stay alive for the
    // synchronous shell call; NOASYNC waits for DDE/launch acknowledgement,
    // not for the installer to finish. NO_UI suppresses shell error dialogs,
    // while leaving normal installer UI and UAC prompts enabled.
    let mut info: SHELLEXECUTEINFOW = unsafe { std::mem::zeroed() };
    info.cbSize = std::mem::size_of::<SHELLEXECUTEINFOW>() as u32;
    info.fMask = SEE_MASK_NOASYNC | SEE_MASK_FLAG_NO_UI;
    info.lpVerb = verb.as_ptr();
    info.lpFile = file.as_ptr();
    info.lpParameters = parameters.as_ref().map_or(std::ptr::null(), |p| p.as_ptr());
    info.nShow = SW_SHOWNORMAL;
    let (success, last_error) = execute(&mut info);
    // ShellExecuteEx returns BOOL (not ShellExecuteW's >32 HINSTANCE).
    // In particular ERROR_CANCELLED (1223) is failure, never a reason to exit.
    if success == 0 {
        Err(std::io::Error::from_raw_os_error(last_error as i32))
    } else {
        Ok(())
    }
}

#[cfg(windows)]
fn windows_shell_open(
    file: &std::ffi::OsStr,
    parameters: Option<&std::ffi::OsStr>,
) -> std::io::Result<()> {
    windows_shell_open_with(file, parameters, |info| {
        // GetLastError must be captured immediately on failure. No process
        // handle is requested, so the shell owns the launched process.
        let success = unsafe { windows_sys::Win32::UI::Shell::ShellExecuteExW(info) };
        let error = if success == 0 {
            unsafe { windows_sys::Win32::Foundation::GetLastError() }
        } else {
            0
        };
        (success, error)
    })
}

#[cfg(windows)]
fn explorer_select_parameters(setup: &std::ffi::OsStr) -> std::ffi::OsString {
    let mut parameters = std::ffi::OsString::from("/select,\"");
    parameters.push(setup);
    parameters.push("\"");
    parameters
}

/// The UI has already collected confirmation. Open Explorer, launch the
/// installer exactly like a double-click (no arguments), then exit.
#[tauri::command]
pub async fn app_install_update(app: AppHandle, setup_path: String) -> Result<(), WorkbenchError> {
    tauri::async_runtime::spawn_blocking(move || {
        run_explicit_install(
            cfg!(windows),
            &setup_path,
            |path| {
                if std::path::Path::new(path).is_file() {
                    Ok(())
                } else {
                    Err(format!("staged setup not found: {path}"))
                }
            },
            |path| {
                #[cfg(windows)]
                {
                    let parameters = explorer_select_parameters(std::ffi::OsStr::new(path));
                    windows_shell_open(std::ffi::OsStr::new("explorer.exe"), Some(&parameters))
                        .map_err(|e| format!("Explorer select failed: {e}"))
                }
                #[cfg(not(windows))]
                {
                    let _ = path;
                    Err("manual installation required".into())
                }
            },
            |path| {
                #[cfg(windows)]
                {
                    windows_shell_open(std::ffi::OsStr::new(path), None)
                        .map_err(|e| format!("installer shell open failed: {e}"))
                }
                #[cfg(not(windows))]
                {
                    let _ = path;
                    Err("manual installation required".into())
                }
            },
            || app.exit(0),
        )
        .map_err(update_error)
    })
    .await
    .map_err(|e| update_error(format!("installer launch task: {e}")))?
}

// ---------------------------------------------------------------------------
// Tiny sha256 facade (self-contained: the digest matches FIPS 180-4; this
// only spares the module the trait-import dance at each use site).
// ---------------------------------------------------------------------------
mod sha2_compatible {
    pub struct Hasher(sha2::Sha256);

    impl Hasher {
        pub fn new() -> Self {
            Self(<sha2::Sha256 as sha2::Digest>::new())
        }
        pub fn update(&mut self, data: &[u8]) {
            sha2::Digest::update(&mut self.0, data);
        }
        pub fn hex(self) -> String {
            use sha2::Digest;
            let out = sha2::Digest::finalize(self.0);
            out.iter().map(|b| format!("{b:02x}")).collect()
        }
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn invalid_configured_proxy_is_rejected_instead_of_mislabeled() {
        assert!(super::client_builder(Some("http://[")).is_err());
    }

    // b12 (T1 user report): the 30s TOTAL timeout killed every 292MB in-app
    // download ~33MB in. Real-stream proof that the connect/read split keeps
    // a large asset alive past 30s to completion. #[ignore] so CI never
    // pulls 292MB; run explicitly with:
    //   cargo test --lib -- --ignored selfupdate_large_stream_survives
    #[test]
    #[ignore = "downloads the real 292MB release asset (~1 min)"]
    #[cfg(windows)]
    fn selfupdate_large_stream_survives() {
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .expect("tokio rt");
        rt.block_on(async {
            let client = client().expect("client");
            let url = "https://github.com/Wifabric/AISC/releases/download/v2.1.14-preview.1/AISC-Workbench-2.1.14-preview.1-setup.exe";
            let started = std::time::Instant::now();
            let mut resp = client.get(url).send().await.expect("send");
            assert!(resp.status().is_success(), "HTTP {}", resp.status());
            let mut total: u64 = 0;
            while let Some(chunk) = resp.chunk().await.expect("chunk") {
                total += chunk.len() as u64;
            }
            let elapsed = started.elapsed().as_secs_f64();
            // The OLD client() died at exactly 30.0s; require we ran past
            // that mark AND completed the full asset.
            assert!(elapsed > 31.0, "finished in {elapsed}s - old timeout may still be set");
            assert_eq!(total, 292_726_047, "expected full 292726047 bytes, got {total}");
            println!("b12 proof: {total} bytes in {elapsed:.1}s (old cap: 30s)");
        });
    }

    use super::*;
    use serde_json::json;

    #[test]
    fn explicit_install_has_no_silent_command_or_non_windows_execution() {
        let source = include_str!("update.rs");
        let install = source
            .split("pub async fn app_install_update")
            .nth(1)
            .unwrap()
            .split("// ---------------------------------------------------------------------------")
            .next()
            .unwrap();
        assert!(
            !install.contains("\"/S\""),
            "installer must show its normal UI"
        );
        assert!(
            !install.contains("\"/R\""),
            "no automatic relaunch argument"
        );
        assert!(
            !install.contains("\"-S\""),
            "non-Windows installation is manual"
        );
        assert!(
            !install.contains("Command::new(\"cmd\")"),
            "use the Windows Shell API"
        );
    }

    #[test]
    fn update_receipt_cleanup_only_after_verified_successful_upgrade() {
        let dir = tempfile::tempdir().unwrap();
        let body = b"verified installer";
        let installer = dir.path().join("workbench-setup-2.1.17-preview.1.exe");
        std::fs::write(&installer, body).unwrap();
        write_staged_update_receipt(
            &installer,
            "2.1.17-preview.1",
            &DownloadResult {
                path: installer.to_string_lossy().to_string(),
                sha256: body_hash(body),
                size: body.len() as u64,
            },
        )
        .unwrap();
        let receipt = installer_receipt_path(&installer);

        assert_eq!(
            cleanup_completed_update_staging(dir.path(), "2.1.17-preview.1"),
            Vec::<PathBuf>::new()
        );
        assert!(installer.is_file());
        assert!(receipt.is_file());

        assert_eq!(
            cleanup_completed_update_staging(dir.path(), "2.1.18"),
            vec![installer.clone()]
        );
        assert!(!installer.exists());
        assert!(!receipt.exists());
    }

    #[test]
    fn update_receipt_cleanup_preserves_changed_bytes_and_unrelated_files() {
        let dir = tempfile::tempdir().unwrap();
        let installer = dir.path().join("workbench-setup-2.1.17-preview.1.exe");
        std::fs::write(&installer, b"verified").unwrap();
        write_staged_update_receipt(
            &installer,
            "2.1.17-preview.1",
            &DownloadResult {
                path: installer.to_string_lossy().to_string(),
                sha256: body_hash(b"verified"),
                size: 8,
            },
        )
        .unwrap();
        std::fs::write(&installer, b"changed").unwrap();
        let unrelated = dir.path().join("user-download.exe");
        std::fs::write(&unrelated, b"keep").unwrap();

        assert_eq!(
            cleanup_completed_update_staging(dir.path(), "2.1.18"),
            Vec::<PathBuf>::new()
        );
        assert!(installer.is_file());
        assert!(unrelated.is_file());
        assert!(installer_receipt_path(&installer).is_file());
    }

    #[test]
    fn update_receipt_cleanup_rejects_paths_outside_owned_staging_directory() {
        let dir = tempfile::tempdir().unwrap();
        let outside = tempfile::tempdir().unwrap();
        let victim = outside.path().join("victim.exe");
        std::fs::write(&victim, b"keep").unwrap();
        let receipt = dir.path().join("workbench-setup-2.1.17-preview.1.exe.receipt.json");
        std::fs::write(
            &receipt,
            serde_json::to_vec(&StagedUpdateReceipt {
                schema_version: 1,
                target: "2.1.17-preview.1".into(),
                installer: format!("..\\..\\{}", victim.file_name().unwrap().to_string_lossy()),
                sha256: body_hash(b"keep"),
                size: 4,
            })
            .unwrap(),
        )
        .unwrap();

        assert_eq!(
            cleanup_completed_update_staging(dir.path(), "2.1.18"),
            Vec::<PathBuf>::new()
        );
        assert!(victim.is_file());
        assert!(receipt.is_file());
    }

    #[test]
    fn explicit_install_checks_file_then_launches_explorer_installer_and_exit() {
        let calls = std::cell::RefCell::new(Vec::new());
        let result = run_explicit_install(
            true,
            r"C:\Users\用户\Downloads\安装 程序.exe",
            |_| {
                calls.borrow_mut().push("exists");
                Ok(())
            },
            |_| {
                calls.borrow_mut().push("explorer");
                Ok(())
            },
            |_| {
                calls.borrow_mut().push("installer");
                Ok(())
            },
            || calls.borrow_mut().push("exit"),
        );
        assert!(result.is_ok());
        assert_eq!(*calls.borrow(), ["exists", "explorer", "installer", "exit"]);
    }

    #[test]
    fn explicit_install_stops_when_staged_file_is_missing() {
        let calls = std::cell::RefCell::new(Vec::new());
        let result = run_explicit_install(
            true,
            "missing.exe",
            |_| {
                calls.borrow_mut().push("exists");
                Err("missing".to_string())
            },
            |_| {
                calls.borrow_mut().push("explorer");
                Ok(())
            },
            |_| {
                calls.borrow_mut().push("installer");
                Ok(())
            },
            || calls.borrow_mut().push("exit"),
        );
        assert_eq!(result.unwrap_err(), "missing");
        assert_eq!(*calls.borrow(), ["exists"]);
    }

    #[test]
    fn explicit_install_stops_when_explorer_launch_fails() {
        let calls = std::cell::RefCell::new(Vec::new());
        let result = run_explicit_install(
            true,
            "installer.exe",
            |_| {
                calls.borrow_mut().push("exists");
                Ok(())
            },
            |_| {
                calls.borrow_mut().push("explorer");
                Err("explorer failed".to_string())
            },
            |_| {
                calls.borrow_mut().push("installer");
                Ok(())
            },
            || calls.borrow_mut().push("exit"),
        );
        assert_eq!(result.unwrap_err(), "explorer failed");
        assert_eq!(*calls.borrow(), ["exists", "explorer"]);
    }

    #[test]
    fn explicit_install_stops_when_shell_execute_fails_or_uac_is_cancelled() {
        let calls = std::cell::RefCell::new(Vec::new());
        let result = run_explicit_install(
            true,
            "installer.exe",
            |_| {
                calls.borrow_mut().push("exists");
                Ok(())
            },
            |_| {
                calls.borrow_mut().push("explorer");
                Ok(())
            },
            |_| {
                calls.borrow_mut().push("installer");
                Err("shell execute failed (UAC cancelled)".to_string())
            },
            || calls.borrow_mut().push("exit"),
        );
        assert_eq!(result.unwrap_err(), "shell execute failed (UAC cancelled)");
        assert_eq!(*calls.borrow(), ["exists", "explorer", "installer"]);
    }

    #[test]
    fn non_windows_explicit_install_reports_manual_install_without_execution() {
        let result = run_explicit_install(
            false,
            "installer.exe",
            |_| panic!("must not check a file on unsupported platforms"),
            |_| panic!("must not launch Explorer"),
            |_| panic!("must not launch the installer"),
            || panic!("must not exit"),
        );
        assert!(result.unwrap_err().contains("manual"));
    }

    #[cfg(windows)]
    #[test]
    fn shell_execute_ex_uses_unicode_open_without_installer_arguments() {
        use std::ffi::OsStr;
        use std::os::windows::ffi::OsStrExt;
        use windows_sys::Win32::UI::Shell::{SEE_MASK_FLAG_NO_UI, SEE_MASK_NOASYNC};
        use windows_sys::Win32::UI::WindowsAndMessaging::SW_SHOWNORMAL;
        let path = OsStr::new(r"C:\Users\用户\Downloads\安装 程序 & update.exe");
        windows_shell_open_with(path, None, |info| {
            let expected: Vec<_> = path.encode_wide().chain(Some(0)).collect();
            // Pointers borrow buffers alive for this callback only.
            unsafe {
                assert_eq!(
                    std::slice::from_raw_parts(info.lpFile, expected.len()),
                    expected
                );
                assert_eq!(
                    std::slice::from_raw_parts(info.lpVerb, 5),
                    [111, 112, 101, 110, 0]
                );
            }
            assert!(info.lpParameters.is_null(), "no silent or relaunch flags");
            assert_eq!(info.nShow, SW_SHOWNORMAL);
            assert_eq!(info.fMask, SEE_MASK_NOASYNC | SEE_MASK_FLAG_NO_UI);
            (1, 1223) // TRUE succeeds even if an old last-error value is present.
        })
        .unwrap();
    }

    #[cfg(windows)]
    #[test]
    fn shell_execute_ex_false_returns_windows_error_including_uac_cancellation() {
        for code in [0, 2, 5, 1223] {
            let error =
                windows_shell_open_with(std::ffi::OsStr::new("setup.exe"), None, |_| (0, code))
                    .unwrap_err();
            assert_eq!(error.raw_os_error(), Some(code as i32));
        }
    }

    #[cfg(windows)]
    #[test]
    fn explorer_select_preserves_quoted_unicode_and_space_path() {
        use std::ffi::OsStr;
        use std::os::windows::ffi::OsStrExt;
        let path = OsStr::new(r"C:\Users\用户\Downloads\安装 程序.exe");
        let parameters = explorer_select_parameters(path);
        assert_eq!(
            parameters,
            OsStr::new(r#"/select,"C:\Users\用户\Downloads\安装 程序.exe""#)
        );
        windows_shell_open_with(OsStr::new("explorer.exe"), Some(&parameters), |info| {
            let expected: Vec<_> = parameters.encode_wide().chain(Some(0)).collect();
            unsafe {
                assert_eq!(
                    std::slice::from_raw_parts(info.lpParameters, expected.len()),
                    expected
                );
            }
            (1, 0)
        })
        .unwrap();
    }

    #[cfg(windows)]
    #[test]
    fn shell_execute_rejects_nul_without_calling_windows() {
        use std::ffi::OsStr;
        for (path, parameters) in [
            (OsStr::new("setup\0.exe"), None),
            (
                OsStr::new("explorer.exe"),
                Some(OsStr::new("/select,\0path")),
            ),
        ] {
            let error = windows_shell_open_with(path, parameters, |_| panic!("must not execute"))
                .unwrap_err();
            assert_eq!(error.kind(), std::io::ErrorKind::InvalidInput);
        }
    }

    #[test]
    fn download_command_scopes_progress_and_avoids_shared_temp_or_stale_sweeps() {
        let source = include_str!("update.rs");
        let download = source
            .split("pub async fn app_download_update(")
            .nth(1)
            .unwrap()
            .split("/// Injectable launch sequence.")
            .next()
            .unwrap();
        assert!(
            download.contains("request_id: Option<String>"),
            "old clients may omit requestId"
        );
        assert!(
            !download.contains("dest.with_extension(\"part\")"),
            "downloads need unique temp files"
        );
        assert!(
            !download.contains("read_dir(update_staging_dir())"),
            "do not delete other requests' results"
        );
    }

    async fn local_download_response(body: &[u8], content_length: usize) -> reqwest::Response {
        use tokio::io::{AsyncReadExt, AsyncWriteExt};
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        let mut response = format!(
            "HTTP/1.1 200 OK\r\nContent-Length: {content_length}\r\nConnection: close\r\n\r\n"
        )
        .into_bytes();
        response.extend_from_slice(body);
        tokio::spawn(async move {
            let (mut stream, _) = listener.accept().await.unwrap();
            let mut buffer = [0; 4096];
            stream.read(&mut buffer).await.unwrap();
            stream.write_all(&response).await.unwrap();
            stream.shutdown().await.unwrap();
        });
        reqwest::Client::builder()
            .no_proxy()
            .timeout(Duration::from_secs(5))
            .build()
            .unwrap()
            .get(format!("http://{address}/setup.exe"))
            .send()
            .await
            .unwrap()
    }

    fn body_hash(body: &[u8]) -> String {
        let mut hasher = sha2_compatible::Hasher::new();
        hasher.update(body);
        hasher.hex()
    }

    #[tokio::test]
    async fn download_stages_verified_bytes_and_emits_request_id_on_every_progress() {
        let dir = tempfile::tempdir().unwrap();
        let dest = dir.path().join("setup.exe");
        let unrelated = dir.path().join("workbench-setup-another.exe");
        std::fs::write(&unrelated, b"other request").unwrap();
        let body = vec![42; 131072];
        let response = local_download_response(&body, body.len()).await;
        let mut progress = Vec::new();
        let result = stage_update_response(
            response,
            &dest,
            &body_hash(&body),
            Some("request A"),
            |event| progress.push(event),
        )
        .await
        .unwrap();
        assert_eq!(result.size, body.len() as u64);
        assert_eq!(result.sha256, body_hash(&body));
        assert_eq!(std::fs::read(&dest).unwrap(), body);
        assert_eq!(std::fs::read(&unrelated).unwrap(), b"other request");
        assert!(!progress.is_empty());
        assert!(progress
            .iter()
            .all(|event| event["requestId"] == "request A"));
        assert_eq!(progress.last().unwrap()["downloaded"], body.len() as u64);
        assert_eq!(std::fs::read_dir(dir.path()).unwrap().count(), 2);
    }

    #[tokio::test]
    async fn download_hash_failure_cleans_only_own_temp_and_preserves_other_result() {
        let dir = tempfile::tempdir().unwrap();
        let dest = dir.path().join("setup.exe");
        std::fs::write(&dest, b"newer verified result").unwrap();
        let response = local_download_response(b"bad", 3).await;
        let error = stage_update_response(response, &dest, &"0".repeat(64), None, |_| {})
            .await
            .unwrap_err();
        assert!(
            error
                .technical_detail
                .as_deref()
                .unwrap()
                .contains("sha256 mismatch"),
            "{error:?}"
        );
        assert_eq!(std::fs::read(&dest).unwrap(), b"newer verified result");
        assert_eq!(std::fs::read_dir(dir.path()).unwrap().count(), 1);
    }

    #[tokio::test]
    async fn download_stream_failure_cleans_only_own_temp() {
        let dir = tempfile::tempdir().unwrap();
        let dest = dir.path().join("setup.exe");
        std::fs::write(&dest, b"another result").unwrap();
        let response = local_download_response(b"short", 99999).await;
        let error = stage_update_response(response, &dest, &body_hash(b"short"), None, |_| {})
            .await
            .unwrap_err();
        assert!(
            error
                .technical_detail
                .as_deref()
                .unwrap()
                .contains(UPDATE_ERROR_NETWORK),
            "{error:?}"
        );
        assert_eq!(std::fs::read(&dest).unwrap(), b"another result");
        assert_eq!(std::fs::read_dir(dir.path()).unwrap().count(), 1);
    }

    #[tokio::test]
    async fn download_rename_failure_cleans_temp_and_retains_destination() {
        let dir = tempfile::tempdir().unwrap();
        let dest = dir.path().join("setup.exe");
        std::fs::create_dir(&dest).unwrap();
        let response = local_download_response(b"valid", 5).await;
        let error = stage_update_response(response, &dest, &body_hash(b"valid"), Some("a"), |_| {})
            .await
            .unwrap_err();
        assert!(
            error
                .technical_detail
                .as_deref()
                .unwrap()
                .contains("staging rename"),
            "{error:?}"
        );
        assert!(dest.is_dir());
        assert_eq!(std::fs::read_dir(dir.path()).unwrap().count(), 1);
    }

    #[tokio::test]
    async fn download_temps_are_unique_and_cleanup_does_not_touch_sibling_request() {
        let dir = tempfile::tempdir().unwrap();
        let dest = dir.path().join("setup.exe");
        let first = UpdateStaging::create(&dest, Some("../../request:中文"))
            .await
            .unwrap();
        let second = UpdateStaging::create(&dest, Some("../../request:中文"))
            .await
            .unwrap();
        assert_ne!(first.path, second.path);
        assert_eq!(first.path.parent(), dest.parent());
        assert_eq!(second.path.parent(), dest.parent());
        let first_path = first.path.clone();
        let second_path = second.path.clone();
        drop(first);
        assert!(!first_path.exists());
        assert!(second_path.exists());
        drop(second);
        assert_eq!(std::fs::read_dir(dir.path()).unwrap().count(), 0);
    }

    #[tokio::test]
    async fn download_staging_create_failure_is_reported_without_deleting_destination() {
        let dir = tempfile::tempdir().unwrap();
        let dest = dir.path().join("missing-parent").join("setup.exe");
        assert!(UpdateStaging::create(&dest, None).await.is_err());
        assert_eq!(std::fs::read_dir(dir.path()).unwrap().count(), 0);
    }

    async fn observed_endpoint(status: u16, requests: usize, delay: Duration) -> String {
        use tokio::io::{AsyncReadExt, AsyncWriteExt};
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        tokio::spawn(async move {
            for _ in 0..requests {
                let (mut stream, _) = listener.accept().await.unwrap();
                tokio::spawn(async move {
                    let mut request = [0; 4096];
                    let _ = stream.read(&mut request).await;
                    tokio::time::sleep(delay).await;
                    let response = format!(
                        "HTTP/1.1 {status} Test\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
                    );
                    let _ = stream.write_all(response.as_bytes()).await;
                });
            }
        });
        format!("http://{address}/asset")
    }

    #[tokio::test]
    async fn transport_records_failed_direct_before_successful_mirror_without_extra_probe() {
        use crate::update_health::{UpdateOutcome, UpdateTransport};
        let direct = observed_endpoint(403, 1, Duration::ZERO).await;
        let mirror = observed_endpoint(200, 1, Duration::ZERO).await;
        let clients = vec![(client_builder(None).unwrap(), UpdateTransport::Direct)];
        let mut observations = Vec::new();
        let response = get_candidates(
            &clients,
            &[direct.clone(), mirror.clone()],
            Default::default(),
            |endpoint, route, transport, outcome, elapsed| {
                observations.push((
                    endpoint.to_owned(),
                    format!("{route:?}"),
                    format!("{transport:?}"),
                    outcome,
                    elapsed,
                ));
            },
        )
        .await
        .unwrap();
        assert_eq!(response.status(), 200);
        assert_eq!(observations.len(), 2);
        assert_eq!(observations[0].0, direct);
        assert_eq!(observations[0].1, "Direct");
        assert!(matches!(observations[0].3, UpdateOutcome::HttpError(403)));
        assert_eq!(observations[1].0, mirror);
        assert_eq!(observations[1].1, "Mirror");
        assert_eq!(observations[1].2, "Direct");
        assert!(matches!(observations[1].3, UpdateOutcome::HeadersReceived));
    }

    #[tokio::test]
    async fn transport_records_timeout_and_every_exhausted_http_attempt() {
        use crate::update_health::{UpdateOutcome, UpdateTransport};
        let direct = observed_endpoint(200, 3, Duration::from_millis(100)).await;
        let mirror = observed_endpoint(503, 3, Duration::ZERO).await;
        let client = reqwest::Client::builder()
            .no_proxy()
            .timeout(Duration::from_millis(30))
            .build()
            .unwrap();
        let mut observations = Vec::new();
        let response = get_candidates(
            &[(client, UpdateTransport::Direct)],
            &[direct, mirror],
            Default::default(),
            |_, _, _, outcome, _| observations.push(outcome),
        )
        .await
        .unwrap();
        assert_eq!(response.status(), 503);
        assert_eq!(observations.len(), 6);
        assert!(observations
            .iter()
            .step_by(2)
            .all(|outcome| matches!(outcome, UpdateOutcome::Timeout)));
        assert!(observations
            .iter()
            .skip(1)
            .step_by(2)
            .all(|outcome| matches!(outcome, UpdateOutcome::HttpError(503))));
    }

    #[test]
    fn github_url_candidates_add_asset_and_raw_mirrors() {
        let url = "https://github.com/Wifabric/AISC/releases/download/v2.1.16-preview.3/AISC-Workbench-2.1.16-preview.3-setup.exe";
        assert_eq!(
            github_url_candidates(url),
            vec![
                url.to_string(),
                format!("https://ghfast.top/{url}"),
                format!("https://gh-proxy.com/{url}"),
            ]
        );

        let raw =
            "https://raw.githubusercontent.com/Wifabric/AISC/v2.1.16-preview.3/src/aisc/VERSION";
        assert_eq!(
            github_url_candidates(raw),
            vec![
                raw.to_string(),
                format!("https://ghfast.top/{raw}"),
                format!("https://gh-proxy.com/{raw}"),
            ]
        );
    }

    #[test]
    fn github_api_candidates_use_only_the_tested_api_mirror() {
        let url = "https://api.github.com/repos/Wifabric/AISC/releases?per_page=30";
        assert_eq!(
            github_url_candidates(url),
            vec![url.to_string(), format!("https://gh-proxy.com/{url}")]
        );
    }

    #[test]
    fn non_github_urls_have_no_mirror_candidates() {
        let url = "https://example.com/file";
        assert_eq!(github_url_candidates(url), vec![url.to_string()]);
    }

    #[test]
    fn local_cli_version_reads_frozen_envelope_cli_version_field() {
        let payload = br#"{"data":{"cli_version":"0.1.7.dev0","bundle_version":"0.1.7.dev0"}}"#;
        assert_eq!(
            cli_version_from_envelope(payload),
            Some("0.1.7.dev0".to_string())
        );
    }

    #[test]
    fn dash_version_normalizes_to_dot_dev() {
        assert_eq!(normalize_version("0.1.0-dev"), "0.1.0.dev0");
        assert_eq!(normalize_version("0.1.0"), "0.1.0");
    }

    #[test]
    fn tag_parsing_is_strict() {
        assert_eq!(parse_tag("v0.1.0"), Some(((0, 1, 0), true, 0)));
        assert_eq!(parse_tag("v1.2.3"), Some(((1, 2, 3), true, 0)));
        assert_eq!(parse_tag("v2.1.12-preview.1"), Some(((2, 1, 12), false, 1)));
        assert_eq!(parse_tag("v2.1.12-preview"), Some(((2, 1, 12), false, 1)));
        assert_eq!(parse_tag("v0.1.0.dev0"), None);
        assert_eq!(parse_tag("v0.1"), None);
        assert_eq!(parse_tag("0.1.0"), Some(((0, 1, 0), true, 0))); // v optional
    }

    #[test]
    fn atom_feed_finds_newest_release_without_rate_limited_api() {
        let atom = r#"
        <feed><entry><id>tag:github.com,2008:Repository/1/v2.1.15-preview.6</id></entry>
        <entry><id>tag:github.com,2008:Repository/1/v2.1.15-preview.7</id></entry>
        <entry><id>tag:github.com,2008:Repository/1/v2.1.14</id></entry></feed>
        "#;
        let (latest, setup, sha, page) = pick_latest_atom(atom).unwrap();
        assert_eq!(latest, "2.1.15-preview.7");
        assert_eq!(setup, "https://github.com/Wifabric/AISC/releases/download/v2.1.15-preview.7/AISC-Workbench-2.1.15-preview.7-setup.exe");
        assert_eq!(sha, "https://github.com/Wifabric/AISC/releases/download/v2.1.15-preview.7/AISC-Workbench-2.1.15-preview.7-setup.exe.sha256");
        assert_eq!(
            page,
            "https://github.com/Wifabric/AISC/releases/tag/v2.1.15-preview.7"
        );
    }

    #[test]
    fn picks_newest_workbench_setup_including_previews() {
        let releases = json!([
          // CLI Inno installer from the old pipeline — must NEVER match.
          { "tag_name": "v0.1.1", "assets": [
              { "name": "AISC-0.1.1-windows-x86_64-setup.exe",
                "browser_download_url": "cli-setup" },
          ], "html_url": "u0" },
          { "tag_name": "v2.1.12", "assets": [
              { "name": "AISC-Workbench-2.1.12-setup.exe",
                "browser_download_url": "s-final" },
              { "name": "AISC-Workbench-2.1.12-setup.exe.sha256",
                "browser_download_url": "h-final" },
          ], "html_url": "p-final" },
          { "tag_name": "v2.1.13-preview.1", "assets": [
              { "name": "AISC-Workbench-2.1.13-preview.1-setup.exe",
                "browser_download_url": "s-preview" },
              { "name": "AISC-Workbench-2.1.13-preview.1-setup.exe.sha256",
                "browser_download_url": "h-preview" },
          ], "html_url": "p-preview" },
        ]);
        // Preview channel: the newer preview beats the same-base final.
        let (tag, setup, sha, page) = pick_latest(&releases).unwrap();
        assert_eq!(tag, "2.1.13-preview.1");
        assert_eq!(setup, "s-preview");
        assert_eq!(sha, "h-preview");
        assert_eq!(page, "p-preview");
    }

    #[test]
    fn pick_rejects_the_cli_installer_asset() {
        let releases = json!([
          { "tag_name": "v0.1.1", "assets": [
              { "name": "AISC-0.1.1-windows-x86_64-setup.exe",
                "browser_download_url": "cli-setup" },
          ], "html_url": "u0" },
        ]);
        // No AISC-Workbench asset → setup URL is absent (asset? propagates).
        assert!(pick_latest(&releases).is_none());
    }

    #[test]
    fn cli_behind_makes_combined_update_available_even_when_gui_is_current() {
        assert!(combined_update_available(
            false,
            Some("0.1.7.dev0"),
            Some("0.1.8.dev0"),
        ));
        assert!(!combined_update_available(
            false,
            Some("0.1.8.dev0"),
            Some("0.1.8.dev0"),
        ));
        assert!(combined_update_available(
            true,
            Some("0.1.8.dev0"),
            Some("0.1.8.dev0"),
        ));
    }

    #[test]
    fn version_compare_final_beats_same_base_preview() {
        assert!(version_gt("2.1.12", "2.1.12-preview.2"));
        assert!(!version_gt("2.1.12-preview.2", "2.1.12"));
        assert!(version_gt("2.1.12-preview.2", "2.1.12-preview.1"));
        assert!(version_gt("2.1.13-preview.1", "2.1.12"));
    }
}
