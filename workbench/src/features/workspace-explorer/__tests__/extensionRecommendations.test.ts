import { describe, expect, it } from "vitest";
import { enUS } from "../../../i18n/en-US";
import { zhCN } from "../../../i18n/zh-CN";

interface Recommendation {
  kind: string; identity: string; query: string; name: string; sourceUrl: string; reasonKey: string;
}
const modules = import.meta.glob<{ EXTENSION_RECOMMENDATIONS: readonly Recommendation[] }>("../extensionRecommendations.ts", { eager: true });
function entries() {
  const model = modules["../extensionRecommendations.ts"];
  expect(model, "B4 must provide the local curated model").toBeDefined();
  return model!.EXTENSION_RECOMMENDATIONS;
}

describe("curated recommendations model", () => {
  it("contains the verified identities and search queries for all three kinds in fixed order", () => {
    expect(entries().map(({ kind, identity, query }) => ({ kind, identity, query }))).toEqual([
      { kind: "skills", identity: "JuliusBrussee/caveman:caveman", query: "caveman" },
      { kind: "mcp", identity: "upstash/context7-mcp", query: "context7" },
      { kind: "plugins", identity: "superpowers@claude-plugins-official", query: "superpowers" },
    ]);
  });
  it("has unique identities, source URLs and bilingual reasons without fake version or popularity", () => {
    expect(new Set(entries().map((entry) => `${entry.kind}:${entry.identity}`)).size).toBe(entries().length);
    for (const entry of entries()) {
      expect(entry.name.trim()).not.toBe("");
      expect(new URL(entry.sourceUrl).protocol).toBe("https:");
      for (const dictionary of [zhCN, enUS]) {
        expect((dictionary as Record<string, string>)[entry.reasonKey]?.trim()).toBeTruthy();
      }
      for (const field of ["installs", "popularity", "version"]) expect(entry).not.toHaveProperty(field);
    }
  });
});
