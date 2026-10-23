import { describe, expect, it } from "vitest";
import source from "../Terminal.vue?raw";

describe("b12 codex selection integration", () => {
  it("installs and disposes the Codex mouse-selection bypass", () => {
    expect(source).toContain("createCodexMouseSelectionBypass");
    expect(source).toContain("attachCodexMouseSelection();");
    expect(source).toContain("detachCodexMouseSelection?.();");
    expect(source).toContain(':disabled="!canCopy"');
  });
});
