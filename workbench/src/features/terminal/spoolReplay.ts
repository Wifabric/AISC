/**
 * P1-2 (2.1.11): linearize a spool page for history replay.
 *
 * The raw PTY stream carries full-screen choreography — scroll-down
 * (`CSI n T`) inserts blank lines, ED/CUP redraw whole regions, alt-screen
 * switches move content into a buffer the scrollback never shows. Live,
 * those sequences paint a viewport; replayed over a long scrollback they
 * leave big bands of never-written blank lines (measured: 100×`CSI 10 T`
 * ⇒ a 199-line band — the reported "big blank area at the top").
 *
 * This filter rewrites a replayed page into a linear log: every redraw
 * round appends instead of repositioning. SGR (colors) and EL
 * (in-line erase) survive; screen-level geometry does not.
 *
 * Byte-oriented on purpose: ESC sequences are pure ASCII, so UTF-8
 * multibyte payload (any byte ≥ 0x80) passes through untouched.
 *
 * 批 8 hand-test revision (2026-09-21): CUU/CUD/RI used to degrade to a
 * line feed — TUI redraw rounds move the cursor tens of times per refresh,
 * so 1 MiB of dense TUI stream injected thousands of blank lines. Cursor
 * moves now drop entirely; the CR that follows a move in every real
 * redraw still rewrites the line in place, so redraw rounds collapse with
 * no line-count inflation. `alignSpoolPage` complements this: byte-offset
 * paging can split UTF-8 and CSI sequences mid-body, and orphan head/tail
 * bytes rendered as garbage — it trims both ends to sequence boundaries.
 */

const ESC = 0x1b;

export function linearizeSpoolPage(data: Uint8Array): Uint8Array {
  const out = new Uint8Array(data.length + 64); // worst case: A/B grow by ≤ 1 byte per sequence
  let w = 0;
  let i = 0;
  const n = data.length;

  while (i < n) {
    const b = data[i];
    if (b !== ESC) {
      if (w < out.length) out[w++] = b;
      i++;
      continue;
    }
    // ESC seen — parse a CSI sequence: ESC [ <params(ASCII) > <final byte>
    if (i + 1 >= n || data[i + 1] !== 0x5b /* [ */) {
      // Two-byte escape (ESC 7/8/D/M …) — drop cursor ops, keep the byte
      // count moving. ESC M (RI) is a scroll-shape op: degrade to LF.
      // ESC M (RI): drop — same phantom-line source as CUU (批 8 revision).
      i += 2;
      continue;
    }
    // CSI: scan params/intermediates to the final byte.
    let j = i + 2;
    while (j < n && data[j] >= 0x20 && data[j] <= 0x2f) j++; // intermediates
    let end = j;
    while (end < n && !(data[end] >= 0x40 && data[end] <= 0x7e)) end++;
    if (end >= n) break; // truncated tail — nothing more to do
    const final = data[end];
    const paramStart = j;
    const paramText = String.fromCharCode(
      ...Array.from(data.subarray(paramStart, end)).filter((c) => c >= 0x30 && c <= 0x3f),
    );
    const isPrivate = paramText.includes("?");

    const copySeq = (): void => {
      for (let k = i; k <= end; k++) {
        if (w < out.length) out[w++] = data[k];
      }
    };

    switch (final) {
      // Screen geometry — strip entirely (this is the blank-band source).
      case 0x54: // CSI n T — scroll down: THE big blank injector
      case 0x53: // CSI n S — scroll up
      case 0x4a: // CSI n J — erase display
      case 0x48: // CSI r;c H — cursor position
      case 0x66: // CSI r;c f — HVP
      case 0x72: // CSI t;b r — DECSTBM scroll region
        break;
      // Cursor up/down — DROP (批 8 hand-test revision). Degrading to LF
      // injected one phantom line per move; a TUI refresh round moves up
      // tens of times, so paged replay grew thousands of blanks. Real
      // redraws follow the move with CR + overwrite, which still lands on
      // the current visual line — rounds collapse, no inflation.
      case 0x41: // CUU
      case 0x42: // CUD
        break;
      // Alt-screen toggles — strip: replay must stay in the normal buffer.
      case 0x68: // DECSET
      case 0x6c: // DECRST
        if (isPrivate && /^(1049|47|1047|1048)$/.test(paramText.replace("?", ""))) {
          break; // stripped
        }
        copySeq();
        break;
      // Everything else (SGR `m`, EL `K`, etc.) — keep verbatim.
      default:
        copySeq();
        break;
    }

    i = end + 1;
  }
  return out.subarray(0, w);
}

/**
 * 批 8 hand-test: byte-offset paging can split a page MID-SEQUENCE —
 * `from` may land inside a UTF-8 char or a CSI body, and the orphan bytes
 * render as garbage at the page head (a UTF-8 char cut at the tail decodes
 * to U+FFFD noise). Trim both ends to safe boundaries:
 * - head: skip UTF-8 continuation bytes, then swallow an orphan CSI
 *   fragment (parameter bytes with no leading ESC) up to and including
 *   its final byte;
 * - tail: drop a trailing incomplete UTF-8 char.
 * A truncated CSI at the tail is already discarded by the linearizer.
 */
export function alignSpoolPage(data: Uint8Array): Uint8Array {
  const n = data.length;
  let start = 0;
  while (start < n && start < 3 && data[start] >= 0x80 && data[start] <= 0xbf) {
    start++;
  }
  if (start >= n) return data.subarray(0, 0);
  if (data[start] >= 0x30 && data[start] <= 0x3f) {
    let j = start;
    while (j < n && j - start < 16 && data[j] >= 0x30 && data[j] <= 0x3f) j++;
    if (j < n && data[j] >= 0x40 && data[j] <= 0x7e) {
      start = j + 1;
    }
  }
  let end = n;
  if (end > start) {
    const last = data[end - 1];
    if (last >= 0x80 && last <= 0xbf) {
      let k = end - 1;
      while (k > start && end - k <= 3 && data[k] >= 0x80 && data[k] <= 0xbf) k--;
      if (k >= start && data[k] >= 0xc0) {
        const lead = data[k];
        const expected = lead >= 0xf0 ? 4 : lead >= 0xe0 ? 3 : 2;
        if (end - k < expected) end = k;
      } else {
        end = k + 1;
      }
    }
  }
  return data.subarray(start, end);
}
