import { describe, expect, it } from "vitest";
import source from "../ExtensionsView.vue?raw";

describe("b13 skill grouping integration", () => {
  it("renders repository groups with batch and child operations", () => {
    expect(source).toContain("store.installedSkillGroups");
    expect(source).toContain("store.marketSkillGroups");
    expect(source).toContain("store.toggleSkillGroup");
    expect(source).toContain("store.updateSkillGroup");
    expect(source).toContain("store.removeSkillGroup");
    expect(source).toContain("store.installSkillGroup");
    expect(source).toContain("store.updateSkill(item)");
  });
});
