import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { i18n } from "../../../i18n";
import { useExtensionsStore } from "../../../stores/extensions";
import { extensionsCall } from "../../../lib/ipc";
import GitHubMcpAuth from "../GitHubMcpAuth.vue";
vi.mock("../../../lib/ipc", () => ({ extensionsCall: vi.fn() }));
vi.mock("@tauri-apps/plugin-clipboard-manager", () => ({ writeText: vi.fn() }));
const call = vi.mocked(extensionsCall);
const status = () => ({ revision: "rev", engines: { claude: { enabled: true, configured: false, connection: "not_verified" }, codex: { enabled: true, configured: false, connection: "not_verified" } } });
beforeEach(() => {
  setActivePinia(createPinia()); i18n.global.locale.value = "zh-CN"; call.mockReset();
  useExtensionsStore().setContext("/qa", "runtime");
  call.mockImplementation(async p => p.op === "list" ? { items: [] } : status());
});
const render = () => mount(GitHubMcpAuth, { global: { plugins: [i18n] } });
describe("GitHub MCP configuration", () => {
  it("saves only selected engines via stdin, clears the token, and does not claim connection success", async () => {
    const wrapper = render(); await flushPromises();
    await wrapper.get('input[value="codex"]').setValue(false);
    await wrapper.get('input[type="password"]').setValue("qa-only-secret");
    await wrapper.get("form").trigger("submit"); await flushPromises();
    const request = call.mock.calls.find(([p]) => p.op === "github-auth-save")![0];
    expect(JSON.parse(request.config!)).toEqual({ agents: ["claude"], token: "qa-only-secret", revision: "rev" });
    expect((wrapper.get('input[type="password"]').element as HTMLInputElement).value).toBe("");
    expect(wrapper.text()).toContain("连接尚未验证"); expect(wrapper.text()).not.toContain("qa-only-secret");
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    expect(useExtensionsStore().operationLog).toEqual([]); wrapper.unmount();
  });
  it("close without save does not mutate and failures never reveal or keep credentials", async () => {
    const wrapper = render(); await flushPromises();
    await wrapper.get('input[type="password"]').setValue("qa-only-secret");
    await wrapper.get(".auth-heading button").trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(1); expect(call.mock.calls.map(([p]) => p.op)).toEqual(["github-auth-status"]);
    call.mockRejectedValueOnce({ code: "AISC_ERR_GITHUB_AUTH_CONFIG_FAILED", message: "qa-only-secret" });
    await wrapper.get("form").trigger("submit"); await flushPromises();
    expect(wrapper.get('[role="alert"]').text()).not.toContain("qa-only-secret");
    expect((wrapper.get('input[type="password"]').element as HTMLInputElement).value).toBe("");
    expect(useExtensionsStore().operationLog).toEqual([]); wrapper.unmount();
  });
  it("drops old results and clears drafts after switching target", async () => {
    const wrapper = render(); await flushPromises();
    let complete!:(v:Record<string, unknown>)=>void; call.mockImplementationOnce(() => new Promise(resolve => { complete = resolve; }));
    await wrapper.get('input[type="password"]').setValue("qa-only-secret");
    await wrapper.get("form").trigger("submit");
    useExtensionsStore().setContext("/other", "other"); await flushPromises();
    expect(wrapper.emitted("close")).toHaveLength(1);
    complete(status()); await flushPromises();
    expect(wrapper.find('input[type="password"]').exists()).toBe(false); expect(wrapper.text()).not.toContain("配置已保存"); wrapper.unmount();
  });
  it("checks connection explicitly without resending a draft token", async () => {
    const wrapper = render(); await flushPromises();
    await wrapper.get('input[type="password"]').setValue("qa-only-secret");
    await wrapper.findAll("button").find(b => b.text().includes("检查连接"))!.trigger("click"); await flushPromises();
    const request = call.mock.calls.find(([p]) => p.op === "github-auth-check")![0];
    expect(request.config).not.toContain("qa-only-secret"); wrapper.unmount();
  });
});
