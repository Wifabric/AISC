# 批 6：构建网络（宿主 TUN 代理下构建失败）——反馈 #1 履约

> 状态：计划待用户验收（2026-09-23 立项）
> 来源：反馈站 20260922-构建镜像时网络异常-匿名（affects 3；「本机始终保持
> TUN 代理模式，初次构建镜像 cc-switch 失败退回保守方案；选择配置容器 TUN
> 后构建成功」；开发者已回复「下版本排查修复」，本批即履约；D-1 纳入）
> 方法：ultracode workflow（研究员读两份构建日志 a1/a2 + 截图图像分析 +
> 代码；evidence/alt 双镜头核验 verdict 均 corrected——a1 定性、yazi 文件名、
> glob 简化改法、D-12 张力四处修正已并入）
> 对应 target：docs/todo.md「v2.1.14-target」反馈 #1 条目
> 范围升级（2026-09-23 D-11 用户裁定）：npm 四包连带预置 + 「无论什么网络
> 条件保底完成构建」——保底专项调研（Dockerfile 全触点 / 离线机制 /
> 条件矩阵 / 体积核算）结论并入本档后实施，本档 §2 方案为已定底座

## 1. 根因（日志 + 代码 + devlog 三重印证，置信 H1）

- **H1（高）**：宿主 Mihomo TUN 透明代理**不覆盖 Docker Desktop(WSL2)
  buildkit 容器的出站流量**，容器内是直连出口，GitHub 生态被墙。证据：
  两次构建国内源全通（apt 清华、npm 淘宝），全部 GitHub/镜像站请求呈典型
  直连被阻形态——a1:1107 ghfast.top 60s 仅 1.8MB/7.9MB（≈30KB/s 超时）、
  a1:1138 DNS NXDOMAIN、a1:1151 SSL timeout；a2:227/235/239/243 TLS 握手
  RST、a2:261 github.com 空响应。**不对称性即根因**：a1:1063 resolver
  成功注入 v5.10.5+sha256（api.github.com 从宿主经 TUN 可达）。devlog:523-524
  开发者 2026-09-17 自踩同款（「buildkit 对全部 GitHub 镜像 TLS 被掐（宿主
  正常）」）。
- **核验修正（定性）**：a1/a2 **均为钉版构建非保守方案**（a1:1063 非空
  CC_SWITCH_ASSET_URL）；用户看到的「cc-switch 失败」是**宿主侧 resolver
  网络失败警告**（main.py:1297-1312；错误串出处 cc_switch_resolver.py:174-182），
  S8b 降级只是提示；两份日志实际都死在 **yazi 下载**（Dockerfile:493-510，
  唯一无本地预置的下载步骤；curl `--max-time 60`（505 行）在慢速镜像下是
  直接死因——60s 仅得 23%）。
- **隐藏第二雷（保守分支 glob 缺陷）**：Dockerfile:440 保守分支按
  `v5.10.4` 硬编码 glob 匹配 downloads/ 预置，而降级路径 CC_SWITCH_* 六个
  build-arg 全不传（models.py:365-373：仅 resolve 成功才注入）→ 走 ARG
  默认 → glob 必落空 → 转容器内下载死链。真触发保守方案时会双重失败。
- **替代机理（alt，文案措辞依据）**：日志只能证明「容器出口未走代理节点」；
  同样自洽的第二机理是 TUN 已接管但分流规则把国产加速域归 DIRECT——对外
  文案按「构建期出口未走代理节点（未覆盖或规则直连）」表述。
- **H3（待追问 U-6）**：「配置容器 TUN 后构建成功」是因果还是巧合（无成功
  日志附件）。

## 2. 方案（D-8，分层）

| 层 | 内容 | 触达 |
| --- | --- | --- |
| P0 | yazi 预置进 `container/downloads/`：跑 `bash scripts/stage-npm.sh --yazi` 提交产物（**yazi-x86_64-unknown-linux-musl-v25.2.26.zip**，约 7.9MB——核验修正文件名：三元组+v 前缀）；Dockerfile:496-500 预置分支零改动即生效（mihomo/geodata/cc-switch 已实证预置即 0.5s 过关） | downloads/ + git |
| P0b | 保守分支对齐预置：Dockerfile:440 glob 去版本号（`cc-switch-cli-*-linux-${cs_arch}-musl.tar.gz \| sort -V \| tail -1`）——核验给的最简改法，替代研究员的 ARG 联动方案；该分支已有「fallback 形态无 pin 校验」显式警告（447-449） | Dockerfile 一行 |
| P0c | yazi / cc-switch 下载 `curl --max-time` 60→180-300s（慢速镜像下 60s 必死的直接止血） | Dockerfile 两处 |
| P1 | 构建失败网络诊断归因：build.py/main.py 在 docker exit 4 路径识别 stderr 的 curl (6)/(28)/(35)/(52) + 「下载失败」模式 → `build.failed` 事件附加结构化 `diagnostics`（network 归因 + 三出路建议），Workbench 失败卡片渲染为可点动作（重试/预置/文档） | main.py:1297-1386 / build.py:490-561 / 前端卡片 |
| P1b | Workbench 构建界面暴露既有 `GH_PROXY` build-arg（架构化的显式同意通道；符合 D-12「不未经同意改写用户网络」与 network.ts 契约「never touch host proxy」） | runtime.rs:1412 argv / 前端 |
| 不做 | P2 宿主代理自动探测注入（降 opt-in 暂不做）；P4 构建期容器 TUN sidecar（不立项）。npm 四包预置已由 D-11 裁定纳入（并入保底专项实施） | — |

## 3. 裁决边界（核验确认无冲突）

- P0 不破「镜像零预置」裁决（2.1.12 D-1 那条指 **provider 预配置模板**；
  downloads/ 入 git 是 v1.2.3 起自包含惯例，devlog:2303-2306）；
- P1b 不破 2.1.13 D-12 与 network.ts 契约（用户显式填代理，非自动改写）。
- D-11 后本批升级为「网络保底构建」：npm 四包 + yazi 等全触点预置、
  resolver 离线 manifest 接入、条件矩阵降级链——专项调研结论并入本档 §2。

## 4. 待用户

~~U-1~~ 已裁定（D-11）；~~U-7~~ 已回执（2026-09-23）；U-6 追问已随回执
发出，等用户答复（不阻塞 P0 落地）。

## 5. 验收

见 [HANDTEST.md](HANDTEST.md) T6（模拟无预置失败诊断字段 → 补预置后 0.5s
级过关 → Workbench 失败卡片动作 → 全预置离线 69 层绿回归）。
