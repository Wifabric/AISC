//! Passive host-update observations. Reading a snapshot never performs a probe.

use std::collections::VecDeque;
use std::sync::{Mutex, OnceLock};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

const MAX_OBSERVATIONS: usize = 100;
static OBSERVATIONS: OnceLock<Mutex<VecDeque<UpdateObservation>>> = OnceLock::new();

#[derive(Debug, Clone, Copy)]
pub enum UpdateRoute {
    Direct,
    Mirror,
}
#[derive(Debug, Clone, Copy)]
pub enum UpdateTransport {
    Direct,
    SystemProxy,
}
#[derive(Debug, Clone, Copy)]
pub enum UpdateOutcome {
    /// The HTTP headers arrived; the body may still fail or time out later.
    HeadersReceived,
    Success,
    HttpError(u16),
    Timeout,
    NetworkError,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateObservation {
    pub scope: &'static str,
    pub endpoint: String,
    pub route: &'static str,
    pub transport: &'static str,
    pub status: &'static str,
    pub latency_ms: u64,
    pub error_code: Option<String>,
    /// Unix epoch milliseconds captured when this attempt completes, not on read.
    pub checked_at: u64,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateHealth {
    pub workbench_version: String,
    pub observations: Vec<UpdateObservation>,
    pub container_extensions: ContainerExtensionsHealth,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct ContainerExtensionsHealth {
    pub status: &'static str,
    pub reason: &'static str,
}

fn append_attempt(
    observations: &mut VecDeque<UpdateObservation>,
    endpoint: &str,
    route: UpdateRoute,
    transport: UpdateTransport,
    outcome: UpdateOutcome,
    latency: Duration,
    checked_at: u64,
) {
    // Origin-only provenance also drops credentials hidden in mirrored URL
    // paths. Never accept headers, raw error messages or response bodies.
    let endpoint = reqwest::Url::parse(endpoint)
        .ok()
        .filter(|url| matches!(url.scheme(), "http" | "https") && url.has_host())
        .map(|url| url.origin().ascii_serialization())
        .unwrap_or_else(|| "[redacted]".to_owned());
    let (status, error_code) = match outcome {
        UpdateOutcome::HeadersReceived => ("headers-received", None),
        UpdateOutcome::Success => ("success", None),
        UpdateOutcome::HttpError(code) => ("http-error", Some(format!("HTTP_{code}"))),
        UpdateOutcome::Timeout => ("timeout", Some("TIMEOUT".to_owned())),
        UpdateOutcome::NetworkError => ("network-error", Some("NETWORK_ERROR".to_owned())),
    };
    while observations.len() >= MAX_OBSERVATIONS {
        observations.pop_front();
    }
    observations.push_back(UpdateObservation {
        scope: "host-update",
        endpoint,
        route: match route {
            UpdateRoute::Direct => "direct",
            UpdateRoute::Mirror => "mirror",
        },
        transport: match transport {
            UpdateTransport::Direct => "direct",
            UpdateTransport::SystemProxy => "system-proxy",
        },
        status,
        latency_ms: millis(latency),
        error_code,
        checked_at,
    });
}

fn snapshot_health(observations: &VecDeque<UpdateObservation>, version: &str) -> UpdateHealth {
    UpdateHealth {
        workbench_version: version.to_owned(),
        observations: observations.iter().cloned().collect(),
        container_extensions: ContainerExtensionsHealth {
            status: "unknown",
            reason: "not-probed",
        },
    }
}

fn millis(duration: Duration) -> u64 {
    duration.as_millis().min(u64::MAX as u128) as u64
}

fn observations() -> &'static Mutex<VecDeque<UpdateObservation>> {
    OBSERVATIONS.get_or_init(|| Mutex::new(VecDeque::with_capacity(MAX_OBSERVATIONS)))
}

/// Record exactly one completed real request attempt. The caller supplies the
/// actual candidate route and client transport; this function never probes.
/// `latency` is the elapsed request duration, usually `Instant::elapsed()`.
pub fn record_attempt(
    endpoint: &str,
    route: UpdateRoute,
    transport: UpdateTransport,
    outcome: UpdateOutcome,
    latency: Duration,
) {
    let checked_at = millis(
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default(),
    );
    let mut rows = observations()
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner());
    append_attempt(
        &mut rows, endpoint, route, transport, outcome, latency, checked_at,
    );
}

/// Read-only, process-local history. Empty means no host attempts observed;
/// container extension connectivity is always unknown because it is unprobed.
#[tauri::command]
pub fn app_update_health(app: tauri::AppHandle) -> UpdateHealth {
    let rows = observations()
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner());
    snapshot_health(&rows, &app.package_info().version.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn append(
        rows: &mut VecDeque<UpdateObservation>,
        endpoint: &str,
        route: UpdateRoute,
        transport: UpdateTransport,
        outcome: UpdateOutcome,
        at: u64,
    ) {
        append_attempt(
            rows,
            endpoint,
            route,
            transport,
            outcome,
            Duration::from_millis(42),
            at,
        );
    }

    #[test]
    fn headers_received_does_not_claim_body_transfer_success() {
        let mut rows = VecDeque::new();
        append(
            &mut rows,
            "https://github.com",
            UpdateRoute::Direct,
            UpdateTransport::Direct,
            UpdateOutcome::HeadersReceived,
            1,
        );
        assert_eq!(rows[0].status, "headers-received");
        assert_eq!(rows[0].error_code, None);
    }

    #[test]
    fn direct_success_has_explicit_wire_contract() {
        let mut rows = VecDeque::new();
        append(
            &mut rows,
            "https://api.github.com/repos/Wifabric/AISC/releases?per_page=30",
            UpdateRoute::Direct,
            UpdateTransport::Direct,
            UpdateOutcome::Success,
            1234,
        );
        let value = serde_json::to_value(snapshot_health(&rows, "2.1.17")).unwrap();
        assert_eq!(
            value,
            serde_json::json!({
                "workbenchVersion": "2.1.17", "observations": [{
                    "scope": "host-update", "endpoint": "https://api.github.com",
                    "route": "direct", "transport": "direct", "status": "success",
                    "latencyMs": 42, "errorCode": null, "checkedAt": 1234
                }], "containerExtensions": {"status": "unknown", "reason": "not-probed"}
            })
        );
    }

    #[test]
    fn retains_direct_failure_before_mirror_success() {
        let mut rows = VecDeque::new();
        append(
            &mut rows,
            "https://github.com",
            UpdateRoute::Direct,
            UpdateTransport::SystemProxy,
            UpdateOutcome::HttpError(403),
            100,
        );
        append(
            &mut rows,
            "https://gh-proxy.com/https://github.com/releases",
            UpdateRoute::Mirror,
            UpdateTransport::Direct,
            UpdateOutcome::Success,
            200,
        );
        let report = snapshot_health(&rows, "2.1.17");
        assert_eq!(report.observations.len(), 2);
        assert_eq!(report.observations[0].status, "http-error");
        assert_eq!(
            report.observations[0].error_code.as_deref(),
            Some("HTTP_403")
        );
        assert_eq!(report.observations[0].transport, "system-proxy");
        assert_eq!(report.observations[1].route, "mirror");
        assert_eq!(report.observations[1].status, "success");
    }

    #[test]
    fn preserves_all_failures_and_timeout_codes() {
        let mut rows = VecDeque::new();
        append(
            &mut rows,
            "https://github.com",
            UpdateRoute::Direct,
            UpdateTransport::Direct,
            UpdateOutcome::Timeout,
            1,
        );
        append(
            &mut rows,
            "https://mirror.example",
            UpdateRoute::Mirror,
            UpdateTransport::Direct,
            UpdateOutcome::NetworkError,
            2,
        );
        let report = snapshot_health(&rows, "v");
        assert_eq!(report.observations.len(), 2);
        assert_eq!(report.observations[0].status, "timeout");
        assert_eq!(
            report.observations[0].error_code.as_deref(),
            Some("TIMEOUT")
        );
        assert_eq!(report.observations[1].status, "network-error");
        assert_eq!(
            report.observations[1].error_code.as_deref(),
            Some("NETWORK_ERROR")
        );
    }

    #[test]
    fn bounded_fifo_retains_only_latest_hundred_attempts() {
        let mut rows = VecDeque::new();
        for at in 0..250 {
            append(
                &mut rows,
                "https://github.com",
                UpdateRoute::Direct,
                UpdateTransport::Direct,
                UpdateOutcome::Success,
                at,
            );
            assert!(rows.len() <= 100);
        }
        assert_eq!(rows.len(), 100);
        assert_eq!(rows.front().unwrap().checked_at, 150);
        assert_eq!(rows.back().unwrap().checked_at, 249);
    }

    #[test]
    fn endpoint_drops_credentials_query_fragment_and_path_tokens() {
        for (input, expected) in [
            (
                "https://alice:password@example.com:8443/token/private?auth=secret#bearer",
                "https://example.com:8443",
            ),
            (
                "https://mirror.example/https://alice:password@github.com/key?token=secret",
                "https://mirror.example",
            ),
            (
                "https://[::1]:8443/private?key=secret",
                "https://[::1]:8443",
            ),
            ("not-a-url password=secret", "[redacted]"),
            ("file:///secret/token", "[redacted]"),
            ("data:text/plain,secret", "[redacted]"),
        ] {
            let mut rows = VecDeque::new();
            append(
                &mut rows,
                input,
                UpdateRoute::Direct,
                UpdateTransport::Direct,
                UpdateOutcome::Success,
                1,
            );
            assert_eq!(rows.front().unwrap().endpoint, expected);
        }
    }

    #[test]
    fn repeated_snapshots_preserve_timestamps_and_cannot_mutate_history() {
        let mut rows = VecDeque::new();
        append(
            &mut rows,
            "https://github.com",
            UpdateRoute::Direct,
            UpdateTransport::Direct,
            UpdateOutcome::Success,
            99,
        );
        let original = snapshot_health(&rows, "2.1.17");
        let mut cached = snapshot_health(&rows, "2.1.17");
        assert_eq!(original, cached);
        cached.observations[0].checked_at = 123;
        assert_eq!(snapshot_health(&rows, "2.1.17"), original);
        assert_eq!(original.observations[0].checked_at, 99);
        assert_eq!(original.container_extensions.status, "unknown");
        assert_eq!(original.container_extensions.reason, "not-probed");
    }

    #[test]
    fn empty_snapshot_is_unknown_without_synthesizing_probe_results() {
        let report = snapshot_health(&VecDeque::new(), "2.1.17");
        assert_eq!(report.workbench_version, "2.1.17");
        assert!(report.observations.is_empty());
        assert_eq!(report.container_extensions.status, "unknown");
        assert_eq!(report.container_extensions.reason, "not-probed");
    }

    #[test]
    fn enormous_duration_saturates_instead_of_wrapping() {
        let mut rows = VecDeque::new();
        append_attempt(
            &mut rows,
            "https://github.com",
            UpdateRoute::Direct,
            UpdateTransport::Direct,
            UpdateOutcome::Success,
            Duration::MAX,
            1,
        );
        assert_eq!(rows.front().unwrap().latency_ms, u64::MAX);
    }
}
