import { describe, expect, it } from "vitest";
import workspaceSource from "../WorkspaceExplorer.vue?raw";

describe("v2.1.16 preview b2 services panel", () => {
  it("embeds host tools in the Services view", () => {
    expect(workspaceSource).toContain("HostToolsServicePanel");
    expect(workspaceSource).not.toContain("settings.group.hostTools");
  });
});
