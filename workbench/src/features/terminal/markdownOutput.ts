/**
 * D-9 review fix: production seam for the b10/b11/b12 render pipeline.
 *
 * The live PTY path stays byte passthrough
 * (`workspaceRuntime.paneStreams -> Terminal.writeChunks -> term.write`) so
 * TUI/ANSI sessions are never re-parsed. When the user turns on a pane's
 * Markdown view we instead decode the SAME buffered text stream, drop the
 * terminal control sequences, and run it through `renderTerminalMarkdown`
 * (b10), `toggleCodeFold` (b11) and `pathLinks` (b12). This module turns that
 * rendered terminal string into plain display lines the Vue view renders with
 * real DOM affordances (foldable code headers, clickable paths).
 */
import {
  locateTerminalPath,
  renderTerminalMarkdown,
  type TerminalPathTarget,
  type TerminalRenderOptions,
} from "./markdownRender";

export interface MarkdownTextSegment {
  kind: "text" | "dim" | "bold";
  text: string;
}

export interface MarkdownLinkSegment {
  kind: "link";
  text: string;
  /** OSC 8 target emitted by `pathLinks` (`file:` / `file://…`). */
  uri: string;
  target: TerminalPathTarget;
}

export type MarkdownSegment = MarkdownTextSegment | MarkdownLinkSegment;

export interface MarkdownRenderedLine {
  /** Code-block ordinal when this line is a foldable code header/summary. */
  codeIndex: number | null;
  /** Whether the code block at `codeIndex` is currently folded. */
  folded: boolean;
  segments: MarkdownSegment[];
  /** Visible text with ANSI/OSC control sequences removed. */
  text: string;
}

/** A code header (`── ts ──`) or fold summary (`── ts (N lines, folded) ──`).
 * The footer (`──────`) has no space and never matches. */
const CODE_HEADER_LINE = /^── .+ ──$/;

const CSI_RE = /\x1b\[[0-9;?]*[ -/]*[@-~]/g;
const OSC_RE = /\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)/g;
/** Two-byte / charset escapes left over after CSI+OSC (e.g. ESC ( B). */
const ESC_TWO_RE = /\x1b[()#][0-9A-Za-z]|\x1b[@-_]/g;
/** C0 controls except \n and \t, plus DEL. */
const CONTROL_RE = /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g;

/** Strip terminal control sequences from a text stream, keeping the readable
 * characters. `\r\n` collapses to `\n`; lone `\r` (progress redraws) becomes a
 * newline so the text view does not overwrite lines. */
export function stripTerminalAnsi(text: string): string {
  return text
    .replace(OSC_RE, "")
    .replace(CSI_RE, "")
    .replace(ESC_TWO_RE, "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(CONTROL_RE, "");
}

function b64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return u8;
}

/** Decoded byte length of one base64 chunk, accounting for `=` padding. */
function b64DecodedLength(b64: string): number {
  let pad = 0;
  if (b64.endsWith("==")) pad = 2;
  else if (b64.endsWith("=")) pad = 1;
  return Math.floor((b64.length / 4) * 3) - pad;
}

/** Decode the tail of a pane's buffered base64 chunks as UTF-8 text, keeping
 * at most `maxBytes` so a long session does not rebuild the entire view on
 * every refresh. */
export function decodeStreamChunks(chunks: string[], maxBytes = 512 * 1024): string {
  let total = 0;
  let start = chunks.length;
  while (start > 0) {
    const n = b64DecodedLength(chunks[start - 1]);
    if (total + n > maxBytes && total > 0) break;
    total += n;
    start--;
  }
  const bytes = new Uint8Array(total);
  let off = 0;
  for (let i = start; i < chunks.length; i++) {
    const u8 = b64ToBytes(chunks[i]);
    bytes.set(u8, off);
    off += u8.length;
  }
  return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
}

/** Split one rendered line into dim / plain / OSC 8 link segments. */
function parseSegments(line: string): MarkdownSegment[] {
  const segments: MarkdownSegment[] = [];
  let buf = "";
  let dim = false;
  let bold = false;
  let linkUri: string | null = null;
  let linkText = "";

  const flush = (): void => {
    if (!buf) return;
    if (linkUri !== null) linkText += buf;
    else segments.push({ kind: bold ? "bold" : dim ? "dim" : "text", text: buf });
    buf = "";
  };

  let i = 0;
  while (i < line.length) {
    if (line[i] !== "\x1b") {
      buf += line[i];
      i++;
      continue;
    }
    if (line.startsWith("\x1b]8;;", i)) {
      const bodyStart = i + 5;
      const end = line.indexOf("\x1b\\", bodyStart);
      if (end >= 0) {
        flush();
        const uri = line.slice(bodyStart, end);
        if (linkUri === null) {
          linkUri = uri;
          linkText = "";
        } else {
          const target = locateTerminalPath(linkText, 0);
          if (target) {
            segments.push({ kind: "link", text: linkText, uri: linkUri, target });
          } else {
            segments.push({ kind: "text", text: linkText });
          }
          linkUri = null;
          linkText = "";
        }
        i = end + 2;
        continue;
      }
    }
    const sgr = /^\x1b\[([0-9;]*)m/.exec(line.slice(i));
    if (sgr) {
      flush();
      const codes = sgr[1].split(";");
      if (codes.includes("0")) { dim = false; bold = false; }
      else { if (codes.includes("2")) dim = true; if (codes.includes("1")) bold = true; }
      i += sgr[0].length;
      continue;
    }
    i += 2; // unknown escape: skip ESC + one byte
  }
  flush();
  if (linkUri !== null && linkText) segments.push({ kind: "text", text: linkText });
  return segments;
}

/** Render engine text into display lines. Code headers/summaries carry the
 * code-block ordinal (click to toggle via `toggleCodeFold`); paths in text and
 * list spans become `link` segments with their located target. */
export function buildMarkdownLines(
  source: string,
  options: TerminalRenderOptions = {},
): MarkdownRenderedLine[] {
  const folded = options.folded ?? new Set<number>();
  const rendered = renderTerminalMarkdown(source, {
    folded,
    pathLinks: options.pathLinks ?? true,
  });
  let codeIndex = -1;
  return rendered.split("\n").map((raw) => {
    const segments = parseSegments(raw);
    const text = segments.map((s) => s.text).join("");
    let index: number | null = null;
    if (CODE_HEADER_LINE.test(text)) {
      codeIndex++;
      index = codeIndex;
    }
    return {
      codeIndex: index,
      folded: index !== null && folded.has(index),
      segments,
      text,
    };
  });
}
