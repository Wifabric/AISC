import { describe, expect, it } from "vitest";
import { readingTurns, recordLink } from "../conversationReading";
import { renderRecordMarkdown } from "../recordMarkdown";
import type { ConversationReadMessage } from "../../../types";

function msg(ordinal: number, kind: ConversationReadMessage["kind"], text: string, role: ConversationReadMessage["role"] = "assistant", phase?: string): ConversationReadMessage {
  return { ordinal, kind, text, role, phase };
}

describe("record reading", () => {
  it("collects all execution and commentary in one fold per turn without hiding the answer", () => {
    const turns = readingTurns([
      msg(0, "message", "问题", "user"), msg(1, "reasoning", "想法"),
      msg(2, "message", "先查文件", "assistant", "commentary"), msg(3, "tool_use", "ls"),
      msg(4, "message", "回答一"), msg(5, "tool_use", "test"), msg(6, "message", "最终回答"),
      msg(7, "message", "下一个问题", "user"), msg(8, "message", "第二个答案"),
    ]);
    expect(turns).toHaveLength(2);
    expect(turns[0].activity.map(m => m.ordinal)).toEqual([1, 2, 3, 4, 5]);
    expect(turns[0].answers.map(m => m.text)).toEqual(["最终回答"]);
    expect(turns[1].activity).toHaveLength(0);
  });
  it("maps container/host/file URLs while rejecting unsafe schemes and traversal", () => {
    expect(recordLink("/root/app/docs/a.md:12", "C:\\project")).toEqual({ kind: "file", path: "docs/a.md" });
    expect(recordLink("file:///C:/project/a%20b.pdf", "C:\\project")).toEqual({ kind: "file", path: "a b.pdf" });
    expect(recordLink("https://example.com", "/ws")?.kind).toBe("web");
    for (const value of ["javascript:alert(1)", "../private", "/etc/passwd", "//evil/a", "file://server/share/a", "%2e%2e/secret"]) {
      expect(recordLink(value, "/ws")).toBeNull();
    }
  });
  it("splits a slash command from its reply and keeps user input and skill execution separate", () => {
    const turns = readingTurns([
      msg(0, "command", "/office-hours\n核对数据", "user"),
      { ordinal: 1, role: "user", kind: "skill", name: "office-hours", text: "Base directory for this skill: /root/skills/office-hours" },
      msg(2, "reasoning", "按技能核对", "assistant"),
      msg(3, "message", "核对完成", "assistant"),
      msg(4, "command", "/compact", "user"),
      { ordinal: 5, role: "assistant", kind: "compact", text: "This session is being continued from a previous conversation." },
      msg(6, "message", "继续", "user"),
    ]);
    expect(turns).toHaveLength(3);
    // User-provided content is the question; injected skill content is execution.
    expect(turns[0].questions.map(m => m.text)).toEqual(["/office-hours\n核对数据"]);
    expect(turns[0].activity.map(m => m.kind)).toEqual(["skill", "reasoning"]);
    expect(turns[0].answers.map(m => m.text)).toEqual(["核对完成"]);
    // /compact directive and its reply are split, never merged into one user turn.
    expect(turns[1].questions.map(m => m.text)).toEqual(["/compact"]);
    expect(turns[1].activity).toHaveLength(0);
    expect(turns[1].answers.map(m => m.text)).toEqual(["This session is being continued from a previous conversation."]);
    expect(turns[2].questions.map(m => m.text)).toEqual(["继续"]);
  });
  it("renders GFM, math, code and footnotes while rejecting executable markup", () => {
    const html = renderRecordMarkdown("# 标题\n\n|a|b|\n|-|-|\n|1|2|\n\n- [x] 完成\n\n$x^2$\n\n```js\nconst x = 1;\n```\n\n脚注[^1]\n\n[^1]: 内容\n\n<script>alert(1)</script>\n\n[bad](javascript:alert(1))");
    expect(html).toContain("<h1"); expect(html).toContain("<table");
    expect(html).toContain('type="checkbox"'); expect(html).toContain("katex");
    expect(html).toContain("hljs"); expect(html).toContain("footnote");
    expect(html).not.toContain("<script>"); expect(html).not.toContain('href="javascript:');
  });
});
