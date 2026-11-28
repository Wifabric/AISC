/**
 * b10 (D-9) terminal render pipeline - base layer.
 *
 * Engine output -> Markdown "basic readability": fenced code blocks are shown
 * as visually delimited blocks and lists render as lists. Depth is capped
 * here on purpose: no LaTeX and no plugin-style extension point.
 *
 * The parsed block model is the seam b11 (command/code folding) and b12 (path
 * clicks) build on: they consume `parseTerminalMarkdown` and extend the
 * renderer instead of re-parsing engine text.
 *
 * b11 adds folding on top of the `code` block type only: a code block (long
 * command / fenced output) can be collapsed to one summary line. Fold state is
 * caller-owned (`ReadonlySet<number>` of code-block ordinals) so the renderer
 * stays pure; `toggleCodeFold` is the trivial toggle helper. With no fold
 * state the output is byte-identical to the b10 base rendering.
 *
 * b12 adds path clicks on the same seam: paths in `text` lines and list-item
 * text are recognized as targets (with optional `:line` / `:line:col`), a
 * click column can be located back to its target, and an opt-in render mode
 * wraps them in OSC 8 file links. Code blocks stay verbatim; with path links
 * off the output is byte-identical to b10/b11.
 *
 * The live PTY path stays byte passthrough
 * (workspaceRuntime.paneStreams -> Terminal.writeChunks -> term.write);
 * this pure pipeline is where textual engine output is rendered before it is
 * handed to the terminal.
 */

export interface TerminalListItem {
  /** Leading indentation preserved verbatim (nested lists). */
  indent: string;
  ordered: boolean;
  /** Original ordered marker (`1.` / `1)`); empty for bullets. */
  marker: string;
  text: string;
}

export type TerminalMarkdownBlock =
  | { kind: "text"; lines: string[] }
  | { kind: "code"; lang: string; code: string }
  | { kind: "list"; items: TerminalListItem[] };

const DIM = "\x1b[2m";
const RESET = "\x1b[0m";

const FENCE_OPEN = /^\s*```(.*)$/;
const FENCE_CLOSE = /^\s*```\s*$/;
const LIST_ITEM = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;

/**
 * b12: a filesystem path with at least one directory component (posix form),
 * optionally suffixed with `:line` or `:line:column`. Bare filenames and URLs
 * do not match; only matches starting at a token boundary qualify.
 */
const PATH_TARGET =
  /(?:^|(?<=[^\w/.:-]))((?:~\/|\.{1,2}\/|\/)?(?:[\w.@%+-]+\/)+[\w.@%+-]+\.[A-Za-z][\w]*)(?::(\d+))?(?::(\d+))?/g;

/** b12: one recognized path inside a text/list span. */
export interface TerminalPathTarget {
  /** Path text without the `:line[:col]` suffix. */
  path: string;
  /** 1-based target line from a `:line` suffix, when present. */
  line?: number;
  /** 1-based target column from a `:line:col` suffix, when present. */
  column?: number;
  /** Full matched text (path plus any `:line[:col]` suffix). */
  text: string;
  /** 0-based offset where `text` starts in the scanned string. */
  start: number;
  /** 0-based offset just past `text` (exclusive). */
  end: number;
}

/** Find clickable path targets in one text/list span. */
export function findTerminalPathTargets(text: string): TerminalPathTarget[] {
  const re = new RegExp(PATH_TARGET.source, "g");
  const targets: TerminalPathTarget[] = [];
  for (const match of text.matchAll(re)) {
    const start = match.index ?? 0;
    targets.push({
      path: match[1],
      line: match[2] === undefined ? undefined : Number(match[2]),
      column: match[3] === undefined ? undefined : Number(match[3]),
      text: match[0],
      start,
      end: start + match[0].length,
    });
  }
  return targets;
}

/** b12 click locate: the path target under a 0-based column, or null. */
export function locateTerminalPath(
  text: string,
  column: number,
): TerminalPathTarget | null {
  return (
    findTerminalPathTargets(text).find(
      (target) => column >= target.start && column < target.end,
    ) ?? null
  );
}

/** b12: wrap path targets in an OSC 8 file link. Absolute paths become
 * `file://<path>`; relative paths stay `file:<path>` for the UI to resolve
 * against its workspace root. The visible text (including `:line:col`) is
 * unchanged. */
