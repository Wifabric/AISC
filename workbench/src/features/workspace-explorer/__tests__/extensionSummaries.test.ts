import { describe, expect, it } from "vitest";
import { CATEGORIZED_EXTENSION_RECOMMENDATIONS } from "../recommendationCatalog";
import { extensionSummary } from "../extensionSummaries";

const CAVEMAN_CHILDREN = [
  "caveman",
  "caveman-commit",
  "caveman-compress",
  "caveman-review",
  "caveman-help",
  "caveman-stats",
  "caveman-explore",
  "caveman-learn",
  "caveman-optimize",
  "caveman-evidence-review",
  "caveman-discover",
  "caveman-manage",
  "caveman-setup",
];

describe("extension summaries", () => {
  it("uses first-party bilingual summaries for every catalog identity", () => {
    for (const recommendation of CATEGORIZED_EXTENSION_RECOMMENDATIONS) {
      const item = {
        kind: recommendation.kind,
        id: recommendation.identity,
        name: recommendation.name,
        repo: recommendation.identity.split(":", 1)[0],
        description: "Market original text",
      };
      const zh = extensionSummary(item, "zh-CN");
      const en = extensionSummary(item, "en-US");
      expect(zh.summary, recommendation.identity).toBe(recommendation.summaryZh);
      expect(zh.source).toBe("first-party");
      expect(en.summary).toBe(recommendation.summaryEn);
      expect(en.source).toBe("first-party");
    }
  });

  it("gives every caveman child a distinct Chinese introduction", () => {
    const summaries = CAVEMAN_CHILDREN.map((directory) => {
      const result = extensionSummary(
        {
          kind: "skills",
          id: `JuliusBrussee/caveman:${directory}`,
          name: directory,
          repo: "JuliusBrussee/caveman",
          directory,
          description: "",
        },
        "zh-CN",
      );
      expect(result.summary.trim()).not.toBe(directory);
      expect(result.source).toBe("first-party");
      return result.summary;
    });
    expect(new Set(summaries).size).toBe(CAVEMAN_CHILDREN.length);
  });

  it("matches an installed skill by repo and directory when its id is only a name", () => {
    const result = extensionSummary(
      {
        kind: "skills",
        id: "code-review",
        name: "code-review",
        repo: "mattpocock/skills",
        directory: "code-review",
        description: "",
      },
      "zh-CN",
    );
    expect(result.summary).toContain("审查代码");
    expect(result.source).toBe("first-party");
  });

  it("labels marketplace result kinds without turning MCP into a skill", () => {
    const result = extensionSummary(
      { kind: "market-mcp", id: "unknown/server", name: "Unknown Server", description: "" },
      "zh-CN",
    );
    expect(result.summary).toContain("暂无功能介绍");
    expect(result.summary).not.toContain("技能 Unknown Server");
  });

  it("uses a transparent local fallback and preserves the market original for unknown items", () => {
    const result = extensionSummary(
      {
        kind: "mcp",
        id: "unknown/server",
        name: "Unknown Server",
        repo: "",
        description: "English market description",
      },
      "zh-CN",
    );
    expect(result.source).toBe("upstream");
    expect(result.summary).toBe("English market description");
    expect(result.summary).not.toContain("安装前");
    expect(result.marketOriginal).toBeUndefined();
  });

  it("does not invent an empty market original", () => {
    const result = extensionSummary(
      { kind: "plugins", id: "unknown@market", name: "Unknown", description: "" },
      "en-US",
    );
    expect(result.source).toBe("fallback");
    expect(result.summary).toContain("No functional description");
    expect(result.marketOriginal).toBeUndefined();
  });
});

it("does not assign catalog or caveman capabilities by name alone", () => {
  for (const name of ["research", "code-review", "caveman", "frontend-design"]) {
    const result = extensionSummary({ kind: "skills", id: name, name,
      directory: name, repo: "someone/unrelated", description: "My actual function" }, "zh-CN");
    expect(result.summary).toBe("My actual function");
    expect(result.source).toBe("upstream");
  }
});
it("matches marketplace kinds by exact source identity", () => {
  const result = extensionSummary({ kind: "market-skill", id: "mattpocock/skills:research",
    name: "research", repo: "mattpocock/skills", directory: "research" }, "zh-CN");
  expect(result.source).toBe("first-party");
});
