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
//! Channel: FINAL releases only (D-17 — vMAJOR.MINOR.PATCH tags; dev/rc
//! never show up here; CLI-side dev iteration rides TestPyPI instead).
//! Transport: reqwest + system proxy (WinINET probe, subscription.rs
//! pattern — same-stack reuse, no new deps).

use std::path::PathBuf;
use std::time::Duration;

use serde::Serialize;
use tauri::AppHandle;
use tauri::Emitter;

use crate::error::WorkbenchError;

const RELEASES_URL: &str = "https://api.github.com/repos/wangyuncepu/AISC/releases?per_page=30";
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

/// Parse `vMAJOR.MINOR.PATCH` (final-only channel, D-17). None otherwise.
pub fn parse_final_tag(tag: &str) -> Option<(u64, u64, u64)> {
    let body = tag.strip_prefix('v')?;
    let mut it = body.split('.');
    let majors = it.next()?.parse().ok()?;
    let minors = it.next()?.parse().ok()?;
    let patch = it.next()?.parse().ok()?;
    if it.next().is_some() {
        return None; // 4+ segments = not a final tag
    }
    Some((majors, minors, patch))
}

fn client() -> Result<reqwest::Client, WorkbenchError> {
    let mut builder = reqwest::Client::builder()
        .user_agent("aisc-workbench-selfupdate")
        .timeout(Duration::from_secs(30));
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
pub fn pick_latest_final(releases: &serde_json::Value) -> Option<(String, String, String, String)> {
    let arr = releases.as_array()?;
    let mut best: Option<((u64, u64, u64), &str)> = None;
    for rel in arr {
        let tag = rel.get("tag_name").and_then(|t| t.as_str()).unwrap_or("");
        let Some(key) = parse_final_tag(tag) else {
            continue; // dev/rc tags are channel noise, not a failure
        };
        if best.is_none_or(|(k, _)| key > k) {
            best = Some((key, tag));
        }
    }
    let (_, tag) = best?;
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
        if name.ends_with("-setup.exe") {
            setup = Some(url.to_string());
        } else if name.ends_with("-setup.exe.sha256") {
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
    let key = |v: &str| -> (u64, u64, u64, u64) {
        let body = v.split(['-', '.']).collect::<Vec<_>>();
        let n = |i: usize| body.get(i).and_then(|s| s.parse().ok()).unwrap_or(0);
        (n(0), n(1), n(2), if v.contains("dev") { 0 } else { 1 })
    };
    key(a) > key(b)
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
        Ok(body) => match pick_latest_final(&body) {
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
                note: "no final release published yet".into(),
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

fn staging_path(app: &AppHandle) -> PathBuf {
    let dir = std::env::temp_dir().join("aisc-workbench-update");
    let _ = std::fs::create_dir_all(&dir);
    dir.join(format!("workbench-setup-{}.exe", current_version(app)))
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
    let dest = staging_path(&app);
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
        std::process::Command::new("cmd")
            .args(["/c", "start", "", &setup_path, "/S"])
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
    fn final_tag_parsing_is_strict() {
        assert_eq!(parse_final_tag("v0.1.0"), Some((0, 1, 0)));
        assert_eq!(parse_final_tag("v1.2.3"), Some((1, 2, 3)));
        assert_eq!(parse_final_tag("v0.1.0.dev0"), None);
        assert_eq!(parse_final_tag("v0.1.0-dev"), None);
        assert_eq!(parse_final_tag("v0.1"), None);
        assert_eq!(parse_final_tag("0.1.0"), None); // must carry the v
    }

    #[test]
    fn picks_newest_final_ignoring_prereleases() {
        let releases = json!([
          { "tag_name": "v0.2.0-dev1", "assets": [], "html_url": "u1" },
          { "tag_name": "v0.1.0", "assets": [
              { "name": "AISC.Workbench_0.1.0_x64-setup.exe",
                "browser_download_url": "s1" },
              { "name": "AISC.Workbench_0.1.0_x64-setup.exe.sha256",
                "browser_download_url": "h1" },
          ], "html_url": "p1" },
          { "tag_name": "v0.3.0", "assets": [
              { "name": "AISC.Workbench_0.3.0_x64-setup.exe",
                "browser_download_url": "s3" },
              { "name": "AISC.Workbench_0.3.0_x64-setup.exe.sha256",
                "browser_download_url": "h3" },
          ], "html_url": "p3" },
        ]);
        let (tag, setup, sha, page) = pick_latest_final(&releases).unwrap();
        assert_eq!(tag, "0.3.0");
        assert_eq!(setup, "s3");
        assert_eq!(sha, "h3");
        assert_eq!(page, "p3");
    }

    #[test]
    fn version_compare_treats_dev_below_final() {
        assert!(version_gt("0.1.0", "0.1.0.dev0"));
        assert!(!version_gt("0.1.0.dev0", "0.1.0"));
        assert!(version_gt("0.2.0", "0.1.9"));
    }
}
