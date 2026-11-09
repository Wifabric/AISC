# AISC Workbench

## AISC Workbench 开发入口

本目录为 AISC 桌面端（Vue/TypeScript + Tauri/Rust），通过冻结 CLI 和容器运行 Claude/Codex。用户安装与使用见 [根 README](../README.md)，构建与版本规则见 [DEVELOP_WIKI](../DEVELOP_WIKI.md)，开发任务从 [活动计划](../docs/plans/README.md) 开始。安装器维护见 [NSIS README](src-tauri/nsis/README.md)。不要仅按下面的通用框架示例启动后就当作完整 AISC 交付；sidecar、bundle 与版本配对须按开发手册准备。

## 框架参考（历史模板）

This template should help get you started developing with Vue 3 and TypeScript in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Vue - Official](https://marketplace.visualstudio.com/items?itemName=Vue.volar) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
