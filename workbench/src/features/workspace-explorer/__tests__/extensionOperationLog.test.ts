import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick, reactive, type Component } from "vue";
import { i18n } from "../../../i18n";

interface LogRow {
  operationId: string;
  kind: "skills" | "mcp" | "plugins";
  action: "install" | "update" | "remove";
  id: string;
  label: string;
  attempt: number;
  startedAt: string;
  finishedAt: string;
  status: "success" | "failed" | "unknown";
  diagnostic: string;
}

function row(status: LogRow["status"], extra: Partial<LogRow> = {}): LogRow {
  return {
    operationId: status, kind: "skills", action: "install", id: "o/r:skill",
    label: "Example skill", attempt: 2, startedAt: "2026-10-27T10:00:00Z",
    finishedAt: "2026-10-27T10:00:05Z", status,
    diagnostic: "direct: failed\nmirror: HTTP 502", ...extra,
  };
}

function makeStore() {
  return reactive({
    operationLog: [] as LogRow[],
    busy: false,
    canRetryOperation: vi.fn((id: string) => id === "failed"),
    retryOperation: vi.fn(async (_id: string) => {}),
    copyOperationDiagnostic: vi.fn(async (_id: string) => {}),
  });
}

let store: ReturnType<typeof makeStore>;
vi.mock("../../../stores/extensions", () => ({ useExtensionsStore: () => store }));

// A missing component fails a business assertion during RED, rather than
// preventing the test suite from loading before any assertions can run.
const components = import.meta.glob<{ default: Component }>("../ExtensionOperationLog.vue", { eager: true });
function mountLog() {
  const component = components["../ExtensionOperationLog.vue"];
  expect(component, "B3 must provide the operation log panel").toBeDefined();
  return mount(component!.default, { global: { plugins: [i18n] } });
}

describe("ExtensionOperationLog", () => {
  beforeEach(() => {
    store = makeStore();
    i18n.global.locale.value = "zh-CN";
  });

  it("provides a collapsible log with a translated empty state", () => {
    const wrapper = mountLog();
    expect(wrapper.get("details > summary").text()).toBe("操作日志");
    expect(wrapper.get("details").attributes("open")).toBeUndefined();
    expect(wrapper.text()).toContain("暂无操作记录");
    expect(wrapper.findAll("li")).toHaveLength(0);
    wrapper.unmount();
  });

  it("renders the supplied statuses, action, attempt, times and literal diagnostics", () => {
    store.operationLog = [row("success"), row("failed"), row("unknown", { diagnostic: "<script>example</script>" })];
    const wrapper = mountLog();
    const rows = wrapper.findAll("li");
    expect(rows).toHaveLength(3);
    expect(rows[0]!.text()).toContain("成功");
    expect(rows[1]!.text()).toContain("失败");
    expect(rows[1]!.text()).toContain("Example skill");
    expect(rows[1]!.text()).toContain("安装");
    expect(rows[1]!.text()).toContain("第 2 次尝试");
    expect(rows[1]!.findAll("time").map((time) => time.attributes("datetime")))
      .toEqual(["2026-10-27T10:00:00Z", "2026-10-27T10:00:05Z"]);
    expect(rows[1]!.text()).toContain("2026-10-27T10:00:00Z");
    expect(rows[1]!.get("pre").text()).toBe("direct: failed\nmirror: HTTP 502");
    expect(rows[2]!.text()).toContain("结果未知，请先刷新列表再重试");
    expect(rows[2]!.get("pre").text()).toBe("<script>example</script>");
    expect(rows[2]!.find("script").exists()).toBe(false);
    wrapper.unmount();
  });

  it("delegates retry only for the selected eligible failed row", async () => {
    store.operationLog = [row("success"), row("failed"), row("failed", { operationId: "old-context" }), row("unknown")];
    const wrapper = mountLog();
    const buttons = wrapper.findAll("button").filter((button) => button.text() === "重试");
    expect(buttons).toHaveLength(1);
    await buttons[0]!.trigger("click");
    await flushPromises();
    expect(store.retryOperation).toHaveBeenCalledExactlyOnceWith("failed");
    wrapper.unmount();
  });

  it("never offers unknown results a retry even if store eligibility is permissive", () => {
    store.operationLog = [row("unknown")];
    store.canRetryOperation.mockReturnValue(true);
    const wrapper = mountLog();
    expect(wrapper.text()).toContain("请先刷新列表再重试");
    expect(wrapper.findAll("button").some((button) => button.text() === "重试")).toBe(false);
    wrapper.unmount();
  });

  it("disables retries while the store is busy", async () => {
    store.operationLog = [row("failed")];
    store.busy = true;
    const wrapper = mountLog();
    const retry = wrapper.findAll("button").find((button) => button.text() === "重试")!;
    expect(retry.attributes("disabled")).toBeDefined();
    await retry.trigger("click");
    expect(store.retryOperation).not.toHaveBeenCalled();
    store.busy = false;
    await nextTick();
    expect(retry.attributes("disabled")).toBeUndefined();
    wrapper.unmount();
  });

  it("delegates diagnostic copying for every row, including unknown and success", async () => {
    store.operationLog = [row("success"), row("failed"), row("unknown")];
    store.busy = true;
    const wrapper = mountLog();
    const copies = wrapper.findAll("button").filter((button) => button.text() === "复制诊断");
    expect(copies).toHaveLength(3);
    for (const copy of copies) await copy.trigger("click");
    await flushPromises();
    expect(store.copyOperationDiagnostic.mock.calls).toEqual([["success"], ["failed"], ["unknown"]]);
    wrapper.unmount();
  });

  it("follows reactive log replacement without retaining rows from the prior context", async () => {
    store.operationLog = [row("failed")];
    const wrapper = mountLog();
    store.operationLog = [row("success", { operationId: "new-context", label: "New workspace item" })];
    await nextTick();
    expect(wrapper.findAll("li")).toHaveLength(1);
    expect(wrapper.text()).toContain("New workspace item");
    expect(wrapper.text()).not.toContain("Example skill");
    store.operationLog = [];
    await nextTick();
    expect(wrapper.text()).toContain("暂无操作记录");
    wrapper.unmount();
  });

  it("translates the log and unknown guidance in English", () => {
    i18n.global.locale.value = "en-US";
    store.operationLog = [row("unknown", { kind: "plugins", action: "remove" })];
    const wrapper = mountLog();
    expect(wrapper.get("summary").text()).toBe("Operation log");
    expect(wrapper.text()).toContain("Unknown result; refresh the list before retrying");
    expect(wrapper.text()).toContain("Uninstall");
    expect(wrapper.text()).toContain("Attempt 2");
    expect(wrapper.text()).toContain("Copy diagnostics");
    expect(wrapper.text()).not.toContain("extensions.log.");
    wrapper.unmount();
  });
});
