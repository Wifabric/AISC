<script setup lang="ts">
import { computed } from 'vue';
const props = defineProps<{ text: string }>();
const emit = defineEmits<{ open: [path: string] }>();
const technical = /^(?:#{1,6}\s*(?:来源与记录|来源与修订依据|对话与维护约定)|[-\s]*(?:目标记录|协作约定来源|本轮约定来源|来源事件|所用\s*skill|最新修订|修订原始记录|关联依据|缺失依据|记录索引|本轮修订|v2记录索引|v2修订)[:：])/;
const blocks = computed(() => {
  const result: { lines: string[]; detail: boolean }[] = [];
  let sectionDetail = false;
  for (const line of props.text.split('\n')) {
    if (line.startsWith('<!--')) continue;
    if (/^#{1,6}\s/.test(line)) sectionDetail = technical.test(line);
    const last = result[result.length - 1];
    const detail = sectionDetail || technical.test(line) || /^> (从修订事件|请通过追加)/.test(line) || /^\s+- /.test(line) && !!last?.detail;
    if (last?.detail === detail) last.lines.push(line);
    else result.push({ lines: [line], detail });
  }
  return result;
});
function clean(line: string) {
  return line.replace(/^#{1,6}\s*/, '').replace(/^>\s?/, '')
    .replace(/\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b/gi, '当前会话')
    .replace(/\b(?:ui-interaction|source-session|revision-session|cp|chat)-[\w-]+/g, '相关记录');
}
function parts(line: string) {
  return line.split(/(\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean).map(text => {
    const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(text);
    return link ? { text: clean(link[1]), path: link[2], bold: false } : { text: clean(text.replace(/^\*\*|\*\*$|^`|`$/g, '')), path: '', bold: text.startsWith('**') };
  });
}
function safe(path: string) { return !/^(?:[a-z]+:|[/\\])/i.test(path) && !path.split(/[/\\]/).includes('..'); }
</script>

<template>
  <div class="topic-document">
    <component :is="block.detail ? 'details' : 'div'" v-for="(block, index) in blocks" :key="index" class="document-block">
      <summary v-if="block.detail">来源与依据（展开查看）</summary>
      <component :is="line.startsWith('# ') ? 'h2' : /^#{2,6} /.test(line) ? 'h3' : 'p'" v-for="(line, n) in block.lines" :key="n" :class="{ quote: line.startsWith('>') }">
        <template v-for="(part, p) in parts(line)" :key="p">
          <button v-if="part.path && safe(part.path)" class="document-link" @click="emit('open', part.path)">{{ part.text }}</button>
          <strong v-else-if="part.bold">{{ part.text }}</strong>
          <span v-else>{{ part.text }}</span>
        </template>
      </component>
    </component>
  </div>
</template>

<style scoped>
.topic-document { font-size: var(--font-xs); line-height: 1.75; overflow-wrap: anywhere; }
h2 { font-size: 1.2em; margin: 0 0 16px; } h3 { font-size: 1.05em; margin: 20px 0 8px; }
p { margin: 6px 0; white-space: pre-wrap; } p:empty { display: none; }
.quote { color: var(--text-muted); border-left: 2px solid var(--border); padding-left: 10px; }
details { margin: 14px 0; padding: 8px; border: 1px solid var(--border-2); border-radius: var(--radius-sm); }
summary { cursor: pointer; color: var(--text-muted); }
.document-link { background: none; border: 0; color: var(--accent); padding: 0; font: inherit; cursor: pointer; text-decoration: underline; }
</style>
