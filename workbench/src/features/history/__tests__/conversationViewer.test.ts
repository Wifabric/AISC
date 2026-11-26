import { afterEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { i18n } from "../../../i18n";
import { useWorkspaceExplorerStore } from "../../../stores/workspaceExplorer";
import ConversationViewer from "../ConversationViewer.vue";
import type { ConversationReadResult } from "../../../types";

vi.mock("../../../lib/ipc", () => ({}));
vi.mock("@tauri-apps/plugin-opener", () => ({ openUrl: vi.fn() }));
vi.mock("@tauri-apps/plugin-clipboard-manager", () => ({ writeText: vi.fn() }));
let wrapper: VueWrapper | undefined;
afterEach(() => { wrapper?.unmount(); document.body.innerHTML = ""; vi.restoreAllMocks(); });
function page(text: string, start = 0): ConversationReadResult {
  return { schema: "aisc.conversation-read/v1", conversation_id: "id", agent: "codex", file_size: 1,
    total: 5 + start, start, malformed_lines: 0, degraded_reason: null,
    messages: [
      { ordinal: start, role: "user", kind: "message", text: "请说明结果" },
      { ordinal: start + 1, role: "assistant", kind: "reasoning", text: "分析方案" },
      { ordinal: start + 2, role: "assistant", kind: "message", text: "正在检查", phase: "commentary" },
      { ordinal: start + 3, role: "assistant", kind: "tool_use", text: "ls", name: "bash", result: "a.md" },
      { ordinal: start + 4, role: "assistant", kind: "message", text },
    ] };
}
function setup() {
  const pinia = createPinia(); setActivePinia(pinia);
  const explorer = useWorkspaceExplorerStore(); explorer.workspace = "/ws";
  const read = vi.spyOn(explorer, "readConversationPage");
  explorer.openConversationViewer("codex", "id", "记录阅读");
  return { pinia, explorer, read };
}
function show(pinia: ReturnType<typeof createPinia>) {
  wrapper = mount(ConversationViewer, { attachTo: document.body, global: { plugins: [pinia, i18n] } });
}
describe("Work Record reader", () => {
  it("renders structured command arguments and output from the same Codex step", async () => {
    const { pinia, read } = setup();
    const data = page("final");
    const tool = data.messages.find(m => m.kind === "tool_use")!;
    tool.name = "exec";
    tool.text = 'text(await tools.exec_command({cmd:"head -n 1 qa.txt",workdir:"/root/app"}))';
    tool.result = "预览测试：蓝色雨伞 7391";
    read.mockResolvedValue(data);
    show(pinia); await flushPromises();
    const activity = document.querySelector(".cv-activity")!;
    (activity as HTMLDetailsElement).open = true;
    activity.dispatchEvent(new Event("toggle"));
    await flushPromises();
    const button = Array.from(activity.querySelectorAll("summary")).find(e => e.textContent?.includes("exec"))!;
    const detail = button.closest("details")!;
    detail.open = true;
    detail.dispatchEvent(new Event("toggle")); await flushPromises();
    expect(activity.textContent).toContain("head -n 1 qa.txt");
    expect(activity.textContent).toContain("/root/app");
    expect(activity.textContent).toContain("蓝色雨伞 7391");
    expect(activity.textContent).not.toContain("text(await");
  });

  it("only links existing bare workspace paths and exports through the active record", async () => {
    const { pinia, explorer, read } = setup();
    read.mockResolvedValue(page("Files: `src/known file.md` and `src/missing.md`"));
    vi.spyOn(explorer, "missingRecordPaths").mockResolvedValue(new Set(["src/missing.md"]));
    const save = vi.spyOn(explorer, "exportConversation").mockResolvedValue(null);
    show(pinia); await flushPromises();
    expect([...document.querySelectorAll(".cv-answer a")].map(a => a.textContent)).toEqual(["src/known file.md"]);
    (document.querySelector(".cv-foot button") as HTMLButtonElement).click();
    await flushPromises();
    expect(save).toHaveBeenCalledWith("codex", "id", "记录阅读");
    expect(document.querySelector(".cv-answer")?.textContent).toContain("src/missing.md");
  });
  it("shows one collapsed activity item and a fully rendered answer, with no input or live stream", async () => {
    const { pinia, read } = setup(); read.mockResolvedValue(page("## 阅读结果\n\n**完整答案**\n\n$E=mc^2$"));
    show(pinia); await flushPromises();
    expect(document.querySelectorAll(".cv-activity")).toHaveLength(1);
    expect(document.querySelector(".cv-activity")?.hasAttribute("open")).toBe(false);
    expect(document.querySelector(".cv-answer h2")?.textContent).toBe("阅读结果");
    expect(document.querySelector(".cv-answer .katex")).not.toBeNull();
    expect(document.querySelector("textarea, .xterm, [contenteditable=true]")).toBeNull();
    expect(read).toHaveBeenCalledTimes(1);
  });
  it("discards an old response when another conversation is opened", async () => {
    const { pinia, explorer, read } = setup();
    let resolve!: (r: ConversationReadResult) => void;
    read.mockReturnValueOnce(new Promise(r => { resolve = r; })).mockResolvedValueOnce(page("新会话答案"));
    show(pinia); await flushPromises();
    explorer.openConversationViewer("claude", "other", "新记录"); await flushPromises();
    resolve(page("陈旧答案")); await flushPromises();
    expect(document.querySelector(".cv-answer")?.textContent).toContain("新会话答案");
    expect(document.querySelector(".cv-answer")?.textContent).not.toContain("陈旧答案");
  });
  it("closes on workspace switch and ignores outstanding reads", async () => {
    const { pinia, explorer, read } = setup();
    let resolve!: (r: ConversationReadResult) => void;
    read.mockReturnValue(new Promise(r => { resolve = r; })); show(pinia); await flushPromises();
    explorer.workspace = "/other"; await flushPromises(); resolve(page("旧工作区")); await flushPromises();
    expect(document.querySelector('[role="dialog"]')).toBeNull();
  });
  it("loads earlier pages using the exclusive ordinal and groups across the boundary", async () => {
    const { pinia, read } = setup(); read.mockResolvedValueOnce(page("较新答案", 100)).mockResolvedValueOnce(page("较早答案"));
    show(pinia); await flushPromises();
    (document.querySelector(".cv-earlier button") as HTMLButtonElement).click(); await flushPromises();
    expect(read).toHaveBeenLastCalledWith("id", "codex", 100, 100);
    expect(document.querySelectorAll(".cv-turn")).toHaveLength(2);
    expect(document.querySelector(".cv-body")?.textContent).toContain("较早答案");
  });
  it("opens contained file links through the store and restores opener focus on Escape", async () => {
    const opener = document.createElement("button"); document.body.append(opener); opener.focus();
    const { pinia, explorer, read } = setup(); read.mockResolvedValue(page("[结果](file:///ws/a.md)"));
    const open = vi.spyOn(explorer, "openRecordLink").mockResolvedValue();
    show(pinia); await flushPromises();
    (document.querySelector(".cv-answer a") as HTMLAnchorElement).click(); await flushPromises();
    expect(open).toHaveBeenCalledWith("file:///ws/a.md", "/ws");
    document.querySelector('[role="dialog"]')?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await flushPromises(); expect(document.activeElement).toBe(opener);
  });
});
