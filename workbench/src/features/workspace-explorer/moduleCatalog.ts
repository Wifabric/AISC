import type { ExtensionModuleDefinition } from "../../lib/ipc";

// D-17: ship definitions offline; member payloads are installed online on Apply.
export const BUILTIN_EXTENSION_MODULES: readonly ExtensionModuleDefinition[] = [
  { id: "aisc-research-basics-v1", name: "科研基础", members: [
    { kind: "skills", identity: "google-deepmind/science-skills:literature_search_arxiv", name: "arXiv 文献检索", source_url: "https://github.com/google-deepmind/science-skills/tree/main/skills/literature_search_arxiv" },
    { kind: "skills", identity: "google-deepmind/science-skills:literature_search_openalex", name: "OpenAlex 学术检索", source_url: "https://github.com/google-deepmind/science-skills/tree/main/skills/literature_search_openalex" },
  ] },
  { id: "aisc-development-basics-v1", name: "开发基础", members: [
    { kind: "skills", identity: "obra/superpowers:systematic-debugging", name: "系统化调试", source_url: "https://github.com/obra/superpowers/tree/main/skills/systematic-debugging" },
    { kind: "skills", identity: "obra/superpowers:test-driven-development", name: "测试驱动开发", source_url: "https://github.com/obra/superpowers/tree/main/skills/test-driven-development" },
  ] },
];
