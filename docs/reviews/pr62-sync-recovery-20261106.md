# Topic conversation sync recovery — 2026-11-06

PR #62 review found that a complete malformed JSONL record or a record exceeding 1 MiB stopped all later outward-message capture. The provider source remained intact, but repeated synchronization failed at the same offset.

The fix drains oversized records in bounded-memory chunks, advances past complete invalid records, and persists a skipped-record count and last byte offset in the binding. Warnings remain visible on subsequent polls. Records exceeding the capture limit, including large outward text, are not captured; their original source is retained. Partial tails wait for a newline. A known different session marker in unreadable content stops the old binding conservatively, with a diagnostic, rather than attributing later messages to the wrong topic. Marker scanning spans chunk boundaries. Discovery skips oversized unrelated records and continues checking other files; files beyond its existing 32 MiB discovery budget are not scanned.

Validation on Windows / Python 3.12: 9 synthetic recovery probes passed, including normal/idempotent capture, partial tails, malformed JSON, tool output, image records, oversized partial tails, split session markers, discovery and malformed session boundaries. Existing local topic regressions: 18 passed. Tests and synthetic fixtures remain local under the existing publishing constraint; these are local results, not GitHub CI or GUI acceptance.

Integrated develop containing #65. The additive TODO conflict retains both the product target and workflow-documentation topic; #65 is recorded as merged. Original #63/#64 product changes and outstanding GUI/user acceptance are preserved. No installed application or real conversation data was modified.

The head-specific remote checks and final functional acceptance must still be recorded after publication. This repair does not waive the existing stage gates or declare the three product PRs accepted.
