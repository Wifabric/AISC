//! User-level module definitions. No installed state or credentials live here.
use std::{collections::{BTreeMap, HashSet}, fs, path::Path};
use fs4::fs_std::FileExt;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use crate::error::WorkbenchError;

const FILE: &str = "extension-modules.json";

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ModuleMember {
    pub kind: String,
    pub identity: String,
    pub name: String,
    pub source_url: String,
    #[serde(flatten)]
    extra: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ExtensionModule {
    pub id: String,
    pub name: String,
    pub members: Vec<ModuleMember>,
    #[serde(flatten)]
    extra: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ModuleDocument {
    pub schema_version: u64,
    pub revision: u64,
    pub definitions: Vec<ExtensionModule>,
    pub hidden_builtin_ids: Vec<String>,
    #[serde(flatten)]
    extra: BTreeMap<String, Value>,
}

impl Default for ModuleDocument {
    fn default() -> Self {
        Self { schema_version: 1, revision: 0, definitions: vec![], hidden_builtin_ids: vec![], extra: BTreeMap::new() }
    }
}

fn validate(doc: &mut ModuleDocument) -> Result<(), String> {
    if doc.schema_version != 1 { return Err("Unsupported module schema; original file preserved".into()); }
    if doc.definitions.len() > 500 { return Err("Too many modules (maximum 500)".into()); }
    let mut ids = HashSet::new();
    for module in &mut doc.definitions {
        if module.id.is_empty() || module.id.len() > 128 || !ids.insert(module.id.clone()) {
            return Err("Invalid or duplicate module ID".into());
        }
        module.name = module.name.trim().to_string();
        if module.name.is_empty() || module.name.len() > 512 || module.members.len() > 200 {
            return Err("Module needs a name and at most 200 members".into());
        }
        let mut members = HashSet::new();
        for member in &module.members {
            if !matches!(member.kind.as_str(), "skills" | "mcp" | "plugins")
                || member.identity.trim().is_empty() || member.identity.len() > 2048
                || member.identity.contains(char::is_whitespace)
                || member.name.trim().is_empty() || member.name.len() > 512 {
                return Err("Invalid module member identity".into());
            }
            let url = reqwest::Url::parse(&member.source_url).map_err(|_| "Invalid member source URL")?;
            if !matches!(url.scheme(), "https" | "http") || url.host_str().is_none()
                || !url.username().is_empty() || url.password().is_some() {
                return Err("Member source must be an HTTP(S) URL without credentials".into());
            }
        }
        module.members.retain(|m| members.insert((m.kind.clone(), m.identity.clone())));
    }
    Ok(())
}

fn lock(dir: &Path) -> Result<fs::File, String> {
    fs::create_dir_all(dir).map_err(|e| e.to_string())?;
    let file = fs::OpenOptions::new().create(true).read(true).write(true)
        .open(dir.join("extension-modules.lock")).map_err(|e| e.to_string())?;
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
    loop {
        if file.try_lock_exclusive().map_err(|e| e.to_string())? { return Ok(file); }
        if std::time::Instant::now() >= deadline { return Err("Module document is busy; retry".into()); }
        std::thread::sleep(std::time::Duration::from_millis(25));
    }
}

fn read_locked(dir: &Path) -> Result<ModuleDocument, String> {
    let path = dir.join(FILE);
    let backup = dir.join(format!("{FILE}.bak"));
    if !path.exists() && backup.exists() {
        fs::rename(&backup, &path).map_err(|e| e.to_string())?;
    }
    let bytes = match fs::read(&path) {
        Ok(bytes) => bytes,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(ModuleDocument::default()),
        Err(e) => return Err(e.to_string()),
    };
    let mut doc: ModuleDocument = serde_json::from_slice(&bytes)
        .map_err(|e| format!("Cannot read module definitions; original file preserved: {e}"))?;
    validate(&mut doc)?;
    Ok(doc)
}

pub fn load_document(dir: &Path) -> Result<ModuleDocument, String> {
    let _lock = lock(dir)?;
    read_locked(dir)
}

pub fn save_document(dir: &Path, expected: u64, mut next: ModuleDocument) -> Result<ModuleDocument, String> {
    let _lock = lock(dir)?;
    let current = read_locked(dir)?;
    if current.revision != expected {
        return Err("Module definitions changed in another window. Reload before saving; draft retained.".into());
    }
    validate(&mut next)?;
    next.revision = current.revision.checked_add(1).ok_or("Module revision overflow")?;
    // Preserve fields written by compatible versions even when an older UI
    // sends only fields it knows.
    for (key, value) in current.extra { next.extra.entry(key).or_insert(value); }
    for module in &mut next.definitions {
        if let Some(old) = current.definitions.iter().find(|m| m.id == module.id) {
            for (key, value) in &old.extra { module.extra.entry(key.clone()).or_insert(value.clone()); }
            for member in &mut module.members {
                if let Some(old_member) = old.members.iter().find(|m| m.kind == member.kind && m.identity == member.identity) {
                    for (key, value) in &old_member.extra { member.extra.entry(key.clone()).or_insert(value.clone()); }
                }
            }
        }
    }
    let bytes = serde_json::to_vec_pretty(&next).map_err(|e| e.to_string())?;
    crate::storage::atomic_replace(&dir.join(FILE), &bytes).map_err(|e| e.to_string())?;
    Ok(next)
}

#[tauri::command]
pub async fn load_extension_modules(app: tauri::AppHandle) -> Result<ModuleDocument, WorkbenchError> {
    let dir = crate::session::config_dir(&app)?;
    tauri::async_runtime::spawn_blocking(move || load_document(&dir)).await
        .map_err(|e| WorkbenchError::cli_protocol().with_detail(e.to_string()))?
        .map_err(|e| WorkbenchError::cli_protocol().with_detail(e))
}

#[tauri::command]
pub async fn save_extension_modules(app: tauri::AppHandle, expected_revision: u64, document: ModuleDocument) -> Result<ModuleDocument, WorkbenchError> {
    let dir = crate::session::config_dir(&app)?;
    tauri::async_runtime::spawn_blocking(move || save_document(&dir, expected_revision, document)).await
        .map_err(|e| WorkbenchError::cli_protocol().with_detail(e.to_string()))?
        .map_err(|e| WorkbenchError::cli_protocol().with_detail(e))
}

#[cfg(test)]
mod tests {
    use super::*;
    fn document() -> ModuleDocument {
        serde_json::from_value(serde_json::json!({"schema_version":1,"revision":0,"hidden_builtin_ids":[],"definitions":[
            {"id":"qa","name":" QA module ","members":[{"kind":"skills","identity":"owner/repo:skill","name":"Skill","source_url":"https://github.com/owner/repo"}]}]})).unwrap()
    }
    #[test]
    fn persists_offline_and_rejects_stale_writers() {
        let dir = tempfile::tempdir().unwrap();
        assert_eq!(load_document(dir.path()).unwrap().revision, 0);
        let mut doc = document();
        let duplicate = doc.definitions[0].members[0].clone();
        doc.definitions[0].members.push(duplicate);
        let saved = save_document(dir.path(), 0, doc).unwrap();
        assert_eq!(saved.definitions[0].members.len(), 1);
        assert_eq!(load_document(dir.path()).unwrap().definitions[0].name, "QA module");
        assert!(save_document(dir.path(), 0, document()).is_err());
        assert_eq!(load_document(dir.path()).unwrap().revision, 1);
    }
    #[test]
    fn corrupt_or_future_documents_cannot_be_overwritten() {
        let dir = tempfile::tempdir().unwrap();
        for bytes in ["{broken".to_string(), serde_json::to_string(&ModuleDocument { schema_version: 99, ..document() }).unwrap()] {
            fs::write(dir.path().join(FILE), &bytes).unwrap();
            assert!(load_document(dir.path()).is_err());
            assert!(save_document(dir.path(), 0, document()).is_err());
            assert_eq!(fs::read_to_string(dir.path().join(FILE)).unwrap(), bytes);
        }
    }
    #[test]
    fn recovers_interrupted_replace_and_preserves_unknown_fields() {
        let dir = tempfile::tempdir().unwrap();
        let mut doc = document();
        doc.extra.insert("future".into(), serde_json::json!({"safe":true}));
        doc.definitions[0].extra.insert("future_member_policy".into(), Value::Bool(true));
        fs::write(dir.path().join(format!("{FILE}.bak")), serde_json::to_vec(&doc).unwrap()).unwrap();
        assert!(load_document(dir.path()).unwrap().extra.contains_key("future"));
        let saved = save_document(dir.path(), 0, document()).unwrap();
        assert!(saved.extra.contains_key("future"));
        assert!(saved.definitions[0].extra.contains_key("future_member_policy"));
    }
    #[test]
    fn invalid_member_does_not_change_saved_file() {
        let dir = tempfile::tempdir().unwrap();
        let saved = save_document(dir.path(), 0, document()).unwrap();
        for kind in ["unknown", "skills"] {
            let mut invalid = saved.clone();
            invalid.definitions[0].members[0].kind = kind.into();
            invalid.definitions[0].members[0].source_url = "https://user:secret@example.org".into();
            assert!(save_document(dir.path(), 1, invalid).is_err());
        }
        assert_eq!(load_document(dir.path()).unwrap().revision, 1);
    }
    #[test]
    fn competing_windows_cannot_overwrite_each_other() {
        let dir = tempfile::tempdir().unwrap();
        let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
        let threads: Vec<_> = (0..2).map(|index| {
            let path = dir.path().to_path_buf();
            let barrier = barrier.clone();
            std::thread::spawn(move || {
                let mut doc = document();
                doc.definitions[0].name = format!("window-{index}");
                barrier.wait();
                save_document(&path, 0, doc)
            })
        }).collect();
        let results: Vec<_> = threads.into_iter().map(|t| t.join().unwrap()).collect();
        assert_eq!(results.iter().filter(|r| r.is_ok()).count(), 1);
        let winner = results.into_iter().find_map(Result::ok).unwrap();
        assert_eq!(load_document(dir.path()).unwrap().definitions[0].name, winner.definitions[0].name);
    }
}
