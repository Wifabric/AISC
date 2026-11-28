/**
 * D-9 review fix: MarkdownOutputView renders the display lines built from the
 * b10/b11/b12 pipeline as real DOM — code blocks with clickable fold headers,
 * list bullets, and clickable path links. Clicking a header emits
 * `toggle-fold`; clicking a path emits `open-path` with the located target.
 */
import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import MarkdownOutputView from "../MarkdownOutputView.vue";
import { buildMarkdownLines } from "../markdownOutput";
import type { TerminalPathTarget } from "../markdownRender";

const SOURCE = [
  "Plan:",
  "```ts",
  "const x = 1;",
  "```",
  "- first item",
  "- opened /root/project/src/file.ts:42",
].join("\n");

describe("MarkdownOutputView", () => {
  it("renders a code block and a list item", () => {
    const wrapper = mount(MarkdownOutputView, {
      props: { lines: buildMarkdownLines(SOURCE) },
    });
    expect(wrapper.find('[data-testid="markdown-output"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("const x = 1;");
    expect(wrapper.text()).toContain("── ts ──");
    expect(wrapper.text()).toContain("• first item");
    wrapper.unmount();
  });

  it("emits toggle-fold when a code header is clicked", async () => {
    const wrapper = mount(MarkdownOutputView, {
      props: { lines: buildMarkdownLines(SOURCE) },
    });
    const header = wrapper.get('[data-testid="md-code-header"]');
    await header.trigger("click");
    expect(wrapper.emitted("toggle-fold")).toEqual([[0]]);
    wrapper.unmount();
  });

  it("renders folded output without the code body", () => {
    const wrapper = mount(MarkdownOutputView, {
      props: { lines: buildMarkdownLines(SOURCE, { folded: new Set([0]) }) },
    });
    expect(wrapper.text()).not.toContain("const x = 1;");
    expect(wrapper.text()).toContain("(1 line, folded)");
    expect(wrapper.get('[data-testid="md-code-header"]').text()).toContain("▸");
    wrapper.unmount();
  });

  it("renders paths as clickable links and emits open-path with the target", async () => {
    const wrapper = mount(MarkdownOutputView, {
      props: { lines: buildMarkdownLines(SOURCE) },
    });
    const link = wrapper.get('[data-testid="md-path-link"]');
    expect(link.text()).toBe("/root/project/src/file.ts:42");
    expect(link.attributes("href")).toBe("file:///root/project/src/file.ts");
    await link.trigger("click");
    const emitted = wrapper.emitted("open-path");
    expect(emitted).toBeTruthy();
    const target = emitted![0][0] as TerminalPathTarget;
    expect(target.path).toBe("/root/project/src/file.ts");
    expect(target.line).toBe(42);
    wrapper.unmount();
  });
});
