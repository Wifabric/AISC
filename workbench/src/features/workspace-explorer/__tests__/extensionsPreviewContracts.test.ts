import { describe, expect, it } from "vitest";
import extensionsSource from "../ExtensionsView.vue?raw";
import workspaceSource from "../WorkspaceExplorer.vue?raw";

describe("v2.1.16 preview b1 extension layout contracts", () => {
  it("makes extension content shrink with the sidebar width", () => {
    expect(extensionsSource).toContain(".extensions-view { display: flex; flex-direction: column; min-width: 0; width: 100%; box-sizing: border-box;");
    expect(extensionsSource).toContain(".extensions-card, .market-hit { width: 100%; min-width: 0; box-sizing: border-box; }");
    expect(extensionsSource).toContain(".ext-row { display: flex; align-items: center; gap: 6px; min-height: 28px; width: 100%; min-width: 0;");
  });

  it("hides the file search box on provider and extensions views", () => {
    expect(workspaceSource).toContain(`artifactFilter !== 'services' && artifactFilter !== 'work-records' && artifactFilter !== 'providers' && artifactFilter !== 'extensions'`);
  });

  it("clears each market result when its query is blank", () => {
    expect(extensionsSource).toContain(`watch(skillQuery`);
    expect(extensionsSource).toContain(`watch(mcpQuery`);
    expect(extensionsSource).toContain(`watch(pluginQuery`);
    expect(extensionsSource).toContain(`store.clearMarketResults`);
  });

  it("renders one stable operation progress surface with completed and total counts", () => {
    expect(extensionsSource).toContain(`data-testid="ext-operation-progress"`);
    expect(extensionsSource).toContain(`store.activeOperation`);
    expect(extensionsSource).toContain(`completed`);
    expect(extensionsSource).toContain(`total`);
  });
});


describe("v2.1.16 preview b2 extension contracts", () => {
  it("keeps child actions right-aligned and details on their own wrapped line", () => {
    expect(extensionsSource).toContain(".skill-child { flex-wrap: wrap;");
    expect(extensionsSource).toContain(".skill-child .mh-detail { flex: 1 1 100%;");
    expect(extensionsSource).toContain("expandedChildId = expandedChildId === item.id ? null : item.id");
  });

  it("renders one operation progress bar without a duplicate spinner", () => {
    const start = extensionsSource.indexOf('class="operation-progress"');
    const end = extensionsSource.indexOf("</div>", start);
    const block = extensionsSource.slice(start, end);
    expect(block).not.toContain('class="spinner"');
    expect(block).toContain('class="op-progress-track"');
  });
});
