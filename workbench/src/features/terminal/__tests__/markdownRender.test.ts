/**
 * b10 (D-9) terminal render pipeline: engine output -> Markdown basic
 * readability. Scope is deliberately narrow - fenced code blocks render as
 * blocks and lists as lists. b11 (folding) / b12 (path clicks) build on the
 * parsed block model, so the parser and renderer are separate seams.
 */
import { describe, expect, it } from "vitest";
import {
  findTerminalPathTargets,
  locateTerminalPath,
  parseTerminalMarkdown,
  renderTerminalMarkdown,
  toggleCodeFold,
} from "../markdownRender";

const stripAnsi = (s: string): string => s.replace(/\x1b\[[0-9;]*m/g, "");

const ENGINE_OUTPUT = [
  "Here is the plan:",
  "",
  "```ts",
  "const x = 1;",
  "console.log(x);",
  "```",
  "",
  "- first item",
  "- second item",
  "",
  "1. ordered one",
  "2. ordered two",
  "",
  "Done.",
].join("\n");

describe("parseTerminalMarkdown (b10)", () => {
  it("separates fenced code and list blocks from prose", () => {
    const blocks = parseTerminalMarkdown(ENGINE_OUTPUT);
    expect(blocks.map((b) => b.kind)).toEqual([
      "text", "code", "text", "list", "text", "list", "text",
    ]);
    expect(blocks[1]).toMatchObject({
      kind: "code",
      lang: "ts",
      code: "const x = 1;\nconsole.log(x);",
    });
    expect(blocks[3].kind).toBe("list");
    if (blocks[3].kind === "list") {
      expect(blocks[3].items.map((i) => i.text)).toEqual(["first item", "second item"]);
      expect(blocks[3].items.every((i) => !i.ordered)).toBe(true);
    }
    expect(blocks[5].kind).toBe("list");
    if (blocks[5].kind === "list") {
      expect(blocks[5].items.map((i) => `${i.marker} ${i.text}`)).toEqual([
        "1. ordered one",
        "2. ordered two",
      ]);
      expect(blocks[5].items.every((i) => i.ordered)).toBe(true);
    }
  });
});

describe("renderTerminalMarkdown (b10)", () => {
  const out = stripAnsi(renderTerminalMarkdown(ENGINE_OUTPUT));
  const lines = out.split("\n");

  it("renders a fenced code block as a preserved block", () => {
    expect(out).not.toContain("```");
    expect(out).toContain("const x = 1;");
    expect(out).toContain("console.log(x);");
    const firstCode = lines.findIndex((l) => l.includes("const x = 1;"));
    expect(lines[firstCode - 1]).toMatch(/^── ts/); // block header (dimmed in real output)
    expect(lines[firstCode + 1]).toBe("console.log(x);"); // code lines stay verbatim
    expect(lines[firstCode + 2]).toMatch(/^──/); // block footer
  });

  it("renders list items as list items", () => {
    expect(out).toContain("• first item");
    expect(out).toContain("• second item");
    expect(out).toContain("1. ordered one");
    expect(out).toContain("2. ordered two");
  });

  it("leaves surrounding prose untouched", () => {
    expect(out).toContain("Here is the plan:");
    expect(out).toContain("Done.");
  });
});

/**
 * b11 (D-9 sub-goal 2) command/code folding: builds on the b10 block model.
 * A code block (fenced command/code output) can be folded to a single summary
 * line and unfolded back to its full content. Fold state is a pure
 * `ReadonlySet<number>` of code-block ordinals, so the renderer stays a pure
 * function and toggling is a small helper. Folding must not disturb the
 * surrounding prose/list/code rendering.
 */
describe("command folding (b11)", () => {
  const LONG_COMMAND = [
    "Running the migration:",
    "```bash",
    "pnpm db:migrate --from 20240101 --to 20241231 --verbose \\",
    "  --confirm --backup --no-interactive",
    "```",
    "- background job queued",
    "Done.",
  ].join("\n");

  it("folds a long code block to a summary line while keeping surrounding rendering", () => {
    const folded = stripAnsi(
      renderTerminalMarkdown(LONG_COMMAND, { folded: new Set([0]) }),
    );
    // collapsed body is gone
    expect(folded).not.toContain("pnpm db:migrate");
    expect(folded).not.toContain("--no-interactive");
    // a single summary line replaces the block
    expect(folded).toContain("── bash (2 lines, folded) ──");
    expect(folded.split("\n").filter((l) => l.includes("──")).length).toBe(1);
    // surrounding base rendering is intact
    expect(folded).toContain("Running the migration:");
    expect(folded).toContain("• background job queued");
    expect(folded).toContain("Done.");
  });

  it("unfolds back to the full base rendering", () => {
    const folded = toggleCodeFold(new Set<number>(), 0);
    expect(folded.has(0)).toBe(true);
    const unfolded = toggleCodeFold(folded, 0);
    expect(unfolded.has(0)).toBe(false);

    const out = stripAnsi(renderTerminalMarkdown(LONG_COMMAND, { folded: unfolded }));
    expect(out).toContain("── bash ──");
    expect(out).toContain("pnpm db:migrate --from 20240101 --to 20241231 --verbose \\");
    expect(out).toContain("  --confirm --backup --no-interactive");
    expect(out).toContain("• background job queued");
    expect(out).toContain("Done.");
    // byte-for-byte equivalent to the b10 default render
    expect(out).toBe(stripAnsi(renderTerminalMarkdown(LONG_COMMAND)));
  });

  it("folds only the selected code block and leaves the default render unchanged", () => {
    const twoBlocks = [
      "```sh",
      "echo one",
      "```",
      "middle",
      "```sh",
      "echo two",
      "```",
    ].join("\n");
    const out = stripAnsi(renderTerminalMarkdown(twoBlocks, { folded: new Set([1]) }));
    expect(out).toContain("echo one"); // first block untouched
    expect(out).not.toContain("echo two"); // second block folded
    expect(out).toContain("── sh (1 line, folded) ──");
    expect(out).toContain("middle");

    // no fold state -> b10 base rendering preserved
    const base = stripAnsi(renderTerminalMarkdown(twoBlocks));
    expect(base).toContain("── sh ──");
    expect(base).toContain("echo one");
    expect(base).toContain("echo two");
    expect(base).not.toContain("folded");
  });
});

/**
 * b12 (D-9 sub-goal 3) path clicks: builds on the b10 block model. Paths in
 * `text` lines and list-item text are recognized and can be rendered as
 * terminal-clickable targets (OSC 8 file links); a click column can be
 * located back to its target. Paths inside code blocks stay verbatim, and
 * with path links off the output is byte-identical to the b10/b11 rendering.
 */
describe("path clicks (b12)", () => {
  const PATH_OUTPUT = [
    "Wrote /root/project/src/file.ts:42 and then",
    "- opened src/aisc/x.py:10",
    "```ts",
    "const p = 'src/not/a/link.ts:1';",
    "```",
    "Done.",
  ].join("\n");

  const stripLinks = (s: string): string => s.replace(/\x1b\]8;;[^\x1b]*\x1b\\/g, "");

  it("recognizes paths and their locate info in text and list spans", () => {
    const abs = findTerminalPathTargets("Wrote /root/project/src/file.ts:42 and then");
    expect(abs).toHaveLength(1);
    expect(abs[0]).toMatchObject({
      path: "/root/project/src/file.ts",
      line: 42,
      text: "/root/project/src/file.ts:42",
    });

    const rel = findTerminalPathTargets("opened src/aisc/x.py:10");
    expect(rel).toHaveLength(1);
    expect(rel[0]).toMatchObject({ path: "src/aisc/x.py", line: 10 });

    // no false positive on prose that is not a path
    expect(findTerminalPathTargets("opened myfile.ts and done")).toEqual([]);
  });

  it("renders text/list paths as clickable OSC 8 file targets", () => {
    const out = renderTerminalMarkdown(PATH_OUTPUT, { pathLinks: true });
    expect(out).toContain("\x1b]8;;file:///root/project/src/file.ts\x1b\\");
    expect(out).toContain("\x1b]8;;file:src/aisc/x.py\x1b\\");
    // the visible text keeps the :line suffix
    expect(stripLinks(out)).toContain("/root/project/src/file.ts:42");
    expect(stripLinks(out)).toContain("• opened src/aisc/x.py:10");
    // code block spans stay verbatim and surrounding prose is intact
    expect(stripLinks(out)).toContain("const p = 'src/not/a/link.ts:1';");
    expect(stripLinks(out)).toContain("Done.");
  });

  it("keeps the default render byte-identical and locates a click column", () => {
    const base = renderTerminalMarkdown(PATH_OUTPUT);
    expect(base).not.toContain("\x1b]8;;");
    expect(stripLinks(renderTerminalMarkdown(PATH_OUTPUT, { pathLinks: false }))).toBe(base);

    const line = "Wrote /root/project/src/file.ts:42 and then";
    const start = line.indexOf("/root/project");
    expect(locateTerminalPath(line, start + 3)).toMatchObject({
      path: "/root/project/src/file.ts",
      line: 42,
    });
    expect(locateTerminalPath(line, start - 1)).toBeNull();
    expect(locateTerminalPath(line, line.length - 1)).toBeNull();
  });
});