function linkTerminalPaths(line: string): string {
  const targets = findTerminalPathTargets(line);
  if (targets.length === 0) return line;
  let result = "";
  let cursor = 0;
  for (const target of targets) {
    const uri = target.path.startsWith("/")
      ? `file://${target.path}`
      : `file:${target.path}`;
    result += line.slice(cursor, target.start);
    result += `\x1b]8;;${uri}\x1b\\${target.text}\x1b]8;;\x1b\\`;
    cursor = target.end;
  }
  return result + line.slice(cursor);
}

/** Split engine output into prose, fenced-code and list blocks. Unterminated
 * fences (a live stream cut mid-block) are treated as code to the end. */
export function parseTerminalMarkdown(input: string): TerminalMarkdownBlock[] {
  const lines = input.split(/\r?\n/);
  const blocks: TerminalMarkdownBlock[] = [];
  let i = 0;

  while (i < lines.length) {
    const fence = FENCE_OPEN.exec(lines[i]);
    if (fence) {
      const lang = fence[1].trim().split(/\s+/)[0] ?? "";
      const code: string[] = [];
      i++;
      while (i < lines.length && !FENCE_CLOSE.test(lines[i])) {
        code.push(lines[i]);
        i++;
      }
      if (i < lines.length) i++; // consume the closing fence
      blocks.push({ kind: "code", lang, code: code.join("\n") });
      continue;
    }

    const item = LIST_ITEM.exec(lines[i]);
    if (item) {
      const items: TerminalListItem[] = [];
      while (i < lines.length) {
        const m = LIST_ITEM.exec(lines[i]);
        if (!m) break;
        items.push({
          indent: m[1],
          ordered: /^\d/.test(m[2]),
          marker: /^\d/.test(m[2]) ? m[2] : "",
          text: m[3],
        });
        i++;
      }
      blocks.push({ kind: "list", items });
      continue;
    }

    const text: string[] = [];
    while (i < lines.length && !FENCE_OPEN.test(lines[i]) && !LIST_ITEM.test(lines[i])) {
      text.push(lines[i]);
      i++;
    }
    blocks.push({ kind: "text", lines: text });
  }

  return blocks;
}

/** b11 fold state: ordinals (0-based, among `code` blocks) of folded blocks;
 * b12 path links: wrap recognized paths in text/list spans with OSC 8 links. */
export interface TerminalRenderOptions {
  folded?: ReadonlySet<number>;
  pathLinks?: boolean;
}

/** Toggle one code block's fold state, returning a new set (input untouched). */
export function toggleCodeFold(
  folded: ReadonlySet<number>,
  codeBlockIndex: number,
): Set<number> {
  const next = new Set(folded);
  if (next.has(codeBlockIndex)) next.delete(codeBlockIndex);
  else next.add(codeBlockIndex);
  return next;
}

/** Render the parsed blocks to terminal text. Basic readability only: code
 * blocks get dimmed header/footer rules (code lines stay verbatim) and lists
 * get a bullet marker / preserved ordinal. Folded code blocks (b11) collapse
 * to a single dim summary line. */
export function renderTerminalMarkdown(
  input: string,
  options: TerminalRenderOptions = {},
): string {
  const folded = options.folded ?? new Set<number>();
  const pathLinks = options.pathLinks ?? false;
  let codeBlockIndex = -1;
  return parseTerminalMarkdown(input)
    .map((block) => {
      if (block.kind === "code") {
        codeBlockIndex++;
        const label = block.lang || "code";
        if (folded.has(codeBlockIndex)) {
          const count = block.code === "" ? 0 : block.code.split("\n").length;
          const lines = `${count} line${count === 1 ? "" : "s"}`;
          return `${DIM}── ${label} (${lines}, folded) ──${RESET}`;
        }
        const header = `${DIM}── ${label} ──${RESET}`;
        const footer = `${DIM}──────${RESET}`;
        return [header, block.code, footer].join("\n");
      }
      if (block.kind === "list") {
        return block.items
          .map((item) => {
            const text = pathLinks ? linkTerminalPaths(item.text) : item.text;
            return item.ordered
              ? `${item.indent}${item.marker} ${text}`
              : `${item.indent}• ${text}`;
          })
          .join("\n");
      }
      return pathLinks ? block.lines.map(linkTerminalPaths).join("\n") : block.lines.join("\n");
    })
    .join("\n");
}
