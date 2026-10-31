import type { ExtensionsItem } from "../../lib/ipc";
import { CATEGORIZED_EXTENSION_RECOMMENDATIONS } from "./recommendationCatalog";

export type ExtensionSummaryLocale = "zh-CN" | "en-US";

export type ExtensionSummaryItem = Pick<
  ExtensionsItem,
  "kind" | "id" | "name" | "repo" | "description"
> &
  Partial<Pick<ExtensionsItem, "directory">>;

export interface ExtensionSummaryResult {
  summary: string;
  marketOriginal?: string;
  source: "first-party" | "upstream" | "fallback";
}

const CAVEMAN_SUMMARIES = new Map<string, { zh: string; en: string }>([
  ["caveman", {
    zh: "用极简、高保真的代理交流指令减少废话，适合偏好短输出的工作流。",
    en: "Uses terse, high-fidelity agent instructions for workflows that prefer brief output.",
  }],
  ["caveman-commit", {
    zh: "按 Conventional Commits 格式编写简洁的提交说明，突出修改动机和必要的兼容性变化。",
    en: "Shapes changes into clear, reviewable commit messages with motive and scope.",
  }],
  ["caveman-compress", {
    zh: "将 CLAUDE.md、记忆文件或待办清单压缩成简洁格式，保留规则、约束和可执行信息。",
    en: "Compresses memory files and to-do lists while preserving rules and actionable information.",
  }],
  ["caveman-review", {
    zh: "精简审查代码或 PR 差异，每条问题用一行列出位置、问题和修复建议。",
    en: "Reviews code or PR diffs with one line per finding: location, problem, and fix.",
  }],
  ["caveman-help", {
    zh: "提供 caveman 技能组的用法速查和常见场景指引。",
    en: "Provides usage guidance and common scenarios for the caveman skill group.",
  }],
  ["caveman-stats", {
    zh: "展示当前 Claude Code 会话记录的输出、缓存读取 token 用量及模式归属，或定位宿主用量报告。",
    en: "Shows recorded output and cache-read token usage and mode attribution for the current session.",
  }],
  ["caveman-explore", {
    zh: "只读探索代码仓库，定位跨文件实现与入口，以文件路径和行号返回线索。",
    en: "Explores repositories read-only and returns path:line citations for cross-file implementation.",
  }],
  ["caveman-learn", {
    zh: "分析 Caveman learn 报告中的 token 开销，逐项征求同意后降低上下文成本并核对收益。",
    en: "Reviews token sinks in Caveman learn reports and applies cost reductions with per-edit consent.",
  }],
  ["caveman-optimize", {
    zh: "根据 Caveman 优化报告选择候选方案，经明确同意后与基线成对评估。",
    en: "Evaluates an operator-selected Caveman optimization candidate against a paired baseline.",
  }],
  ["caveman-evidence-review", {
    zh: "只读审查 Caveman Cloud 的费用、Cave Score、工作流、调用链、延迟、错误和节省证据。",
    en: "Reviews Caveman Cloud cost, Cave Score, workflows, traces, latency, errors, and savings read-only.",
  }],
  ["caveman-discover", {
    zh: "发现并标注仓库中的 LLM 工作流，使 Caveman Cloud 能按工作流归集费用。",
    en: "Finds and labels repository LLM workflows so Caveman Cloud can group spending by workflow.",
  }],
  ["caveman-manage", {
    zh: "审查 Caveman Cloud 实验的启动、批准、取消、推广和回滚条件，阻止不满足评估要求的操作。",
    en: "Inspects the Caveman experiment lifecycle and blocks execution that lacks evaluation safeguards.",
  }],
  ["caveman-setup", {
    zh: "将仓库接入 Caveman Cloud 网关，以保持请求行为的记录模式测量 LLM 用量与费用。",
    en: "Connects a repository to the Caveman Cloud gateway in record mode to measure LLM costs.",
  }],
]);

function normalizedKind(kind: string): string {
  return ({ "market-skill": "skills", "market-mcp": "mcp", "market-plugin": "plugins" } as Record<string, string>)[kind] ?? kind;
}

const FIRST_PARTY = new Map<string, (typeof CATEGORIZED_EXTENSION_RECOMMENDATIONS)[number]>(
  CATEGORIZED_EXTENSION_RECOMMENDATIONS.map((entry) =>
    [`${entry.kind}:${entry.identity.toLowerCase()}`, entry] as const),
);

function firstPartySummary(item: ExtensionSummaryItem, locale: ExtensionSummaryLocale): ExtensionSummaryResult | null {
  const kind = normalizedKind(item.kind);
  const repo = item.repo?.trim().toLowerCase() ?? "";
  const directory = item.directory?.trim() || item.name.trim();
  const id = item.id.trim().toLowerCase();
  const cavemanRepo = repo === "juliusbrussee/caveman" || id.startsWith("juliusbrussee/caveman:");
  const caveman = kind === "skills" && cavemanRepo
    ? CAVEMAN_SUMMARIES.get(directory) : undefined;
  const original = item.description?.trim();
  if (caveman) return {
    summary: locale === "zh-CN" ? caveman.zh : caveman.en,
    source: "first-party", ...(original ? { marketOriginal: original } : {}),
  };
  // Exact kind and repository identity only: an unrelated skill with the same
  // display name must never inherit another author's capabilities.
  const keys = [id, repo && directory ? `${repo}:${directory.toLowerCase()}` : ""];
  for (const key of keys.filter(Boolean)) {
    const entry = FIRST_PARTY.get(`${kind}:${key}`);
    if (entry) return {
      summary: locale === "zh-CN" ? entry.summaryZh : entry.summaryEn,
      source: "first-party", ...(original ? { marketOriginal: original } : {}),
    };
  }
  return null;
}

function fallbackSummary(
  item: ExtensionSummaryItem,
  locale: ExtensionSummaryLocale,
): ExtensionSummaryResult {
  const original = item.description?.trim();
  if (original) return { source: "upstream", summary: original };
  return {
    source: "fallback",
    summary: locale === "zh-CN"
      ? "暂无功能介绍，可查看来源说明。"
      : "No functional description is available. See the source for details.",
  };
}

export function extensionSummary(
  item: ExtensionSummaryItem,
  locale: ExtensionSummaryLocale,
): ExtensionSummaryResult {
  return firstPartySummary(item, locale) ?? fallbackSummary(item, locale);
}

export function skillGroupSummary(
  group: { repo: string; items: ExtensionSummaryItem[] }, locale: ExtensionSummaryLocale,
): string {
  const rootName = group.repo.split("/").pop()?.toLowerCase();
  const root = group.items.find(item => (item.directory || item.name).toLowerCase() === rootName);
  if (root) return extensionSummary(root, locale).summary;
  const descriptions = group.items.slice(0, 3).map(item =>
    `${item.name}：${extensionSummary(item, locale).summary}`);
  return descriptions.join(" ");
}
