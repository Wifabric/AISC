import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useCcSwitchUiStore } from "../ccSwitchUi";

/**
 * b2 (v2.1.14): FALLBACK_TEMPLATES is the add page's second source of truth
 * (old images / network-restricted runs) — it must NOT drift from the
 * container manifest. The drift was real: codesome-v3's native endpoint
 * lost `/v1` in the manifest and the add page silently rewrote the prefill
 * once the manifest landed. The manifest is produced by executing the very
 * module the adapter ships (deterministic, static fixtures) — no parsing.
 */
describe("FALLBACK_TEMPLATES ↔ container manifest snapshot", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("endpoint triples match provider_templates_manifest() per template id", () => {
    const root = resolve(process.cwd(), "..");
    // local Windows: the repo venv; CI (ubuntu): system python3.
    const pyExe = [".venv/Scripts/python.exe", ".venv/bin/python", "python3", "python"].find(
      (p) => p.includes("/") ? existsSync(resolve(root, p)) : true);
    expect(pyExe, "repo venv python not found").toBeDefined();
    const out = execFileSync(resolve(root, pyExe!), {
      cwd: root,
      encoding: "utf-8",
      // provider_templates_manifest() is deterministic; the timeout only
      // guards a hung interpreter.
      timeout: 30_000,
      input: [
        "import json, sys",
        "sys.path.insert(0, 'container/lib')",
        "import cc_switch_preset_providers as h",
        "print(json.dumps(h.provider_templates_manifest()))",
      ].join("\n"),
    });
    const manifest: Record<string, { claude_endpoint: string; codex_endpoint: string;
      codex_endpoint_native: string }> = {};
    for (const entry of JSON.parse(out.slice(out.indexOf("[")))) {
      manifest[entry.id] = entry;
    }

    const fallback = useCcSwitchUiStore().templates; // initial = FALLBACK
    expect(fallback.length).toBeGreaterThanOrEqual(6);
    for (const t of fallback) {
      const m = manifest[t.id];
      // A fallback entry with no manifest counterpart is itself a drift.
      expect(m, `manifest missing template ${t.id}`).toBeDefined();
      expect(t.claude_endpoint).toBe(m!.claude_endpoint);
      expect(t.codex_endpoint).toBe(m!.codex_endpoint);
      expect(t.codex_endpoint_native).toBe(m!.codex_endpoint_native);
    }
  });
});
