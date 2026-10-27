import type { ExtensionsKind } from "../../stores/extensions";

export interface ExtensionRecommendation {
  kind: ExtensionsKind;
  identity: string;
  query: string;
  name: string;
  sourceUrl: string;
  reasonKey: string;
}

// Fixed editorial order, not a cross-market popularity ranking. These identities
// identify the recommendation only; installation uses actual market results.
export const EXTENSION_RECOMMENDATIONS = [
  {
    kind: "skills", identity: "JuliusBrussee/caveman:caveman", query: "caveman", name: "caveman",
    sourceUrl: "https://github.com/JuliusBrussee/caveman",
    reasonKey: "extensions.recommendations.reason.caveman",
  },
  {
    // Smithery qualifiedName, verified via its registry search on 2026-10-27.
    kind: "mcp", identity: "upstash/context7-mcp", query: "context7", name: "Context7",
    sourceUrl: "https://registry.smithery.ai/servers/upstash/context7-mcp",
    reasonKey: "extensions.recommendations.reason.context7",
  },
  {
    // Present in the bundled claude-plugins-official marketplace.json.
    kind: "plugins", identity: "superpowers@claude-plugins-official", query: "superpowers", name: "superpowers",
    sourceUrl: "https://github.com/obra/superpowers",
    reasonKey: "extensions.recommendations.reason.superpowers",
  },
] as const satisfies readonly ExtensionRecommendation[];
