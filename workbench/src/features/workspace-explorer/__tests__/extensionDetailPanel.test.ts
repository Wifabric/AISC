import { beforeEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { i18n } from "../../../i18n";
import ExtensionDetailPanel from "../ExtensionDetailPanel.vue";
import { CATEGORIZED_EXTENSION_RECOMMENDATIONS } from "../recommendationCatalog";

const research = CATEGORIZED_EXTENSION_RECOMMENDATIONS.find(
  (entry) => entry.identity === "mattpocock/skills:research",
)!;

beforeEach(() => {
  i18n.global.locale.value = "zh-CN";
});

describe("ExtensionDetailPanel", () => {
  it("shows a first-party Chinese summary before metadata and preserves market text", () => {
    const wrapper = mount(ExtensionDetailPanel, {
      global: { plugins: [i18n] },
      props: {
        item: {
          kind: "skills", id: research.identity, name: research.name,
          repo: "mattpocock/skills", directory: "research",
          description: "English market description", installs: "732132",
        },
        recommendation: research,
      },
      slots: { actions: "<button data-testid='panel-action'>安装</button>" },
    });
    const summary = wrapper.get("[data-testid='extension-detail-summary']");
    expect(summary.text()).toBe(research.summaryZh);
    expect(wrapper.text().indexOf(research.summaryZh)).toBeLessThan(
      wrapper.text().indexOf("English market description"),
    );
    expect(wrapper.get("[data-testid='extension-detail-original']").text()).toContain(
      "English market description",
    );
    expect(wrapper.find("[data-testid='panel-action']").exists()).toBe(true);
    expect(wrapper.get("a").attributes("href")).toBe("https://github.com/mattpocock/skills");
  });

  it("falls back to a useful Chinese introduction for unknown market items", () => {
    const wrapper = mount(ExtensionDetailPanel, {
      global: { plugins: [i18n] },
      props: {
        item: {
          kind: "mcp", id: "unknown/server", name: "Unknown Server",
          description: "Original English copy",
        },
      },
    });
    expect(wrapper.get("[data-testid='extension-detail-summary']").text()).toBe("Original English copy");
    expect(wrapper.find("[data-testid='extension-detail-original']").exists()).toBe(false);
  });

  it("renders update, install count and source metadata without fake values", () => {
    const wrapper = mount(ExtensionDetailPanel, {
      global: { plugins: [i18n] },
      props: {
        item: {
          kind: "plugins", id: "chart@official", name: "chart",
          marketplace: "official", version: "1.0.0", installs: "20",
          repo: "https://example/chart.git",
        },
        update: {
          kind: "plugins", id: "chart@official", name: "chart", status: "ok",
          update_available: true, latest_version: "1.1.0", current_version: "1.0.0",
        },
      },
    });
    const text = wrapper.get("[data-testid='extension-detail-metadata']").text();
    expect(text).toContain("插件");
    expect(text).toContain("official");
    expect(text).toContain("20");
    expect(text).toContain("1.0.0");
    expect(text).toContain("1.1.0");
    expect(wrapper.text()).not.toContain("undefined");
  });

  it("uses a labelled complementary region and emits close on Escape", async () => {
    const wrapper = mount(ExtensionDetailPanel, {
      global: { plugins: [i18n] },
      props: { item: { kind: "skills", id: "demo", name: "Demo" } },
    });
    expect(wrapper.get("[data-testid='extension-detail-panel']").attributes("role")).toBe("complementary");
    await wrapper.get("[data-testid='extension-detail-panel']").trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toHaveLength(1);
  });
});
