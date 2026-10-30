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
  const href = String(tokens[idx].attrGet("href") ?? "");
  if (!/^https?:\/\//i.test(href) && !href.startsWith("#")) {
    tokens[idx].attrSet("data-record-href", href);
    tokens[idx].attrSet("href", "#");
  }
  return self.renderToken(tokens, idx, options);
};

export function renderRecordMarkdown(text: string): string {
  try {
    // MathML and generated KaTeX styles survive; record HTML is escaped upstream.
    return DOMPurify.sanitize(md.render(text), { ADD_ATTR: ["data-record-image", "data-record-href", "loading", "referrerpolicy"],
      FORBID_TAGS: ["script", "iframe", "object", "embed", "form"], FORBID_ATTR: ["srcset"] });
  } catch { return `<pre>${md.utils.escapeHtml(text)}</pre>`; }
}
