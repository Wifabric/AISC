#!/usr/bin/env python3
"""i18n key 使用率检查（本地门禁用）。

规则：
1. zh-CN.ts 与 en-US.ts 的顶层 key 集合必须一致（一处缺 key 即红）。
2. 每个顶层 key 必须至少在 workbench/src 被引用一次（t("key") /
   t('key') / $t("key") / i18n.t("key")），孤儿 key 即红。
动态 key（t(`prefix.${x}`)）不在本次覆盖范围，确有需要再扩展。

退出码：0 = 全通过；1 = 有孤儿 key 或 key 集合不一致。
"""
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
i18n_dir = root / "workbench" / "src" / "i18n"
src_dir = root / "workbench" / "src"

KEY_RE = re.compile(r'^\s*"([A-Za-z0-9_.]+)"\s*:')

def i18n_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = KEY_RE.match(line)
        if m:
            keys.add(m.group(1))
    return keys

def main() -> int:
    zh = i18n_keys(i18n_dir / "zh-CN.ts")
    en = i18n_keys(i18n_dir / "en-US.ts")
    bad = False

    only_zh = zh - en
    only_en = en - zh
    if only_zh or only_en:
        bad = True
        if only_zh:
            print(f"[i18n] zh-CN 有但 en-US 缺：{sorted(only_zh)}")
        if only_en:
            print(f"[i18n] en-US 有但 zh-CN 缺：{sorted(only_en)}")

    # 收集 workbench/src 里所有 t("literal") / $t("literal") / i18n.t("literal")
    ref_re = re.compile(r"\bt\(\s*['\"]([A-Za-z0-9_.]+)['\"]")
    referenced: set[str] = set()
    for p in sorted(src_dir.rglob("*")):
        if p.suffix not in (".ts", ".vue"):
            continue
        if "i18n" in p.parts:  # 定义文件不算引用
            continue
        for m in ref_re.finditer(p.read_text(encoding="utf-8", errors="replace")):
            referenced.add(m.group(1))

    orphans = (zh | en) - referenced
    if orphans:
        bad = True
        print(f"[i18n] 孤儿 key（未在任何 t(...) 中被引用）：{sorted(orphans)}")

    if bad:
        return 1
    print(f"[i18n] OK：{len(zh)} keys，zh/en 一致，无孤儿")
    return 0

if __name__ == "__main__":
    sys.exit(main())
