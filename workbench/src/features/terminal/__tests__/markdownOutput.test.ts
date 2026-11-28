/**
 * D-9 review fix: the production adapter between the live text stream and the
 * b10/b11/b12 render pipeline (markdownOutput.ts). These tests pin the two
 * jobs that make the pipeline user-visible: decoding/ANSI-stripping the
 * buffered text stream, and turning `renderTerminalMarkdown` output into
 * display lines with foldable code headers and located path links.
 */
import { describe, expect, it } from "vitest";
import {
  buildMarkdownLines,
  decodeStreamChunks,
  stripTerminalAnsi,
} from "../markdownOutput";

const SOURCE = [
  "Here is the plan:",
  "",
  "```ts",
  "const x = 1;",
  "console.log(x);",
  "```",
  "",
  "- first item",
  "- opened /root/project/src/file.ts:42",
  "",
  "Done.",
].join("\n");

describe("stripTerminalAnsi", () => {
  it("drops CSI colour and OSC 8 sequences while keeping readable text", () => {
    const raw =
      "\x1b[31mred\x1b[0m\n\x1b]8;;file:src/a.ts\x1b\\src/a.ts\x1b]8;;\x1b\\ end";
    expect(stripTerminalAnsi(raw)).toBe("red\nsrc/a.ts end");
  });

  it("normalizes carriage returns and removes stray control bytes", () => {
    expect(stripTerminalAnsi("a\r\nb\rc\x07")).toBe("a\nb\nc");
  });
});

describe("decodeStreamChunks", () => {
  it("decodes base64 chunks to UTF-8 text", () => {
    const b64 = (s: string) => Buffer.from(s, "utf-8").toString("base64");
    expect(decodeStreamChunks([b64("hello "), b64("world")])).toBe("hello world");
  });

  it("keeps the tail within the byte budget", () => {
    const b64 = (s: string) => Buffer.from(s, "utf-8").toString("base64");
    expect(decodeStreamChunks([b64("AAAA"), b64("BBBB")], 4)).toBe("BBBB");
  });
});

describe("buildMarkdownLines", () => {
  it("marks code headers foldable and keeps the code body visible", () => {
    const lines = buildMarkdownLines(SOURCE);
    const header = lines.find((l) => l.codeIndex === 0);
    expect(header).toBeDefined();
    expect(header!.text).toMatch(/^── ts ──$/);
    expect(header!.folded).toBe(false);
    expect(header!.segments.some((s) => s.kind === "dim")).toBe(true);
    expect(lines.some((l) => l.text === "const x = 1;" && l.codeIndex === null)).toBe(true);
  });

  it("renders lists and turns paths into located link segments", () => {
    const lines = buildMarkdownLines(SOURCE);
    expect(lines.some((l) => l.text === "• first item")).toBe(true);
    const link = lines
      .flatMap((l) => l.segments)
      .find((s) => s.kind === "link");
    expect(link).toBeDefined();
    if (link && link.kind === "link") {
      expect(link.target.path).toBe("/root/project/src/file.ts");
      expect(link.target.line).toBe(42);
      expect(link.uri).toBe("file:///root/project/src/file.ts");
      expect(link.text).toBe("/root/project/src/file.ts:42");
    }
  });

  it("renders # headings and **bold** as bold segments (b18)", () => {
    const lines = buildMarkdownLines("# Plan\n\n**bold** and `code`");
    expect(lines[0]!.segments.some((seg) => seg.kind === "bold" && seg.text === "Plan")).toBe(true);
    const styled = lines.find((l) => l.text.includes("bold"));
    expect(styled!.segments.some((seg) => seg.kind === "bold" && seg.text === "bold")).toBe(true);
    expect(styled!.segments.some((seg) => seg.kind === "dim" && seg.text === "code")).toBe(true);
  });

  it("collapses a folded code block to its summary line", () => {
    const lines = buildMarkdownLines(SOURCE, { folded: new Set([0]) });
    expect(lines.some((l) => l.text === "const x = 1;")).toBe(false);
    const summary = lines.find((l) => l.codeIndex === 0);
    expect(summary!.folded).toBe(true);
    expect(summary!.text).toContain("(2 lines, folded)");
    // surrounding rendering intact
    expect(lines.some((l) => l.text === "• first item")).toBe(true);
    expect(lines.some((l) => l.text === "Done.")).toBe(true);
  });
});
