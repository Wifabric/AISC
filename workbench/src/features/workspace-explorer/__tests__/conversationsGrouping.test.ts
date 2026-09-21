/**
 * 批 8 手测: history (conversations) panel groups rows by agent — but ONLY
 * when both agents have history. A lone agent's list stays flat (a single
 * section header is noise, not info); group order follows each group's most
 * recent activity.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import { i18n } from "../../../i18n";
import { useWorkspaceExplorerStore } from "../../../stores/workspaceExplorer";
import WorkspaceExplorer from "../WorkspaceExplorer.vue";
import type { ConversationSummary } from "../../../types";

vi.mock("../../../lib/ipc", () => ({
  logUiEvent: vi.fn().mockResolvedValue(undefined),
  workspaceList: vi.fn(async () => ({
    schema_version: 1, nodes: [], next_cursor: null, truncated: false,
  })),
  workspaceOpen: vi.fn().mockResolvedValue(undefined),
  conversationList: vi.fn(async () => ({ schema_version: 1, conversations: [] })),
}));
vi.mock("@tauri-apps/plugin-clipboard-manager", () => ({
  writeText: vi.fn().mockResolvedValue(undefined),
  readText: vi.fn().mockResolvedValue(""),
}));
vi.mock("@tauri-apps/plugin-dialog", () => ({ confirm: vi.fn(), open: vi.fn() }));
vi.mock("@tauri-apps/api/core", () => ({ Channel: class {} }));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockResolvedValue(() => {}),
}));
vi.mock("@tauri-apps/api/window", () => ({ getCurrentWindow: () => ({}) }));
vi.mock("@tauri-apps/plugin-notification", () => ({
  isPermissionGranted: vi.fn(),
  requestPermission: vi.fn(),
  sendNotification: vi.fn(),
}));

function conv(id: string, agent: "claude" | "codex", lastAt: string): ConversationSummary {
  return {
    conversation_id: id,
    agent,
    title: `${agent}-${id}`,
    started_at: lastAt,
    last_at: lastAt,
    message_count: 3,
    file_size: 128,
    resumable: true,
  };
}

function mountPanel(): ReturnType<typeof mount> {
  return mount(WorkspaceExplorer, { global: { plugins: [i18n] } });
}

beforeEach(() => {
  setActivePinia(createPinia());
  i18n.global.locale.value = "zh-CN";
});

describe("conversations panel agent grouping", () => {
  it("stays FLAT when only one agent has history (no section headers)", () => {
    const explorer = useWorkspaceExplorerStore();
    explorer.activeKind = "conversations";
    explorer.conversations = [
      conv("c1", "codex", "2026-09-20T10:00:00Z"),
      conv("c2", "codex", "2026-09-19T10:00:00Z"),
    ];
    const wrapper = mountPanel();
    try {
      expect(wrapper.findAll(".conversation-group-label").length).toBe(0);
      const rows = wrapper.findAll(".conversation-row");
      expect(rows).toHaveLength(2);
      expect(rows[0].text()).toContain("codex-c1");
    } finally {
      wrapper.unmount();
    }
  });

  it("groups by agent when both have history; newest group first", () => {
    const explorer = useWorkspaceExplorerStore();
    explorer.activeKind = "conversations";
    // Interleaved on purpose — the store list is global recency order.
    explorer.conversations = [
      conv("c1", "codex", "2026-09-20T10:00:00Z"),
      conv("a1", "claude", "2026-09-21T09:00:00Z"),
      conv("c2", "codex", "2026-09-18T10:00:00Z"),
      conv("a2", "claude", "2026-09-15T09:00:00Z"),
    ];
    const wrapper = mountPanel();
    try {
      const headers = wrapper.findAll(".conversation-group-label");
      expect(headers).toHaveLength(2);
      // Claude's newest conversation (09-21) beats Codex's (09-20) → first.
      expect(headers[0].text()).toContain("Claude");
      expect(headers[0].attributes("data-agent")).toBe("claude");
      expect(headers[1].text()).toContain("Codex");
      // Rows appear under their own header: all claude rows before codex rows.
      const titles = wrapper.findAll(".conversation-row .conversation-title").map((w) => w.text());
      expect(titles).toEqual(["claude-a1", "claude-a2", "codex-c1", "codex-c2"]);
    } finally {
      wrapper.unmount();
    }
  });
});
