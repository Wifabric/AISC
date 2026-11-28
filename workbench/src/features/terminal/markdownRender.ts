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

/** Render the parsed blocks to terminal text. Basic readability only: code
 * blocks get dimmed header/footer rules (code lines stay verbatim) and lists
 * get a bullet marker / preserved ordinal. */
export function renderTerminalMarkdown(input: string): string {
  return parseTerminalMarkdown(input)
    .map((block) => {
      if (block.kind === "code") {
        const label = block.lang || "code";
        const header = `${DIM}── ${label} ──${RESET}`;
        const footer = `${DIM}──────${RESET}`;
        return [header, block.code, footer].join("\n");
      }
      if (block.kind === "list") {
        return block.items
          .map((item) =>
            item.ordered
              ? `${item.indent}${item.marker} ${item.text}`
              : `${item.indent}• ${item.text}`,
          )
          .join("\n");
      }
      return block.lines.join("\n");
    })
    .join("\n");
}
