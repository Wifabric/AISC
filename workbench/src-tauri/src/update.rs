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

fn client() -> Result<reqwest::Client, WorkbenchError> {
    let mut builder = reqwest::Client::builder()
        .user_agent("aisc-workbench-selfupdate")
        // b12 (T1 user report): the old TOTAL timeout(30s) was fine for the
        // subscription downloader's small files and the ~60MB payloads of
        // 2.1.13-era installers — but the C-混合 bundles pushed the setup to
        // 292MB and every in-app download now died ~30s in ("参数无效"/断流).
        // Bound STALLS, not total size: connect 10s, read 60s idle.
        .connect_timeout(Duration::from_secs(10))
        .read_timeout(Duration::from_secs(60));
    if let Some(proxy) = crate::subscription::system_http_proxy() {
        if let Ok(p) = reqwest::Proxy::all(&proxy) {
            builder = builder.proxy(p);
        }
    }
    builder
        .build()
        .map_err(|e| WorkbenchError::usage(format!("http client: {e}")))
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
        Some((b, n)) => (b, Some(if n.is_empty() { "1" } else { n.trim_start_matches('.') })),
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
    for asset in rel.get("assets").and_then(|a| a.as_array()).unwrap_or(&vec![]) {
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

fn version_gt(a: &str, b: &str) -> bool {
    version_key(a) > version_key(b)
}

/// Check for a newer FINAL release. Network failures degrade to a
/// note-carrying UpdateInfo (a check must never crash the menu), except
/// when a hard error object is needed by tests.
#[tauri::command]
pub async fn app_check_update(app: AppHandle) -> Result<UpdateInfo, WorkbenchError> {
    let current = current_version(&app);
    let fetch = async {
        let resp = client()?
            .get(RELEASES_URL)
            .headers(gh_headers())
            .send()
            .await
            .map_err(|e| WorkbenchError::usage(format!("{UPDATE_ERROR_NETWORK}: {e}")))?;
        if !resp.status().is_success() {
            return Err(WorkbenchError::usage(format!(
                "{UPDATE_ERROR_NETWORK}: HTTP {}",
                resp.status()
            )));
        }
        let text = resp
            .text()
            .await
            .map_err(|e| WorkbenchError::usage(format!("{UPDATE_ERROR_NETWORK}: {e}")))?;
        let body: serde_json::Value = serde_json::from_str(&text)
            .map_err(|e| WorkbenchError::usage(format!("{UPDATE_ERROR_NETWORK}: body: {e}")))?;
        Ok::<_, WorkbenchError>(body)
    };
    let info = match fetch.await {
        Ok(body) => match pick_latest(&body) {
            Some((latest, setup, sha, page)) => UpdateInfo {
                update_available: version_gt(&latest, &current),
                current,
                latest: Some(latest),
                setup_url: Some(setup),
                sha256_url: Some(sha),
                release_url: Some(page),
                note: String::new(),
            },
            None => UpdateInfo {
                current,
                latest: None,
                update_available: false,
                setup_url: None,
                sha256_url: None,
                release_url: None,
                note: "no newer published version available".into(),
            },
        },
        Err(e) => UpdateInfo {
            current,
            latest: None,
            update_available: false,
            setup_url: None,
            sha256_url: None,
            release_url: None,
            note: format!("check failed (offline?): {}", e.technical_detail.unwrap_or_default()),
        },
    };
    Ok(info)
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
    let name = if safe.is_empty() { current_version(app) } else { safe };
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
    let client = client()?;
    let sidecar = client
        .get(&sha256_url)
        .headers(gh_headers())
        .send()
        .await
        .map_err(|e| WorkbenchError::usage(format!("{UPDATE_ERROR_NETWORK}: sha256 sidecar: {e}")))?;
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

    let mut resp = client
        .get(&setup_url)
        .headers(gh_headers())
        .send()
        .await
        .map_err(|e| WorkbenchError::usage(format!("{UPDATE_ERROR_NETWORK}: setup download: {e}")))?;
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
    file.flush().await.map_err(|e| WorkbenchError::usage(format!("staging flush: {e}")))?;
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
            if name.starts_with("workbench-setup-") && name.ends_with(".exe") && entry.path() != dest {
                let _ = tokio::fs::remove_file(entry.path()).await;
            }
        }
    }
    Ok(DownloadResult { path: dest.display().to_string(), sha256: actual, size: downloaded })
}

/// Run the staged installer SILENT and exit. The UI has already collected
/// the user's confirmation; the installer owns everything from here
/// (PATH takeover + docker lifecycle + file replacement).
#[tauri::command]
pub async fn app_install_update(app: AppHandle, setup_path: String) -> Result<(), WorkbenchError> {
    let setup = PathBuf::from(&setup_path);
    if !setup.is_file() {
        return Err(WorkbenchError::usage(format!("staged setup not found: {setup_path}")));
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
    let spawn = std::process::Command::new(&setup_path)
        .arg("-S")
        .spawn();
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
    use super::*;
    use serde_json::json;

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
    fn version_compare_final_beats_same_base_preview() {
        assert!(version_gt("2.1.12", "2.1.12-preview.2"));
        assert!(!version_gt("2.1.12-preview.2", "2.1.12"));
        assert!(version_gt("2.1.12-preview.2", "2.1.12-preview.1"));
        assert!(version_gt("2.1.13-preview.1", "2.1.12"));
    }
}
