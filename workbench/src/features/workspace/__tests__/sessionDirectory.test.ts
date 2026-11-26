import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { expect, it, vi } from "vitest";
import { i18n } from "../../../i18n";
import { useWorkspaceExplorerStore } from "../../../stores/workspaceExplorer";
import SessionDirectory from "../SessionDirectory.vue";
import { workspaceList } from "../../../lib/ipc";

vi.mock("../../../lib/ipc", () => ({ workspaceList: vi.fn() }));

it("filters files and resolves typed subdirectories without passing a trailing slash to the CLI", async () => {
  const pinia = createPinia();
  setActivePinia(pinia);
  useWorkspaceExplorerStore().workspace = "/workspace";
  vi.mocked(workspaceList).mockImplementation(async (_workspace, parent) => ({
    schema_version: 1, next_cursor: null, truncated: false,
    nodes: ["dir", "file"].map((kind, index) => {
      const name = index ? "source.txt" : "source files";
      return { kind: kind as "dir" | "file", name, relative_path: parent ? parent + "/" + name : name,
        expandable: !index, artifact_badges: [], change_state: "" };
    }),
  }));
  const view = mount(SessionDirectory, { props: { modelValue: "" }, global: { plugins: [pinia, i18n] } });
  await flushPromises();
  await view.get("input").setValue("src/so");
  await flushPromises();
  expect(view.findAll("option").map(option => option.attributes("value"))).toEqual(["src/source files/"]);
  await view.get("input").setValue("src/source files/");
  expect(view.emitted("update:modelValue")?.pop()).toEqual(["src/source files"]);
  view.unmount();
});
