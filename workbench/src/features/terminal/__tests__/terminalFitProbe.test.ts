import { describe, expect, it } from "vitest";
import source from "../Terminal.vue?raw";

describe("b16 terminal fit diagnostic removal", () => {
  it("does not auto-open the screenshot-feedback fit probe", () => {
    expect(source).not.toContain("fitDiagOpen");
    expect(source).not.toContain("fit 诊断");
    expect(source).not.toContain("gridChanges");
    expect(source).not.toContain(".fit-diag");
  });
});
