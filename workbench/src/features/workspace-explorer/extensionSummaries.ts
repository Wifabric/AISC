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
  source: "first-party" | "fallback";
}

const CAVEMAN_SUMMARIES = new Map<string, { zh: string; en: string }>([
  ["caveman", {
    zh: "用极简、高保真的代理交流指令减少废话，适合偏好短输出的工作流。",
    en: "Uses terse, high-fidelity agent instructions for workflows that prefer brief output.",
  }],
  ["caveman-commit", {
    zh: "把变更整理成清晰、可审阅的提交说明，突出动机和边界。",
    en: "Shapes changes into clear, reviewable commit messages with motive and scope.",
  }],
  ["caveman-compress", {
    zh: "压缩冗长输出并保留关键结论、限制和下一步行动。",
    en: "Compresses verbose output while retaining conclusions, constraints, and next actions.",
  }],
  ["caveman-review", {
    zh: "审查代码与文档的一致性、边界条件和可维护性。",
    en: "Reviews code and documentation for consistency, edge cases, and maintainability.",
  }],
  ["caveman-help", {
    zh: "提供 caveman 技能组的用法速查和常见场景指引。",
    en: "Provides usage guidance and common scenarios for the caveman skill group.",
  }],
  ["caveman-stats", {
    zh: "统计任务、输出和行为指标，帮助量化工作流变化。",
    en: "Summarizes task, output, and behavior metrics to quantify workflow changes.",
  }],
  ["caveman-explore", {
    zh: "以短周期探索资料和代码路径，快速收敛到有价值线索。",
    en: "Explores material and code paths in short cycles to converge on useful leads.",
  }],
  ["caveman-learn", {
    zh: "把新材料拆成渐进学习步骤、检查点和练习。",
    en: "Breaks new material into progressive study steps, checkpoints, and exercises.",
  }],
  ["caveman-optimize", {
    zh: "定位流程瓶颈并提出可验证的优化实验。",
    en: "Identifies workflow bottlenecks and proposes verifiable optimization experiments.",
  }],
  ["caveman-evidence-review", {
    zh: "审查证据链、来源和推断强度，标出未证实结论。",
    en: "Reviews evidence chains, sources, and inference strength while flagging unproven claims.",
  }],
  ["caveman-discover", {
    zh: "发现相关资料、工具和替代方案，并比较适用条件。",
    en: "Discovers relevant material, tools, and alternatives, then compares applicability.",
  }],
  ["caveman-manage", {
    zh: "管理任务清单、优先级和状态，保持执行过程可追踪。",
    en: "Manages tasks, priorities, and status so execution remains traceable.",
  }],
  ["caveman-setup", {
    zh: "完成 caveman 技能组的初始配置、启用和验证。",
    en: "Handles initial configuration, enabling, and verification for the caveman skill group.",
  }],
]);

const FIRST_PARTY = new Map(
  CATEGORIZED_EXTENSION_RECOMMENDATIONS.flatMap((entry) => [
    [entry.identity.toLowerCase(), entry] as const,
    [`${entry.kind}:${entry.name.toLowerCase()}`, entry] as const,
  ]),
);

function keysFor(item: ExtensionSummaryItem): string[] {
  const id = item.id.trim();
  const name = item.name.trim();
  const repo = item.repo?.trim() ?? "";
  const directory = item.directory?.trim() ?? name;
  return [
    id,
    repo && directory ? `${repo}:${directory}` : "",
    directory,
    name,
  ].map((value) => value.toLowerCase()).filter(Boolean);
}

function firstPartySummary(
  item: ExtensionSummaryItem,
  locale: ExtensionSummaryLocale,
): ExtensionSummaryResult | null {
  const cavemanDirectory = item.directory?.trim() || (item.repo === "JuliusBrussee/caveman" ? item.name : "");
  const caveman = CAVEMAN_SUMMARIES.get(cavemanDirectory);
  if (caveman) {
    return {
      summary: locale === "zh-CN" ? caveman.zh : caveman.en,
      source: "first-party",
    };
  }

  for (const key of keysFor(item)) {
    const entry = FIRST_PARTY.get(key);
    if (entry) {
      return {
        summary: locale === "zh-CN" ? entry.summaryZh : entry.summaryEn,
        source: "first-party",
      };
    }
  }
  return null;
}

function fallbackSummary(
  item: ExtensionSummaryItem,
  locale: ExtensionSummaryLocale,
): ExtensionSummaryResult {
  const name = item.name.trim() || item.id.trim();
  const source = item.repo?.trim() || (item.kind === "mcp" ? "Smithery" : "market");
  const marketOriginal = item.description?.trim();
  return {
    source: "fallback",
    summary: locale === "zh-CN"
      ? `这是一个来自 ${source} 的${item.kind === "mcp" ? " MCP 服务" : item.kind === "plugins" ? "插件" : "技能"} ${name}；安装前请核对市场原文、仓库说明和权限需求。`
      : `${name} is a ${item.kind === "mcp" ? "MCP server" : item.kind === "plugins" ? "plugin" : "skill"} from ${source}; verify the market text, repository, and permissions before installing.`,
    ...(marketOriginal ? { marketOriginal } : {}),
  };
}

export function extensionSummary(
  item: ExtensionSummaryItem,
  locale: ExtensionSummaryLocale,
): ExtensionSummaryResult {
  return firstPartySummary(item, locale) ?? fallbackSummary(item, locale);
}
