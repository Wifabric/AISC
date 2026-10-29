import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { reactive } from "vue";
import { i18n } from "../../../i18n";
import ExtensionFailureNotice from "../ExtensionFailureNotice.vue";
import type { ExtensionOperationRecord } from "../../../stores/extensions";

let store: ReturnType<typeof makeStore>;
function record(status: ExtensionOperationRecord["status"], id = "op-2"): ExtensionOperationRecord {
  return {
    operationId: id, workspace: "/ws", runtimeId: "rid", kind: "skills",
    action: "update", id: "owner/repo:skill", label: "skill", attempt: 1,
    startedAt: "2026-10-29T10:00:00Z", finishedAt: "2026-10-29T10:00:01Z",
    status, diagnostic: "network timeout",
  };
}
function makeStore() {
  return reactive({
    busy: false,
    operationLog: [] as ExtensionOperationRecord[],
    canRetryOperation: vi.fn(() => true),
    retryOperation: vi.fn(async () => {}),
    copyOperationDiagnostic: vi.fn(() => {}),
  });
}
vi.mock("../../../stores/extensions", () => ({ useExtensionsStore: () => store }));

beforeEach(() => {
  store = makeStore();
  i18n.global.locale.value = "zh-CN";
});

function mountNotice() {
  return mount(ExtensionFailureNotice, { global: { plugins: [i18n] } });
}

describe("ExtensionFailureNotice", () => {
  it("shows only the latest failure without exposing a history list", () => {
    store.operationLog = [record("success", "op-1"), record("failed", "op-2"), record("unknown", "op-3")];
    const wrapper = mountNotice();
    expect(wrapper.text()).toContain("skill");
    expect(wrapper.text()).toContain("network timeout");
    expect(wrapper.findAll("li")).toHaveLength(0);
    expect(wrapper.text()).not.toContain("op-1");
  });

  it("offers retry only for a known retryable failure", async () => {
    store.operationLog = [record("failed")];
    const wrapper = mountNotice();
    await wrapper.get("[data-testid='extension-failure-retry']").trigger("click");
    expect(store.retryOperation).toHaveBeenCalledWith("op-2");
    wrapper.unmount();

    store = makeStore();
    store.operationLog = [record("unknown")];
    const noRetry = mountNotice();
    expect(noRetry.find("[data-testid='extension-failure-retry']").exists()).toBe(false);
    await noRetry.get("[data-testid='extension-failure-copy']").trigger("click");
    expect(store.copyOperationDiagnostic).toHaveBeenCalledWith("op-2");
  });

  it("renders nothing after successful operations only", () => {
    store.operationLog = [record("success")];
    const wrapper = mountNotice();
    expect(wrapper.find("[data-testid='extension-failure']").exists()).toBe(false);
  });
});
