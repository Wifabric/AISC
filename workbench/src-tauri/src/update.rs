//! A7 (0.1.0, D-8 ruling 自研): Workbench self-update — the light path.
//!
//! check → download (sha256-verified, progress events, nothing lands on
//! failure) → the UI collects the user's confirmation → the NSIS installer
//! runs SILENT (/S; installer.nsi has explicit `${Silent}` branches) and
//! the app exits so files can be replaced. The installer already chains
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

use std::path::PathBuf;
use std::time::Duration;

use serde::Serialize;
use tauri::AppHandle;
use tauri::Emitter;

use crate::error::WorkbenchError;

const RELEASES_URL: &str = "https://api.github.com/repos/Wifabric/AISC/releases?per_page=30";
const RELEASES_ATOM_URL: &str = "https://github.com/Wifabric/AISC/releases.atom";
const UPDATE_ERROR_NETWORK: &str = "app.update/network";

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
        if let Ok(proxy) = reqwest::Proxy::all(proxy) {
            builder = builder.proxy(proxy);
        }
    }
    builder
        .build()
        .map_err(|e| WorkbenchError::usage(format!("http client: {e}")))
}

fn client() -> Result<reqwest::Client, WorkbenchError> {
    client_builder(crate::subscription::system_http_proxy().as_deref())
}

