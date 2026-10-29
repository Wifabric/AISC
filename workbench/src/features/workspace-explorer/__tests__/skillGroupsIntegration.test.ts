import { describe, expect, it } from "vitest";
import source from "../ExtensionsView.vue?raw";
import marketSource from "../ExtensionMarketDialog.vue?raw";

describe("b13/R2 skill grouping integration", () => {
  it("renders installed repository groups with batch and child operations", () => {
    expect(source).toContain("store.installedSkillGroups");
    expect(source).toContain("store.toggleSkillGroup");
    expect(source).toContain("store.updateSkillGroup");
    expect(source).toContain("store.removeSkillGroup");
    expect(source).toContain("store.updateSkill(item)");
  });

  it("keeps repository-group installation in the market dialog", () => {
    expect(marketSource).toContain("store.marketSkillGroups");
    expect(marketSource).toContain("store.installSkillGroup(group)");
  });
});
