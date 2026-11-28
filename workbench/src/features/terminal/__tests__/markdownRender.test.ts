/**
 * b10 (D-9) terminal render pipeline: engine output -> Markdown basic
 * readability. Scope is deliberately narrow - fenced code blocks render as
 * blocks and lists as lists. b11 (folding) / b12 (path clicks) build on the
 * parsed block model, so the parser and renderer are separate seams.
 */
import { describe, expect, it } from "vitest";
import { parseTerminalMarkdown, renderTerminalMarkdown } from "../markdownRender";

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