/// Network strategies in priority order. A stale/clash proxy must not make
/// GitHub permanently unreachable; a direct connection must not be skipped in
/// environments where the proxy is required. Try both, with bounded retries.
fn update_clients() -> Result<Vec<reqwest::Client>, WorkbenchError> {
    match crate::subscription::system_http_proxy() {
        Some(proxy) => Ok(vec![client_builder(Some(&proxy))?, client_builder(None)?]),
        None => Ok(vec![client_builder(None)?]),
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

async fn get_with_fallback(
    url: &str,
    headers: reqwest::header::HeaderMap,
) -> Result<reqwest::Response, WorkbenchError> {
    let clients = update_clients()?;
    let mut errors = Vec::new();
    for attempt in 0..3 {
        for client in &clients {
            match client.get(url).headers(headers.clone()).send().await {
                Ok(response) => return Ok(response),
                Err(e) => errors.push(format!("attempt {}: {}", attempt + 1, err_chain(&e))),
            }
        }
        if attempt < 2 {
            tokio::time::sleep(Duration::from_millis(300)).await;
        }
    }
    Err(WorkbenchError::usage(format!(
        "{UPDATE_ERROR_NETWORK}: {url}: {}",
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
        return Err(WorkbenchError::usage(format!(
            "{UPDATE_ERROR_NETWORK}: bundled CLI HTTP {}",
            response.status()
        )));
    }
    let text = response.text().await.map_err(|e| {
        WorkbenchError::usage(format!("{UPDATE_ERROR_NETWORK}: bundled CLI body: {e}"))
    })?;
    let version = text.trim().to_string();
    if version.is_empty() {
        return Err(WorkbenchError::usage(format!(
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

/// Stream the setup.exe to a staging file, verify against the .sha256
/// sidecar, emit `update://progress` {downloaded,total} along the way.
/// Nothing is kept on any failure (fail-closed, D-8).
#[tauri::command]
pub async fn app_download_update(
    app: AppHandle,
    setup_url: String,
    sha256_url: String,
    target_version: String,
) -> Result<DownloadResult, WorkbenchError> {
    let sidecar = get_with_fallback(&sha256_url, gh_headers()).await?;
    if !sidecar.status().is_success() {
        return Err(WorkbenchError::usage(format!(
            "{UPDATE_ERROR_NETWORK}: sha256 sidecar HTTP {}",
            sidecar.status()
        )));
    }
    let sidecar_text = sidecar
        .text()
        .await
        .map_err(|e| WorkbenchError::usage(format!("{UPDATE_ERROR_NETWORK}: {e}")))?;
    let expected = sidecar_text
        .split_whitespace()
        .next()
        .unwrap_or("")
        .to_ascii_lowercase();
    if expected.len() != 64 {
        return Err(WorkbenchError::usage("sha256 sidecar malformed"));
    }

    let mut resp = get_with_fallback(&setup_url, gh_headers()).await?;
    if !resp.status().is_success() {
        return Err(WorkbenchError::usage(format!(
            "{UPDATE_ERROR_NETWORK}: setup download HTTP {}",
            resp.status()
        )));
    }
    let total = resp.content_length().unwrap_or(0);
    let dest = staging_path(&app, &target_version);
    let tmp = dest.with_extension("part");
    use tokio::io::AsyncWriteExt;
    let mut file = tokio::fs::File::create(&tmp)
        .await
        .map_err(|e| WorkbenchError::usage(format!("staging create: {e}")))?;
    let mut hasher = sha2_compatible::Hasher::new();
    let mut downloaded: u64 = 0;
    loop {
        let chunk = resp
            .chunk()
            .await
            .map_err(|e| WorkbenchError::usage(format!("{UPDATE_ERROR_NETWORK}: {e}")))?
            .unwrap_or_default();
        if chunk.is_empty() {
            break;
        }
        hasher.update(&chunk);
        file.write_all(&chunk)
            .await
            .map_err(|e| WorkbenchError::usage(format!("staging write: {e}")))?;
        downloaded += chunk.len() as u64;
        let _ = app.emit(
            "update://progress",
            serde_json::json!({ "downloaded": downloaded, "total": total }),
        );
    }
    file.flush()
        .await
        .map_err(|e| WorkbenchError::usage(format!("staging flush: {e}")))?;
    drop(file);
    let actual = hasher.hex();
    if actual != expected {
        let _ = tokio::fs::remove_file(&tmp).await;
        return Err(WorkbenchError::usage(format!(
            "sha256 mismatch: expected {expected:.16}..., got {actual:.16}... — download discarded"
        )));
    }
    tokio::fs::rename(&tmp, &dest)
        .await
        .map_err(|e| WorkbenchError::usage(format!("staging rename: {e}")))?;
    // b1: drop stale staged installers from previous updates — they used to
    // masquerade under the current version's name and lingered in %TEMP%.
    if let Ok(entries) = std::fs::read_dir(update_staging_dir()) {
        for entry in entries.flatten() {
            let name = entry.file_name();
            let name = name.to_string_lossy();
            if name.starts_with("workbench-setup-")
                && name.ends_with(".exe")
                && entry.path() != dest
            {
                let _ = tokio::fs::remove_file(entry.path()).await;
            }
        }
    }
    Ok(DownloadResult {
        path: dest.display().to_string(),
        sha256: actual,
        size: downloaded,
    })
}

/// Run the staged installer SILENT and exit. The UI has already collected
/// the user's confirmation; the installer owns everything from here
/// (PATH takeover + docker lifecycle + file replacement).
#[tauri::command]
pub async fn app_install_update(app: AppHandle, setup_path: String) -> Result<(), WorkbenchError> {
    let setup = PathBuf::from(&setup_path);
    if !setup.is_file() {
        return Err(WorkbenchError::usage(format!(
            "staged setup not found: {setup_path}"
        )));
    }
    // Detached start: cmd /c start keeps the installer alive after we exit.
    #[cfg(windows)]
    let spawn = {
        use std::os::windows::process::CommandExt;
        // b1: /R makes the silent installer relaunch the app as the
        // ORIGINAL user (nsis_tauri_utils::RunAsUser) once the upgrade chain
        // — PATH takeover, docker cleanup/rebuild — finishes (.onInstSuccess).
        // No elevation is inherited: this installer runs with
        // RequestExecutionLevel user and RunAsUser is a second guard.
        std::process::Command::new("cmd")
            .args(["/c", "start", "", &setup_path, "/S", "/R"])
            .creation_flags(0x0800_0000) // CREATE_NO_WINDOW
            .spawn()
    };
    #[cfg(not(windows))]
    let spawn = std::process::Command::new(&setup_path).arg("-S").spawn();
    spawn.map_err(|e| WorkbenchError::usage(format!("installer spawn: {e}")))?;
    // Give the OS a beat to detach, then exit the app (files are in use).
    tokio::time::sleep(Duration::from_millis(600)).await;
    app.exit(0);
    Ok(())
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
