import { describe, expect, it } from "vitest";
import extensionsSource from "../ExtensionsView.vue?raw";
import marketSource from "../ExtensionMarketDialog.vue?raw";
import workspaceSource from "../WorkspaceExplorer.vue?raw";

describe("v2.1.17 R2 extension layout contracts", () => {
  it("keeps installed content shrinkable with the sidebar width", () => {
    expect(extensionsSource).toContain(".extensions-view { display: flex; flex-direction: column; min-width: 0; width: 100%; box-sizing: border-box;");
    expect(extensionsSource).toContain(".extensions-card { width: 100%; min-width: 0; box-sizing: border-box;");
    expect(extensionsSource).toContain(".ext-row { display: flex; align-items: center; gap: 6px;");
  });

  it("hides the file search box on provider and extensions views", () => {
    expect(workspaceSource).toContain(
      `artifactFilter !== 'services' && artifactFilter !== 'work-records' && artifactFilter !== 'providers' && artifactFilter !== 'extensions'`,
    );
  });

  it("moves discovery and history out of the installed view", () => {
    expect(extensionsSource).not.toContain("ExtensionRecommendations");
    expect(extensionsSource).not.toContain("ExtensionOperationLog");
    expect(extensionsSource).not.toContain("extensions-market");
    expect(extensionsSource).toContain("ExtensionMarketDialog");
    expect(extensionsSource).toContain("ExtensionFailureNotice");
    expect(extensionsSource).toContain("ExtensionDetailPanel");
  });

  it("renders one stable operation progress surface with completed and total counts", () => {
    expect(extensionsSource).toContain(`data-testid="ext-operation-progress"`);
    expect(extensionsSource).toContain("store.activeOperation");
    expect(extensionsSource).toContain("completed");
    expect(extensionsSource).toContain("total");
    const start = extensionsSource.indexOf('class="operation-progress"');
    const end = extensionsSource.indexOf("</div>", start);
    const block = extensionsSource.slice(start, end);
    expect(block).not.toContain('class="spinner"');
    expect(block).toContain('class="op-progress-track"');
  });

  it("keeps the market dialog usable at narrow widths", () => {
    expect(marketSource).toContain("grid-template-columns: minmax(0, 1fr) 300px");
    expect(marketSource).toContain("@media (max-width: 720px)");
    expect(marketSource).toContain("grid-template-columns: 1fr");
    expect(marketSource).toContain("role=\"dialog\"");
    expect(marketSource).toContain("aria-modal=\"true\"");
  });
});
