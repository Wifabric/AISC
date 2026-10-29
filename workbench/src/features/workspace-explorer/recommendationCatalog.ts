import type { ExtensionsKind } from "../../stores/extensions";

export type RecommendationCategoryId =
  | "research"
  | "education"
  | "knowledge"
  | "visualization"
  | "writing"
  | "development";

export interface RecommendationCategory {
  id: RecommendationCategoryId;
  labelZh: string;
  labelEn: string;
  summaryZh: string;
  summaryEn: string;
}

export interface CategorizedRecommendation {
  category: RecommendationCategoryId;
  kind: ExtensionsKind;
  identity: string;
  query: string;
  name: string;
  sourceUrl: string;
  heat?: string;
  heatSource: "skills.sh" | "smithery" | "official-directory";
  summaryZh: string;
  summaryEn: string;
}

export const EXTENSION_RECOMMENDATION_CATEGORIES = [
  {
    id: "research",
    labelZh: "科学研究",
    labelEn: "Research",
    summaryZh: "检索论文、复现实验、整理证据与跟踪学术来源。",
    summaryEn: "Find papers, reproduce experiments, and organize cited evidence.",
  },
  {
    id: "education",
    labelZh: "教育学习",
    labelEn: "Education",
    summaryZh: "构建课程、练习、知识卡与循序渐进的学习路径。",
    summaryEn: "Build courses, exercises, flashcards, and guided learning paths.",
  },
  {
    id: "knowledge",
    labelZh: "知识文档",
    labelEn: "Knowledge & documents",
    summaryZh: "读取、汇总和维护文档、知识库与技术资料。",
    summaryEn: "Read, summarize, and maintain documents and knowledge bases.",
  },
  {
    id: "visualization",
    labelZh: "数据可视化",
    labelEn: "Data visualization",
    summaryZh: "把数据整理成图表、仪表盘和清晰的解释叙事。",
    summaryEn: "Turn data into charts, dashboards, and clear explanatory narratives.",
  },
  {
    id: "writing",
    labelZh: "写作表达",
    labelEn: "Writing",
    summaryZh: "改进结构、语气、中文或英文表达，并去除模板化痕迹。",
    summaryEn: "Improve structure, tone, and voice while removing stock phrasing.",
  },
  {
    id: "development",
    labelZh: "开发工程",
    labelEn: "Development",
    summaryZh: "强化代码审查、调试、安全、架构和前端工程流程。",
    summaryEn: "Strengthen review, debugging, security, architecture, and frontend work.",
  },
] as const satisfies readonly RecommendationCategory[];

function skill(
  category: RecommendationCategoryId,
  identity: string,
  name: string,
  heat: string,
  summaryZh: string,
  summaryEn: string,
): CategorizedRecommendation {
  const repo = identity.split(":", 1)[0];
  return {
    category,
    kind: "skills",
    identity,
    query: name,
    name,
    sourceUrl: `https://github.com/${repo}`,
    heat,
    heatSource: "skills.sh",
    summaryZh,
    summaryEn,
  };
}

function mcp(
  category: RecommendationCategoryId,
  identity: string,
  name: string,
  query: string,
  heat: string | undefined,
  summaryZh: string,
  summaryEn: string,
): CategorizedRecommendation {
  return {
    category,
    kind: "mcp",
    identity,
    query,
    name,
    sourceUrl: `https://registry.smithery.ai/servers/${identity}`,
    heat,
    heatSource: "smithery",
    summaryZh,
    summaryEn,
  };
}

function plugin(
  category: RecommendationCategoryId,
  name: string,
  sourceUrl: string,
  summaryZh: string,
  summaryEn: string,
): CategorizedRecommendation {
  return {
    category,
    kind: "plugins",
    identity: `${name}@claude-plugins-official`,
    query: name,
    name,
    sourceUrl,
    heatSource: "official-directory",
    summaryZh,
    summaryEn,
  };
}

