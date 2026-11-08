import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import ModuleOperationProgress from "../ModuleOperationProgress.vue";
import { i18n } from "../../../i18n";

const state = vi.hoisted(() => ({ phase: "complete", error: "", targetChanged: false, busy: false,
  plan: { module_name: "QA", rows: [] as any[] } }));
vi.mock("../../../stores/moduleOperations", () => ({ useModuleOperationsStore: () => state }));

describe("module result explanation", () => {
  it.each(["installed", "removed", "auth_required"])("does not present the old missing preflight state after %s", status => {
    i18n.global.locale.value = "zh-CN";
    state.plan.rows = [{ key: "qa", member: { name: "QA", identity: "qa/repo:skill", kind: "skills" },
      action: "install", status, reason: "missing" }];
    const wrapper = mount(ModuleOperationProgress, { global: { plugins: [i18n] } });
    expect(wrapper.text()).toContain(i18n.global.t(`modules.status.${status}`));
    expect(wrapper.text()).not.toContain(i18n.global.t("modules.reason.missing"));
    wrapper.unmount();
  });
  it("retains the reason explaining why a member was protected", () => {
    state.plan.rows = [{ key: "qa", member: { name: "QA", identity: "qa/repo:skill", kind: "skills" },
      action: "retain", status: "retained", reason: "shared" }];
    const wrapper = mount(ModuleOperationProgress, { global: { plugins: [i18n] } });
    expect(wrapper.text()).toContain(i18n.global.t("modules.reason.shared"));
    wrapper.unmount();
  });
});
