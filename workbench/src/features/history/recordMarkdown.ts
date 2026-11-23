import MarkdownIt from "markdown-it";
import footnote from "markdown-it-footnote";
import taskLists from "markdown-it-task-lists";
import texmath from "markdown-it-texmath";
import katex from "katex";
import DOMPurify from "dompurify";
import hljs from "highlight.js/lib/common";

const md = new MarkdownIt({ html: false, linkify: true, breaks: true,
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try { return hljs.highlight(code, { language: lang, ignoreIllegals: true }).value; } catch { /* plain escaped fallback */ }
    }
    return "";
  },
}).use(footnote).use(taskLists).use(texmath, {
  engine: katex, delimiters: ["dollars", "brackets"],
  katexOptions: { throwOnError: false, trust: false, strict: "ignore", maxExpand: 1000, maxSize: 20 },
});

// Relative and container file links are handled by the reader, never navigated.
md.validateLink = (url: string) => !/^(?:javascript|vbscript|data|blob):/i.test(url);
const imageRule = md.renderer.rules.image!;
md.renderer.rules.image = (tokens, idx, options, env, self) => {
  const token = tokens[idx];
  const src = String(token.attrGet("src") ?? "");
  if (!/^https?:\/\//i.test(src) && !/^data:image\/(?:png|jpeg|gif|webp);base64,/i.test(src)) {
    token.attrSet("data-record-image", src);
    token.attrSet("src", "");
  }
  token.attrSet("loading", "lazy"); token.attrSet("referrerpolicy", "no-referrer");
  return imageRule(tokens, idx, options, env, self);
};
md.renderer.rules.link_open = (tokens, idx, options, _env, self) => {
  let href = String(tokens[idx].attrGet("href") ?? "");
  const label = tokens[idx + 1]?.content ?? "";
  if (tokens[idx].markup === "linkify" && /^[\w.-]+\.(?:md|rs|py|js|ts|vue|json|toml|yaml|yml|sh|txt)$/i.test(label)) {
    href = label;
  }
  if (!/^https?:\/\//i.test(href) && !href.startsWith("#")) {
    tokens[idx].attrSet("data-record-href", href);
    tokens[idx].attrSet("href", "#");
  }
  return self.renderToken(tokens, idx, options);
};

/** Recognize path literals in prose and inline code after Markdown is sanitized. */
export function markRecordPaths(root: HTMLElement) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  while (walker.nextNode()) nodes.push(walker.currentNode as Text);
  const pattern = /(?:[a-z]:[\\/]|\.{0,2}[\\/])?(?:[\p{L}\p{N}_@.-]+[\\/])*[\p{L}\p{N}_@-][\p{L}\p{N}_.-]*\.[a-z][a-z0-9]{0,9}(?::\d+(?::\d+)?|#L\d+)?/giu;
  for (const node of nodes) {
    if (node.parentElement?.closest("a,pre,button,.katex")) continue;
    const fragment = document.createDocumentFragment();
    // Inline code delimits an entire path, including spaces and extensionless files.
    if (node.parentElement?.tagName === "CODE" && /[\\/]/.test(node.data) &&
        !/^[\w+.-]+:\/\//.test(node.data) && !/[\n`|<>"*?]/.test(node.data)) {
      const anchor = document.createElement("a");
      anchor.href = "#"; anchor.dataset.recordHref = node.data; anchor.textContent = node.data;
      node.replaceWith(anchor);
      continue;
    }
    let end = 0;
    for (const match of node.data.matchAll(pattern)) {
      const start = match.index!;
      const raw = match[0];
      fragment.append(node.data.slice(end, start));
      const a = document.createElement("a");
      a.href = "#"; a.dataset.recordHref = raw; a.textContent = raw;
      fragment.append(a);
      end = start + raw.length;
    }
    if (end) { fragment.append(node.data.slice(end)); node.replaceWith(fragment); }
  }
}

export function renderRecordMarkdown(text: string): string {
  try {
    // MathML and generated KaTeX styles survive; record HTML is escaped upstream.
    return DOMPurify.sanitize(md.render(text), { ADD_ATTR: ["data-record-image", "data-record-href", "loading", "referrerpolicy"],
      FORBID_TAGS: ["script", "iframe", "object", "embed", "form"], FORBID_ATTR: ["srcset"] });
  } catch { return `<pre>${md.utils.escapeHtml(text)}</pre>`; }
}
