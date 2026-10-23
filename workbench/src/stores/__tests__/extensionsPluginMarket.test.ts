import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useExtensionsStore } from "../extensions";
import { extensionsCall } from "../../lib/ipc";

vi.mock("../../lib/ipc", () => ({
  extensionsCall: vi.fn(),
}));

const extensionsCallMock = vi.mocked(extensionsCall);

beforeEach(() => {
  setActivePinia(createPinia());
  extensionsCallMock.mockReset();
});

describe("extensions plugin marketplace", () => {
  it("searches the configured Claude plugin marketplaces", async () => {
    extensionsCallMock.mockResolvedValue({
      items: [{ kind: "market-plugin", id: "skill-creator@claude-plugins-official", name: "skill-creator" }],
    });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    await store.searchPlugins("skill creator");

    expect(store.marketPlugins).toHaveLength(1);
    expect(store.marketPlugins[0]?.id).toBe("skill-creator@claude-plugins-official");
    expect(extensionsCallMock).toHaveBeenCalledWith({
      workspace: "e:/projects",
      runtimeId: "00000000-0000-4000-8000-000000000000",
      op: "plugin-search",
      query: "skill creator",
    });
  });

  it("tracks plugin operation progress by item id", async () => {
    let releaseOperation: (() => void) | undefined;
    const operation = new Promise<Record<string, unknown>>((resolve) => {
      releaseOperation = () => resolve({ items: [] });
    });
    extensionsCallMock.mockImplementationOnce(() => operation).mockResolvedValue({ items: [] });
    const store = useExtensionsStore();
    store.setContext("e:/projects", "00000000-0000-4000-8000-000000000000");
    const pending = store.pluginAction("plugin-install", "skill-creator@claude-plugins-official");
    expect(store.opBusyId).toBe("skill-creator@claude-plugins-official");
    releaseOperation?.();
    await pending;
    expect(store.opBusyId).toBeNull();
  });
});
