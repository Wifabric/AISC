import io, re

p = 'workbench/src/features/workspace-explorer/WorkspaceExplorer.vue'
s = io.open(p, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
L = nl

# 1) import changesTree helpers
anchor = 'import { buildSearchMatcher } from "../../lib/search";'
assert anchor in s, 'search import'
s = s.replace(anchor, anchor + L + 'import { buildChangeTree, gitTypeOf, subtreeBadge, type ChangeTreeNode } from "./changesTree";', 1)

# 2) script: replace changesFiltered comment+computed with dual-source computeds
old = L.join([
'/** 2.1.9 T6: the Changes panel is a FLAT list — the shared search matcher',
'  (substring > subsequence fuzzy, `/regex/` for patterns) is the only',
'  filter. Classification (kind sections/chips/attribution) was cut per',
'  user ruling: agent self-registration proved unreliable. */',
]).replace('  (substring', '  (substring')
# locate the actual block flexibly
pat = re.compile(r'/\*\* 2\.1\.9 T6: the Changes panel is a FLAT list.*?\}\)\;', re.S)
m = pat.search(s)
assert m, 'changesFiltered block not found'
new = L.join([
'/** v2.1.13 (D-6): dual-source changes rows. Git source (local repo + host',
'  git) shows `git status` entries; the watcher fallback keeps the historical',
'  session-log semantics. The tree grouping is presentation only — the',
'  v2.1.9-cut attribution taxonomy stays cut. Filter: the shared search',
'  matcher (substring > subsequence fuzzy, `/regex/` for patterns). */',
'const changeRows = computed(() => {',
'  if (explorer.changesSource === "git") {',
'    return explorer.gitEntries.map((e) => ({',
'      path: e.path,',
'      type: gitTypeOf(e.x, e.y),',
'      renameFrom: e.renameFrom,',
'    }));',
'  }',
'  const matcher = searchMatcher.value;',
'  const rows = explorer.unattributedEntries;',
'  if (matcher === null) return rows;',
'  return rows.filter((e) => matcher(e.relative_path.toLowerCase()) > 0)',
'    .map((e) => ({ path: e.relative_path, type: e.change_type }));',
'});',
'const changesTree = computed(() => {',
'  const matcher = searchMatcher.value;',
'  const filter = matcher === null ? null : (p: string) => matcher(p) > 0;',
'  return buildChangeTree(changeRows.value, filter);',
'});',
'/** Flattened (expanded-only) render rows — same idiom as the file tree. */',
'const changeExpanded = ref(new Set<string>());',
'function toggleChangeDir(node: ChangeTreeNode): void {',
'  const next = new Set(changeExpanded.value);',
'  if (next.has(node.path)) next.delete(node.path);',
'  else next.add(node.path);',
'  changeExpanded.value = next;',
'}',
'const changeTreeRows = computed(() => {',
'  const out: Array<{ node: ChangeTreeNode; depth: number }> = [];',
'  const visit = (nodes: ChangeTreeNode[], depth: number) => {',
'    for (const n of nodes) {',
'      out.push({ node: n, depth });',
'      if (n.dir && changeExpanded.value.has(n.path)) visit(n.children, depth + 1);',
'    }',
'  };',
'  visit(changesTree.value, 0);',
'  return out;',
'});',
'const changeSourceLabel = computed(() =>',
'  explorer.changesSource === "git"',
'    ? t("changes.source.git", { branch: explorer.gitBranch, n: changeRows.value.length })',
'    : t("changes.source.watcher", { n: changeRows.value.length }));',
'/** Unified diff line classification (±/@ prefixes) for the diff pane. */',
'const diffLines = computed(() => {',
'  const d = explorer.gitDiff;',
'  if (!d || d.binary) return [];',
'  return d.unified.split("\\n").map((line) => ({',
'    line,',
'    kind: line.startsWith("+") && !line.startsWith("+++")',
'      ? "add"',
'      : line.startsWith("-") && !line.startsWith("---")',
'        ? "del"',
'        : line.startsWith("@@") ? "hunk" : "ctx",',
'  }));',
'});',
'function onRowClick(node: ChangeTreeNode): void {',
'  if (node.dir) {',
'    toggleChangeDir(node);',
'    return;',
'  }',
'  onArtifactSelect(node.path);',
'  if (explorer.changesSource === "git") void explorer.openGitDiff(node.path);',
'}',
'function subtreeCount(node: ChangeTreeNode): number {',
'  return subtreeBadge(node).count;',
'}'])
s = s[:m.start()] + new + s[m.end():]

# 3) template: replace the flat list with source indicator + tree + diff pane
pat = re.compile(
    r'      <p v-if="!changesFiltered\.length" class="explorer-empty">' + re.escape(L) +
    r'.*?' + re.escape(L) +
    r'        <ChangeBadge v-if="badgeTypeOf\(u\.change_type\)" :type="badgeTypeOf\(u\.change_type\)!" />' + re.escape(L) +
    r'      \}' + re.escape(L) +
    r'      </div>' + re.escape(L),
    re.S)
m = pat.search(s)
assert m, 'artifacts flat list not found'
new = L.join([
'      <!-- v2.1.13 D-6: source indicator — git (authoritative, local repo)',
'           via read-only status/diff) or the watcher session-log fallback. -->',
'      <p class="changes-source" :class="\'src-\' + explorer.changesSource">',
'        {{ changeSourceLabel }}',
'      </p>',
'      <!-- D-11: the raw-file preview is gone for good. The pane below is',
'           DIFF-ONLY and exists solely in the changes context (git source). -->',
'      <div v-if="explorer.gitDiff" class="diff-pane">',
'        <div class="diff-head">',
'          <span class="diff-path">{{ explorer.gitDiff.path }}</span>',
'          <button class="explorer-mini" @click="explorer.closeGitDiff()">✕</button>',
'        </div>',
'        <p v-if="explorer.gitDiff.binary" class="note">{{ t("changes.diff.binary") }}</p>',
'        <pre v-else class="diff-body"><span',
'          v-for="(l, i) in diffLines"',
'          :key="i"',
'          :class="\'diff-\' + l.kind"',
'        >{{ l.line }}' + L + '</span></pre>',
'      </div>',
'      <p v-if="!changeRows.length" class="explorer-empty">',
'        {{ searchQuery ? t("explorer.searchNoMatch") : t("explorer.empty.artifacts") }}',
'      </p>',
'      <div class="change-tree">',
'        <div',
'          v-for="{ node, depth } in changeTreeRows"',
'          :key="(node.dir ? \'d:\' : \'f:\') + node.path"',
'          class="explorer-row change-row"',
'          :class="{ selected: !node.dir && selected === node.path }"',
'          :style="{ paddingLeft: 6 + depth * 12 + \'px\' }"',
'          @click="onRowClick(node)"',
'          @dblclick="!node.dir && explorer.openFile(node.path)"',
'          @contextmenu.prevent.stop="!node.dir && openMenuAt({ kind: \'file\', relativePath: node.path, renamable: nodeOf(node.path) !== null }, $event.clientX, $event.clientY)"',
'        >',
'          <span v-if="node.dir" class="change-twisty">{{ changeExpanded.has(node.path) ? "▾" : "▸" }}</span>',
'          <span class="explorer-name" :title="hostPath(node.path)">{{ node.name }}</span>',
'          <span v-if="node.dir" class="change-count">{{ subtreeCount(node) }}</span>',
'          <ChangeBadge v-else-if="badgeTypeOf(node.type)" :type="badgeTypeOf(node.type)!" />',
'        </div>',
'      </div>',
]) + L
s = s[:m.start()] + new + s[m.end():]

# 4) styles appended before </style>
styles = L.join([
'/* --- v2.1.13 changes-page: source indicator + projection tree + diff --- */',
'.changes-source {',
'  margin: 0 0 6px; padding: 2px 8px; font-size: var(--text-xs, 11px);',
'  color: var(--text-muted); border-left: 2px solid var(--border);',
'}',
'.changes-source.src-git { color: var(--text-2); border-left-color: var(--status-ok); }',
'.change-tree { min-width: 0; }',
'.change-row { display: flex; align-items: center; gap: 6px; }',
'.change-twisty { width: 12px; flex: 0 0 12px; color: var(--text-muted); }',
'.change-count { margin-left: auto; color: var(--text-muted); font-size: var(--text-xs, 11px); }',
'.diff-pane {',
'  border-top: 1px solid var(--border); margin-top: 6px; padding-top: 6px;',
'  max-height: 45%; overflow: auto;',
'}',
'.diff-head { display: flex; align-items: center; justify-content: space-between; gap: 6px; }',
'.diff-path { font-family: var(--font-mono); font-size: var(--text-xs, 11px); color: var(--text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }',
'.diff-body {',
'  margin: 4px 0 0; font-family: var(--font-mono); font-size: var(--text-xs, 11px);',
'  white-space: pre; overflow-x: auto; line-height: 1.35;',
'}',
'.diff-add { display: block; color: var(--status-ok); background: rgba(76, 175, 80, 0.10); }',
'.diff-del { display: block; color: var(--status-err); background: rgba(229, 83, 75, 0.10); }',
'.diff-hunk { display: block; color: var(--text-muted); }',
'.diff-ctx { display: block; color: var(--text-2); }',
]) + L
anchor = '</style>'
assert s.rstrip().endswith('</style>')
idx = s.rfind('</style>')
s = s[:idx] + styles + L + s[idx:]

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('vue ok')
