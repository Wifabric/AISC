# Topic conversation sync recovery — 2026-11-06

PR #62 review found that a complete malformed JSONL record or a record exceeding 1 MiB stopped all later outward-message capture. The provider source remained intact, but repeated synchronization failed at the same offset.

The fix drains oversized records in bounded-memory chunks, advances past complete invalid records, and persists a skipped-record count and last byte offset in the binding. Warnings remain visible on subsequent polls. Records exceeding the capture limit, including large outward text, are not captured; their original source is retained. Partial tails wait for a newline. A known different session marker in unreadable content stops the old binding conservatively, with a diagnostic, rather than attributing later messages to the wrong topic. Marker scanning spans chunk boundaries. Discovery skips oversized unrelated records and continues checking other files; files beyond its existing 32 MiB discovery budget are not scanned.

Validation on Windows / Python 3.12: 9 synthetic recovery probes passed, including normal/idempotent capture, partial tails, malformed JSON, tool output, image records, oversized partial tails, split session markers, discovery and malformed session boundaries. Existing local topic regressions: 18 passed. Tests and synthetic fixtures remain local under the existing publishing constraint; these are local results, not GitHub CI or GUI acceptance.

Integrated develop containing #65. The additive TODO conflict retains both the product target and workflow-documentation topic; #65 is recorded as merged. Original #63/#64 product changes and outstanding GUI/user acceptance are preserved. No installed application or real conversation data was modified.

The head-specific remote checks and final functional acceptance must still be recorded after publication. This repair does not waive the existing stage gates or declare the three product PRs accepted.


## Follow-up review and verification

The previous implementation still had three edge cases: EOF without progress after concurrent truncation, a non-object payload reaching marker inspection, and an early marker hidden by a whole-file size filter. The follow-up exits on empty reads, type-checks payload before accessing role, and scans at most the first 32 MiB of each discovery candidate. If no marker is found and scanning was limited, it returns an explicit limit diagnostic; a marker within the scanned prefix can bind even when the full file is larger. The earlier whole-file-skip description above records the superseded implementation.

Validation: original 9 recovery probes PASS; all 3 reported edge-case reproductions PASS; 7 additional checks PASS (payload variants, discovery budget, unrelated large files, duplicate bindings, invalid UTF-8, resume offsets, Codex records). Broader topic Python regressions: 39 PASS and 11 subtests PASS; 6 pre-existing locale deprecation warnings. Topic frontend tests: 32 PASS on production topic modules verified identical to the PR. Local tests and synthetic fixtures remain local under the existing publishing constraint.

Review was performed sequentially by the same agent acting as implementer and reviewer, not an independent person. No remaining blocking finding was identified in this review scope. Head-specific CI must be checked after publication; model/Remote/GUI/user acceptance not exercised here remains outstanding. No product PR is merged by this update. The material-collection mechanism is not added to DEVELOP_WIKI.
