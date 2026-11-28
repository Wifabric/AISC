<script setup lang="ts">
/**
 * D-9 review fix: the user-visible Markdown view for a terminal pane.
 *
 * Pure presentation over `buildMarkdownLines` (markdownOutput.ts): code block
 * headers/summaries are click targets that emit `toggle-fold` (b11), path
 * segments emitted by `pathLinks` (b12) are anchors that emit `open-path`.
 * The live xterm byte stream is untouched — this view is an opt-in overlay.
 */
import type { MarkdownRenderedLine } from "./markdownOutput";
import type { TerminalPathTarget } from "./markdownRender";

defineProps<{ lines: MarkdownRenderedLine[] }>();

const emit = defineEmits<{
  (e: "toggle-fold", codeIndex: number): void;
  (e: "open-path", target: TerminalPathTarget): void;
}>();

function onLineClick(line: MarkdownRenderedLine): void {
  if (line.codeIndex !== null) emit("toggle-fold", line.codeIndex);
}
</script>

<template>
  <div class="md-output" data-testid="markdown-output">
    <div
      v-for="(line, li) in lines"
      :key="li"
      class="md-line"
      :class="{ 'md-code-header': line.codeIndex !== null, folded: line.folded }"
      :data-testid="line.codeIndex !== null ? 'md-code-header' : undefined"
      :data-code-index="line.codeIndex ?? undefined"
      :role="line.codeIndex !== null ? 'button' : undefined"
      :tabindex="line.codeIndex !== null ? 0 : undefined"
      @click="onLineClick(line)"
      @keydown.enter.prevent="onLineClick(line)"
    >
      <span v-if="line.codeIndex !== null" class="md-caret" aria-hidden="true">{{
        line.folded ? "▸" : "▾"
      }}</span>
      <template v-for="(seg, si) in line.segments" :key="si">
        <a
          v-if="seg.kind === 'link'"
          class="md-path-link"
          :href="seg.uri"
          :title="seg.text"
          data-testid="md-path-link"
          @click.stop.prevent="emit('open-path', seg.target)"
          >{{ seg.text }}</a
        >
        <span v-else :class="seg.kind === 'dim' ? 'md-dim' : undefined">{{ seg.text }}</span>
      </template>
    </div>
  </div>
</template>

<style scoped>
.md-output {
  height: 100%;
  overflow: auto;
  padding: 8px 12px;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: var(--font-xs, 12px);
  line-height: 1.5;
  color: var(--text);
  background: var(--bg);
  user-select: text;
}

.md-line {
  white-space: pre-wrap;
  word-break: break-word;
  min-height: 1.5em;
}

.md-code-header {
  cursor: pointer;
  user-select: none;
  border-radius: var(--radius-sm, 3px);
}

.md-code-header:hover,
.md-code-header:focus-visible {
  background: var(--surface-2);
  outline: none;
}

.md-caret {
  display: inline-block;
  width: 1.2em;
  color: var(--text-muted);
}

.md-dim {
  color: var(--text-muted);
}

.md-path-link {
  color: var(--accent);
  text-decoration: underline;
  cursor: pointer;
}
</style>
