import { describe, expect, it } from "vitest";
import {
  EXTENSION_RECOMMENDATION_CATEGORIES,
  EXTENSION_RECOMMENDATIONS_BY_CATEGORY,
  type RecommendationCategoryId,
} from "../recommendationCatalog";

const EXPECTED_CATEGORY_IDS: RecommendationCategoryId[] = [
  "research",
  "education",
  "knowledge",
  "visualization",
  "writing",
  "development",
];

describe("categorized extension recommendations", () => {
  it("provides exactly six stable categories", () => {
    expect(EXTENSION_RECOMMENDATION_CATEGORIES.map((category) => category.id)).toEqual(
      EXPECTED_CATEGORY_IDS,
    );
    for (const category of EXTENSION_RECOMMENDATION_CATEGORIES) {
      expect(category.labelZh.trim()).not.toBe("");
      expect(category.labelEn.trim()).not.toBe("");
      expect(category.summaryZh.trim()).not.toBe("");
      expect(category.summaryEn.trim()).not.toBe("");
    }
  });

  it("gives every category exactly ten prominent, unique entries", () => {
    expect(EXTENSION_RECOMMENDATION_CATEGORIES).toHaveLength(6);
    for (const { id } of EXTENSION_RECOMMENDATION_CATEGORIES) {
      expect(EXTENSION_RECOMMENDATIONS_BY_CATEGORY[id], id).toHaveLength(10);
    }

    const identities = EXTENSION_RECOMMENDATION_CATEGORIES.flatMap(({ id }) =>
      EXTENSION_RECOMMENDATIONS_BY_CATEGORY[id].map((entry) => `${entry.kind}:${entry.identity}`),
    );
    expect(new Set(identities).size).toBe(60);
  });

  it("keeps every recommendation actionable and honestly sourced", () => {
    for (const { id } of EXTENSION_RECOMMENDATION_CATEGORIES) {
      for (const entry of EXTENSION_RECOMMENDATIONS_BY_CATEGORY[id]) {
        expect(entry.category).toBe(id);
        expect(["skills", "mcp", "plugins"]).toContain(entry.kind);
        expect(entry.identity.trim()).not.toBe("");
        expect(entry.query.trim()).not.toBe("");
        expect(entry.name.trim()).not.toBe("");
        expect(new URL(entry.sourceUrl).protocol).toBe("https:");
        expect(entry.summaryZh.trim().length).toBeGreaterThanOrEqual(8);
        expect(entry.summaryEn.trim().length).toBeGreaterThanOrEqual(8);
        expect(["skills.sh", "smithery", "official-directory"]).toContain(entry.heatSource);
        if (entry.heat !== undefined) expect(entry.heat.trim()).not.toBe("");
      }
    }
  });

  it("mixes asset kinds across the research, education, and knowledge categories", () => {
    for (const id of ["research", "education", "knowledge"] as const) {
      const kinds = new Set(EXTENSION_RECOMMENDATIONS_BY_CATEGORY[id].map((entry) => entry.kind));
      expect(kinds.size, id).toBeGreaterThanOrEqual(2);
    }
  });
});
