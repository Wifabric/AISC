/**
 * v2.1.13 (changes-page): build the nested projection tree shown in the
 * 变更 tab. A pure function over {path, type} rows so the git source and the
 * watcher fallback feed the SAME renderer (D-6: tree grouping is presentation,
 * never the v2.1.9-cut attribution taxonomy).
 *
 * Directory rows are synthesized from path prefixes; a directory that only
 * groups deleted children stays visible (vscode SCM shows the folder too).
 */

export interface ChangeRow {
  path: string;
  /** created | modified | deleted | renamed (ChangeBadge vocabulary). */
  type: string;
  /** git rename origin, when the row carries one. */
  renameFrom?: string;
}

export interface ChangeTreeNode {
  /** Directory name, or the file's basename at the leaf. */
  name: string;
  /** Workspace-relative path: files carry the full path; dirs carry the
   *  directory prefix ("" at the root level). */
  path: string;
  /** True for synthesized directory rows. */
  dir: boolean;
  type: string;
  renameFrom?: string;
  children: ChangeTreeNode[];
}

function badgeRank(type: string): number {
  // deleted first (most alarming), then renamed/modified/created
  const order: Record<string, number> = { deleted: 0, renamed: 1, modified: 2, created: 3 };
  return order[type] ?? 4;
}

function worse(a: string, b: string): string {
  return badgeRank(a) <= badgeRank(b) ? a : b;
}

/** Normalize a watcher/git row into a ChangeRow (drops ignored shapes). */
export function toChangeRow(raw: {
  path?: string;
  relative_path?: string;
  type?: string;
  change_type?: string;
  renameFrom?: string;
}): ChangeRow | null {
  const path = raw.path ?? raw.relative_path;
  if (!path) return null;
  return {
    path,
    type: raw.type ?? raw.change_type ?? "modified",
    renameFrom: raw.renameFrom,
  };
}

/**
 * Build the projection tree. `filter` is the shared search predicate
 * (already lowercase-matched by the caller); a file matching keeps its
 * ancestor chain visible.
 */
export function buildChangeTree(
  rows: ChangeRow[],
  filter: ((path: string) => boolean) | null = null,
): ChangeTreeNode[] {
  type Dir = {
    name: string;
    path: string;
    children: Map<string, Dir | { leaf: ChangeTreeNode }>;
  };
  const root: Dir = { name: "", path: "", children: new Map() };

  const ensureDir = (dir: Dir, seg: string, full: string): Dir => {
    const existing = dir.children.get(seg);
    if (existing && "children" in existing) return existing;
    const created: Dir = { name: seg, path: full, children: new Map() };
    dir.children.set(seg, created);
    return created;
  };

  for (const row of rows) {
    if (filter && !filter(row.path.toLowerCase())) continue;
    const segs = row.path.split("/").filter(Boolean);
    if (segs.length === 0) continue;
    let dir = root;
    for (let i = 0; i < segs.length - 1; i += 1) {
      dir = ensureDir(dir, segs[i], segs.slice(0, i + 1).join("/"));
    }
    dir.children.set(segs[segs.length - 1], {
      leaf: {
        name: segs[segs.length - 1],
        path: row.path,
        dir: false,
        type: row.type,
        renameFrom: row.renameFrom,
        children: [],
      },
    });
  }

  const convert = (dir: Dir): ChangeTreeNode[] => {
    const nodes: ChangeTreeNode[] = [];
    const dirs: ChangeTreeNode[] = [];
    for (const [seg, child] of dir.children.entries()) {
      if ("children" in child) {
        const node: ChangeTreeNode = {
          name: seg,
          path: child.path,
          dir: true,
          type: "dir",
          children: convert(child),
        };
        if (node.children.length > 0) dirs.push(node);
      } else {
        nodes.push(child.leaf);
      }
    }
    // vscode SCM order: directories first, files after; each alphabetical.
    dirs.sort((a, b) => a.name.localeCompare(b.name));
    nodes.sort((a, b) => a.name.localeCompare(b.name));
    return [...dirs, ...nodes];
  };

  return convert(root);
}

/** Aggregate the worst badge across a subtree (directory count chips). */
export function subtreeBadge(node: ChangeTreeNode): { count: number; worst: string } {
  if (!node.dir) return { count: 1, worst: node.type };
  let count = 0;
  let worst = "created";
  const visit = (n: ChangeTreeNode): void => {
    if (!n.dir) {
      count += 1;
      worst = worse(worst, n.type);
      return;
    }
    for (const c of n.children) visit(c);
  };
  visit(node);
  return { count, worst };
}

/** git porcelain XY -> ChangeBadge vocabulary (the watcher's 4 types). */
export function gitTypeOf(x: string, y: string): string {
  const code = `${x}${y}`;
  if (code.includes("R") || code.includes("C")) return "renamed";
  if (code.includes("D")) return "deleted";
  if (code.includes("A") || code === "??") return "created";
  if (code.includes("M") || code.includes("T")) return "modified";
  return "modified";
}