export const EXTENSION_RECOMMENDATIONS_BY_CATEGORY = {
  research: [
    skill("research", "mattpocock/skills:research", "research", "732132",
      "整理研究问题、检索材料并产出有来源支持的结论，是通用研究入口。",
      "Frame research questions, gather material, and produce sourced conclusions."),
    skill("research", "llllllllama/rigorpilot-skills:ai-research-explore", "ai-research-explore", "340646",
      "围绕 AI 研究项目做探索性分析，帮助形成可验证的实验路径。",
      "Explore AI research projects and shape verifiable experiment paths."),
    skill("research", "llllllllama/rigorpilot-skills:ai-research-reproduction", "ai-research-reproduction", "340280",
      "按科研复现流程核对环境、步骤和结果，减少不可重复实验。",
      "Check environments, steps, and results to make experiments reproducible."),
    skill("research", "google-deepmind/science-skills:literature-search-arxiv", "literature-search-arxiv", "3401",
      "检索 arXiv 论文并提取相关文献线索，适合预印本调研。",
      "Search arXiv papers and extract relevant literature leads."),
    skill("research", "google-deepmind/science-skills:literature-search-openalex", "literature-search-openalex", "3116",
      "通过 OpenAlex 检索学术作品、作者与机构关系。",
      "Search scholarly works, authors, and institutions through OpenAlex."),
    skill("research", "google-deepmind/science-skills:pubmed-database", "pubmed-database", "2729",
      "检索 PubMed 生物医学文献，获取论文摘要与相关线索。",
      "Search biomedical literature in PubMed for abstracts and related papers."),
    skill("research", "google-deepmind/science-skills:literature-search-europepmc", "literature-search-europepmc", "2581",
      "使用 Europe PMC 检索生命科学论文与开放全文信息。",
      "Search life-sciences papers and open full-text metadata in Europe PMC."),
    skill("research", "firecrawl/skills:firecrawl-research-index", "firecrawl-research-index", "24613",
      "把网页与论文资料转成可检索索引，支持后续引用与比对。",
      "Index web and paper material for later retrieval and comparison."),
    mcp("research", "pubmed", "PubMed", "pubmed", "43250",
      "查询 3600 万条生物医学引用，适合循证检索和论文摘要阅读。",
      "Query 36 million biomedical citations for evidence-based research."),
    mcp("research", "consensus", "Consensus", "academic research", "95",
      "用 AI 分析学术论文结论，快速提取研究发现与共识证据。",
      "Use AI-powered paper analysis to extract findings and research consensus."),
  ],
  education: [
    mcp("education", "microsoft/learn_mcp", "Microsoft Learn", "Microsoft Learn", "1272",
      "访问 Microsoft Learn 官方文档与学习路径，适合技术课程准备。",
      "Access official Microsoft Learn documentation and learning paths."),
    mcp("education", "clouatre-labs/math-mcp", "Math MCP Learning", "math learning", "579",
      "提供数学运算、统计、可视化与持久学习工作区。",
      "Provide math operations, statistics, visualizations, and study workspaces."),
    mcp("education", "vocab-voyage/vocab-voyage-mcp", "Vocab Voyage", "vocabulary", "1029",
      "用卡片、测验和游戏准备 SAT、GRE 等语言考试。",
      "Prepare for tests such as SAT and GRE with cards, quizzes, and games."),
    mcp("education", "flash-cards/flash", "Flash", "flashcards", undefined,
      "把笔记转成间隔重复卡片，由 Agent 生成并维护复习计划。",
      "Turn notes into spaced-repetition cards maintained by an agent."),
    mcp("education", "ltt2019051173/bloom-study-guide", "Bloom Study Guide", "study guide", undefined,
      "把学习对话整理成带要点、词汇和测验的学习指南。",
      "Turn learning chats into guides with key ideas, glossaries, and quizzes."),
    skill("education", "github/awesome-copilot:add-educational-comments", "add-educational-comments", "9243",
      "在代码中补充教学性注释，帮助新手理解实现意图。",
      "Add educational code comments that explain implementation intent."),
    skill("education", "samber/developer-relations-skills:developer-education-strategy", "developer-education-strategy", "11737",
      "规划开发者教育内容、课程层级和学习路径。",
      "Plan developer education content, course levels, and learning paths."),
    plugin("education", "learn-with-coursera",
      "https://github.com/coursera/skills",
      "把学习意图转成 Coursera 课程推荐与个性化学习方案。",
      "Turn learning intents into personalized Coursera course recommendations."),
    plugin("education", "explanatory-output-style",
      "https://github.com/anthropics/claude-plugins-public/tree/main/plugins/explanatory-output-style",
      "在回答中加入实现选择和代码库模式的教学解释。",
      "Add educational insights about implementation choices and codebase patterns."),
    plugin("education", "learning-output-style",
      "https://github.com/anthropics/claude-plugins-public/tree/main/plugins/learning-output-style",
      "以互动学习模式运行，让学习者在关键决策点参与编码。",
      "Use interactive learning mode with meaningful coding decision points."),
  ],
  knowledge: [
    skill("knowledge", "anthropics/skills:pdf", "pdf", "219011",
      "读取、创建和处理 PDF，适合论文、报告与表单资料整理。",
      "Read, create, and process PDFs for papers, reports, and forms."),
    skill("knowledge", "anthropics/skills:docx", "docx", "209217",
      "生成和编辑 Word 文档，保留排版、批注与审阅结构。",
      "Generate and edit Word documents while preserving layout and review state."),
    skill("knowledge", "mattpocock/skills:handoff", "handoff", "1064565",
      "把工作上下文整理成交接记录，降低会话与团队切换成本。",
      "Package working context into high-quality handoff records."),
    skill("knowledge", "mattpocock/skills:writing-for-agents", "writing-for-agents", "488277",
      "为 Agent 编写清晰任务说明、约束和验收标准。",
      "Write clear agent instructions, constraints, and acceptance criteria."),
    skill("knowledge", "firecrawl/skills:firecrawl-knowledge-base", "firecrawl-knowledge-base", "32627",
      "维护可检索知识库，把抓取内容转化为结构化资料。",
      "Maintain a searchable knowledge base from crawled material."),
    skill("knowledge", "firecrawl/skills:firecrawl-knowledge-ingest", "firecrawl-knowledge-ingest", "31427",
      "批量导入网页资料并建立可引用的知识索引。",
      "Ingest web material in batches and build citable knowledge indexes."),
    skill("knowledge", "openclaw/openclaw:summarize", "summarize", "22604",
      "快速摘要长文与会话内容，保留关键行动和限制。",
      "Summarize long material while preserving actions and constraints."),
    skill("knowledge", "tw93/waza:read", "read", "14178",
      "以结构化方式阅读资料，提取主题、要点和后续问题。",
      "Read material structurally to extract themes, points, and follow-ups."),
    mcp("knowledge", "upstash/context7-mcp", "Context7", "context7", undefined,
      "按软件版本查询官方文档和代码示例，减少过期 API 用法。",
      "Look up version-aware documentation and code examples for software libraries."),
    plugin("knowledge", "desktop-commander",
      "https://desktopcommander.app",
      "统一处理终端、进程、文件和 PDF/Office 等结构化资料。",
      "Work across terminal, processes, files, PDF/Office, and structured data."),
  ],
  visualization: [
    skill("visualization", "anthropics/knowledge-work-plugins:data-visualization", "data-visualization", "13923",
      "根据数据特征选择图表类型并生成清晰可视化。",
      "Choose chart types from data characteristics and create clear visuals."),
    skill("visualization", "antvis/chart-visualization-skills:chart-visualization", "chart-visualization", "6416",
      "使用 AntV 图表体系构建统计图与交互式可视化。",
      "Build statistical charts and interactive visuals with the AntV system."),
    skill("visualization", "anthropics/knowledge-work-plugins:create-viz", "create-viz", "5235",
      "快速创建可视化初稿，再按阅读目标调整比例与标注。",
      "Create visualization drafts and refine scale and annotation for readers."),
    skill("visualization", "wshobson/agents:data-storytelling", "data-storytelling", "17098",
      "把指标变化组织成有因果和结论的数据叙事。",
      "Organize metrics into causal, conclusion-driven data narratives."),
    skill("visualization", "wshobson/agents:kpi-dashboard-design", "kpi-dashboard-design", "16458",
      "设计 KPI 仪表盘的信息层级、指标定义和异常提示。",
      "Design KPI dashboard hierarchy, metric definitions, and exception cues."),
    skill("visualization", "wshobson/agents:grafana-dashboards", "grafana-dashboards", "13278",
      "构建 Grafana 面板、数据源查询与运维监控视图。",
      "Build Grafana panels, datasource queries, and operational views."),
    skill("visualization", "claude-office-skills/skills:chart-designer", "chart-designer", "5702",
      "设计适合报告与演示的图表样式、颜色和标注。",
      "Design report- and presentation-ready chart styling and annotation."),
    skill("visualization", "jimliu/baoyu-skills:baoyu-diagram", "baoyu-diagram", "15501",
      "把复杂概念转成中文流程图、架构图或关系图。",
      "Turn complex concepts into Chinese flow, architecture, or relationship diagrams."),
    skill("visualization", "github/awesome-copilot:power-bi-report-design-consultation", "power-bi-report-design-consultation", "9405",
      "咨询并优化 Power BI 报表结构、度量与页面布局。",
      "Consult on Power BI report structure, measures, and page layout."),
    skill("visualization", "wshobson/agents:service-mesh-observability", "service-mesh-observability", "10450",
      "可视化服务网格流量、依赖与可观测性指标。",
      "Visualize service-mesh traffic, dependencies, and observability metrics."),
  ],
  writing: [
    skill("writing", "mattpocock/skills:writing-beats", "writing-beats", "496835",
      "用节奏单位组织叙述，让文章推进自然且有张力。",
      "Organize prose with narrative beats for natural momentum."),
    skill("writing", "mattpocock/skills:writing-shape", "writing-shape", "496415",
      "先设计文章结构和信息形状，再展开段落表达。",
      "Design document structure and information shape before drafting."),
    skill("writing", "mattpocock/skills:writing-fragments", "writing-fragments", "495767",
      "以片段方式积累、组合和重写素材，减少空白页压力。",
      "Collect, combine, and rewrite fragments to reduce blank-page friction."),
    skill("writing", "mattpocock/skills:writing-great-skills", "writing-great-skills", "306548",
      "编写高质量 Skill 说明，使触发条件和任务边界更清晰。",
      "Write strong skill instructions with clear triggers and task boundaries."),
    skill("writing", "yuan1z0825/nature-skills:nature-writing", "nature-writing", "15947",
      "按 Nature 风格组织科学表达的论证、结果与讨论。",
      "Organize scientific argumentation, results, and discussion in Nature style."),
    skill("writing", "yuan1z0825/nature-skills:nature-polishing", "nature-polishing", "17803",
      "润色科研英语，改善精确性、逻辑连接和学术语气。",
      "Polish research English for precision, cohesion, and academic tone."),
    mcp("writing", "manavm/zero-slop", "Zero Slop", "writing editor", undefined,
      "删除模板化措辞、重复句式和常见 AI 腔，让草稿更像人写。",
      "Cut stock phrases, repetition, and AI-sounding patterns from drafts."),
    mcp("writing", "theserverlessdev/wsc", "Writing Style Checker", "style checker", "286",
      "检查文体、语法与 AI 痕迹，并给出可执行修改建议。",
      "Check style, grammar, and AI tells with actionable editing suggestions."),
    mcp("writing", "prose-coach/prose-coach", "Prose Coach", "prose editing", undefined,
      "以确定性规则标记常见写作模式，帮助形成稳定文风。",
      "Flag common writing patterns deterministically to build a stable voice."),
    plugin("writing", "canva",
      "https://www.canva.com",
      "创建、编辑和审查 Canva 设计，并进行品牌与尺寸检查。",
      "Create, edit, and review Canva designs with brand and sizing checks."),
  ],
  development: [
    plugin("development", "superpowers",
      "https://github.com/obra/superpowers",
      "提供头脑风暴、TDD、系统调试、子代理与代码审查工作流。",
      "Provides brainstorming, TDD, systematic debugging, subagents, and review workflows."),
    plugin("development", "code-review",
      "https://github.com/anthropics/claude-plugins-public/tree/main/plugins/code-review",
      "用多专门 Agent 审查 PR，并按置信度过滤误报。",
      "Reviews pull requests with specialized agents and confidence filtering."),
    plugin("development", "chrome-devtools-mcp",
      "https://github.com/ChromeDevTools/chrome-devtools-mcp",
      "控制真实 Chrome 检查网络、控制台、性能与页面状态。",
      "Control live Chrome to inspect network, console, performance, and pages."),
    plugin("development", "semgrep",
      "https://github.com/semgrep/mcp-marketplace.git",
      "在编码循环中实时检测安全漏洞并指导修复。",
      "Catch security vulnerabilities in real time and guide fixes."),
    skill("development", "mattpocock/skills:code-review", "code-review", "815431",
      "审查代码正确性、边界条件和可维护性，并给出优先级建议。",
      "Review correctness, edge cases, and maintainability with prioritized advice."),
    skill("development", "pbakaus/impeccable:impeccable", "impeccable", "369445",
      "提升界面完成度与细节质量，适合发布前 UI 打磨。",
      "Raise interface finish and detail quality before release."),
    skill("development", "vercel-labs/agent-skills:vercel-react-best-practices", "vercel-react-best-practices", "849926",
      "应用 React 与 Next.js 最佳实践，优化组件结构与数据流。",
      "Apply React and Next.js best practices to component structure and data flow."),
    skill("development", "llllllllama/rigorpilot-skills:safe-debug", "safe-debug", "340211",
      "按假设验证方式调试，避免无证据的连串修补。",
      "Debug through tested hypotheses instead of speculative patches."),
    skill("development", "llllllllama/rigorpilot-skills:explore-code", "explore-code", "340288",
      "系统探索陌生代码库，快速定位职责、数据流与风险。",
      "Systematically explore unfamiliar code to locate responsibilities and risks."),
    skill("development", "mattpocock/skills:domain-modeling", "domain-modeling", "902838",
      "梳理业务概念、不变量与边界，建立更稳的领域模型。",
      "Clarify business concepts, invariants, and boundaries for stable domain models."),
  ],
} as const satisfies Record<RecommendationCategoryId, readonly CategorizedRecommendation[]>;

export const CATEGORIZED_EXTENSION_RECOMMENDATIONS: readonly CategorizedRecommendation[] =
  EXTENSION_RECOMMENDATION_CATEGORIES.flatMap(({ id }) => EXTENSION_RECOMMENDATIONS_BY_CATEGORY[id]);
