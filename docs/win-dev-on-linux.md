# 在 Linux 上开发 Windows 端：全流程手册

> 建立日期：2026-09-14。场景：开发机从 zh-CN Windows 迁移到 Arch Linux 后，继续开发
> AISC Workbench（Tauri 2 + Vue 3 + Rust 桌面端），并在本机 KVM 的 Windows 虚拟机里完成
> Windows 端验证。本文记录一次性搭建、日常循环和踩坑经验，是 Hyper-V "k3" 测试机流程
> （`scripts/*-k3-vm.ps1` 时代的等价物）在 Linux 上的继任者。

## 0. 总览

```text
┌─ Arch Linux 宿主机 ─────────────────────────────────────────────┐
│ develop 分支开发                                                  │
│   bash scripts/local-gates.sh   # pytest + cargo + vitest + tsc  │
│   （Linux 可承载 ~95% 开发；Windows 专属代码全部 cfg(windows) 门控）│
│        │ git push origin develop                                 │
│        ▼                                                         │
│ GitHub Actions                                                   │
│   nsis-installer.yml → AISC Workbench_*_x64-setup.exe            │
│        │ gh run download                                         │
│        ▼                                                         │
│ scp 进 VM → 静默安装 → smoke_installer.ps1 → 结果回报             │
└──────────────────────────────────────────────────────────────────┘
        ▲ SSH (密码走 askpass，凭据在 /mnt/data/vm/aisc-win11/credentials)
┌─ KVM 虚拟机 aisc-win11 ─────────────────────────────────────────┐
│ Windows 11 25H2 zh-CN（不激活）· WinRE 可断点续装                  │
│ 8 vCPU / 12G / 120G qcow2 · q35 + OVMF SecureBoot + TPM2.0       │
│ host-passthrough（嵌套虚拟化开启，为 Docker Desktop 预留）          │
│ SATA 磁盘 + virtio 网卡 · 本地账户 aisc（管理员）                  │
└──────────────────────────────────────────────────────────────────┘
```

## 1. Linux 端一次性环境搭建

### 1.1 开发工具链（全部用户级安装，不动系统）

| 组件 | 安装方式 | 说明 |
|---|---|---|
| Python venv | `python -m venv .venv && pip install -e ".[dev]"` | 仓库根 `.venv`；系统 Python 3.14 可用 |
| Rust | `curl https://sh.rustup.rs \| sh -s -- -y --profile minimal` | `~/.cargo/bin` |
| Node | nvm（`nvm install 22`）+ 仓库根 `.nvmrc` | 锁 22 与 CI 一致，见 1.2 |
| Tauri 系统依赖 | Arch 一般已有：webkit2gtk-4.1 / libayatana-appindicator / librsvg / base-devel | 缺什么 `pacman -S` 补 |
| KVM 栈 | qemu-full / libvirt / virt-manager / swtpm / libosinfo | 检查 `cat /sys/module/kvm_intel/parameters/nested` 为 `Y`（Docker Desktop in VM 需要） |

### 1.2 本机三个环境坑（都在 `scripts/local-gates.sh` 内置了修复）

1. **npm registry**：`package-lock.json` 的 resolved 指向 npmmirror，npm 12 直接 `npm ci`
   会报 "Fetching packages of type remote have been disabled"。
   **修**：`npm ci --registry=https://registry.npmmirror.com`。
2. **zh_CN locale**：CLI 的 `help_i18n` 会把 argparse help 译成中文，而契约测试断言英文
   `"usage:"`（`tests/features/test_runtime_json_contract.py::...bare_runtime...`）。
   **修**：跑测时 `LC_ALL=C.UTF-8 LC_MESSAGES=C.UTF-8 LANG=C.UTF-8 LANGUAGE=en`。
3. **Node ≥26 的实验性 localStorage**：原生全局（值为 undefined）遮蔽 vitest jsdom 注入的
   localStorage，`panelLayout.test.ts` 9 个用例全挂。**修**：用 nvm 的 Node 22（根治），
   或 `NODE_OPTIONS=--no-experimental-webstorage`。

### 1.3 nvm 与用户 `~/.npmrc` prefix 的冲突

用户 `~/.npmrc` 若有 `prefix=`（系统 Node 免 sudo 装全局的常见配置），`nvm use` 会**无条件
拒绝**（nvm 对用户级 npmrc 的 prefix 检查不看值，项目级 .npmrc 也救不了）。两个选择：

- **推荐**：把 prefix 挪到系统 npm 的 globalconfig（`npm config get globalconfig`，Arch 上
  是 `/etc/npmrc`）。语义完全不变（系统 npm -g 仍装 `~/.npm-global`），nvm 管的 npm 读自己
  版本目录下的 etc/npmrc，互不干扰：
  ```bash
  sudo sh -c 'echo "prefix=/home/<user>/.npm-global" > /etc/npmrc'
  sed -i '/^prefix=/d' ~/.npmrc
  ```
- 或绕过：脚本里直接把 `$NVM_DIR/versions/node/v22.x/bin` 前置 PATH（`local-gates.sh` 就是
  这么做的，不依赖上面的迁移）。

### 1.4 门禁

```bash
bash scripts/local-gates.sh        # = local-gates.ps1 的 Linux 对等版
# 1) pytest（忽略 integration） 2) cargo test --lib 3) vitest run 4) vue-tsc --noEmit
# 全绿输出 LOCAL GATES: ALL GREEN
```

cargo 编译需要 sidecar 占位（CI 同款做法）：
```bash
mkdir -p workbench/src-tauri/binaries workbench/src-tauri/nsis/bundle/aisc-bundle
touch workbench/src-tauri/binaries/aisc-x86_64-unknown-linux-gnu
# 真 sidecar：bash scripts/build-cli.sh（产物 dist/aisc-x86_64-unknown-linux-gnu）
```

## 2. Windows 测试虚拟机（一次性构建）

### 2.1 物料

```text
/mnt/data/iso/Win11_25H2_zh-CN_x64.iso     # zh-CN Windows 11（对齐真实用户环境：
                                            #   GBK 控制台、zh locale 正是历史 bug 高发区）
/mnt/data/iso/virtio-win.iso               # fedorapeople stable（网卡驱动等）
/mnt/data/vm/aisc-win11/answer-root/autounattend.xml   # 无人值守应答
/mnt/data/vm/aisc-win11/answer.iso         # xorriso 打包的应答盘（第 3 光驱）
/mnt/data/vm/aisc-win11/credentials        # VM 密码（600 权限）
/mnt/data/vm/aisc-win11/vm.sh              # 访问工具（ip/state/ssh/scp）
/mnt/data/vm/aisc-win11/askpass.sh         # SSH_ASKPASS 免交互
```

### 2.2 建机命令

```bash
virt-install --connect qemu:///system \
  --name aisc-win11 --os-variant win11 --vcpus 8 --memory 12288 \
  --cpu host-passthrough --machine q35 \
  --boot uefi,firmware.feature0.name=secure-boot,firmware.feature0.enabled=yes \
  --features smm=on --tpm model=tpm-crb,backend.type=emulator,backend.version=2.0 \
  --disk path=/mnt/data/vm/aisc-win11/disk.qcow2,format=qcow2,size=120,bus=sata,discard=unmap \
  --cdrom /mnt/data/iso/Win11_25H2_zh-CN_x64.iso \
  --disk path=/mnt/data/iso/virtio-win.iso,device=cdrom,readonly=on \
  --disk path=/mnt/data/vm/aisc-win11/answer.iso,device=cdrom,readonly=on \
  --network network=default,model=virtio \
  --channel unix,target.type=virtio,target.name=org.qemu.guest_agent.0 \
  --graphics spice,listen=none --video virtio --noautoconsole
```

启动后 OVMF 卡 "Press any key to boot from CD or DVD"（无限等待），用 QEMU monitor 远程按键：

```bash
virsh qemu-monitor-command aisc-win11 --hmp 'sendkey spc'   # 空格 → 出启动菜单
sleep 1.5
virsh qemu-monitor-command aisc-win11 --hmp 'sendkey ret'   # 第 1 次会被 BdsDxe 吃掉
sleep 3
virsh qemu-monitor-command aisc-win11 --hmp 'sendkey ret'   # 第 2 次才真正从 DVD 引导
```

**关键：建机后立刻把重启策略改成自动重启**（virt-install 默认 `on_reboot=destroy`，
Windows setup 安装中段的第一次温重启会撞上它直接把域关掉——这就是"装到一半 VM 莫名
关机"的根因；且 libvirt 拒绝只改 on_poweroff 不改 on_reboot 的组合，必须两个一起）：

```bash
virsh -c qemu:///system dumpxml aisc-win11 > /tmp/x.xml
sed -i -e 's|<on_poweroff>destroy</on_poweroff>|<on_poweroff>restart</on_poweroff>|' \
       -e 's|<on_reboot>destroy</on_reboot>|<on_reboot>restart</on_reboot>|' /tmp/x.xml
virsh -c qemu:///system define /tmp/x.xml
# live 配置要生效需 destroy+start 一次——务必趁安装早期复制阶段做（<5 分钟内），
# 晚期（specialize 阶段）硬断电会把 setup 打进"计算机意外地重新启动"脏状态死循环
```

之后全自动：分区 → 装系统（期间多次重启，无需干预）→ OOBE 跳过 → 首次登录执行
FirstLogonCommands（关休眠 → 装 virtio-win guest tools → 启用 OpenSSH server → 开 RDP →
写 C:\provision-done.txt）。SSH 端口通即就绪（OpenSSH capability 从 Windows Update 下载，
首次约需数分钟）。

### 2.3 autounattend.xml 要点（完整文件在 `/mnt/data/vm/aisc-win11/answer-root/`）

- **必须带 UTF-8 BOM**（本流程踩过的最大坑，见 2.4）
- zh-CN 全套 locale；通用 Pro 密钥 `VK7JG-NPHTM-C97JM-9MPGT` 选版本（不激活）
- GPT 分区表（EFI 300M / MSR 128M / C: 扩满）；`WillWipeDisk`
- 本地管理员 `aisc` + AutoLogon 1 次
- FirstLogonCommands 里 cmd 的 `%d` **不要**写成 `%25d`（unattend 无 URL 转义语境）

### 2.4 坑清单（每一条都实际踩过）

| # | 症状 | 根因 | 解法 |
|---|---|---|---|
| 1 | autounattend 完全不生效，setup 进交互界面 | XML 无 BOM 被 setup **静默忽略** | 文件头加 BOM（`printf '\xEF\xBB\xBF'`） |
| 2 | 磁盘列表为空，装不了 | WinPE 无 virtio-blk 驱动 | 磁盘用 `bus=sata`；网卡 virtio 无妨（驱动由 guest tools MSI 装） |
| 3 | 冷启动卡 "Press any key..."，CPU 空转 | OVMF 无启动项时 el-torito 无限等键 | monitor `sendkey` 序列（见 2.2） |
| 4 | sendkey ret 一次无效 | 第一次回车被 BdsDxe 处理器消费 | 连发两次 |
| 5 | 安装中段 VM 莫名 shut off | **根因已定**：virt-install 默认 `on_reboot=destroy`，Windows setup 的中段温重启直接把域关掉 | 建机后立刻按 2.2 改 restart/restart；已关掉的 `virsh start` 续装即可 |
| 5b | setup 报"计算机意外地重新启动…安装无法继续"并重启循环 | 安装晚期（specialize 后）硬断电/destroy 留下脏状态 | 只能在早期复制阶段做 destroy+start；晚期只能整个重来（换新 qcow2） |
| 5c | setup 问"继续升级 / 全新安装" | 磁盘上有上一次的残留安装 | 按 `N`（全新安装），autounattend 的 WillWipeDisk 会清盘 |
| 6 | xorriso 重打 answer.iso 报 SORRY | 输出文件已存在 | 先 `rm` 旧件 |
| 7 | SPICE 下 `virsh screenshot` 不可用 | 仅支持 VNC | `qemu-monitor-command --hmp 'screendump /tmp/x.ppm'` + ffmpeg 转 png |
| 8 | SSH 命令输出中文乱码 | Windows 控制台 GBK vs 终端 UTF-8 | 测试命令尽量英文输出；这正是 CLI 侧 `serve _frame` GBK 帧事故（S2）的同源问题，VM 恰好是复现环境 |

### 2.5 日常操作速查

```bash
/mnt/data/vm/aisc-win11/vm.sh ip          # 取 IP（ARP）
/mnt/data/vm/aisc-win11/vm.sh state       # 域状态
/mnt/data/vm/aisc-win11/vm.sh ssh "dir"   # 免交互 SSH
/mnt/data/vm/aisc-win11/vm.sh scp a.exe "aisc@<ip>:C:/Users/aisc/Desktop/"
virsh start aisc-win11                     # 开机（sshd 已设自动启动）
virt-manager                               # 图形窗口（真人手测时用）
```

## 3. 日常测试循环

```bash
# ① 开发 + 门禁（Linux 本地）
bash scripts/local-gates.sh

# ② 推送触发 CI
git push origin develop        # nsis-installer.yml 打 Windows 包（vendor/** 在路径过滤内）

# ③ 等 CI 绿 + 下载安装包
run=$(gh run list --workflow nsis-installer.yml --branch develop --limit 1 --json databaseId \
      --jq '.[0].databaseId')
gh run watch $run
gh run download $run -n aisc-workbench-windows-nsis -D /mnt/data/vm/artifacts/<sha>

# ④ 推进 VM 并静默安装（NSIS：/S；安装目录 %LOCALAPPDATA%\AISC Workbench）
ip=$(/mnt/data/vm/aisc-win11/vm.sh ip)
/mnt/data/vm/aisc-win11/vm.sh scp "/mnt/data/vm/artifacts/<sha>/AISC Workbench_*-setup.exe" "aisc@$ip:Desktop/setup.exe"
/mnt/data/vm/aisc-win11/vm.sh ssh 'C:\Users\aisc\Desktop\setup.exe /S'
```

注意：`packaging/windows/smoke_installer.ps1` 是**旧 Inno 安装器**（`/VERYSILENT`、
`Programs\AISC`）的冒烟，不适用于 Workbench NSIS 包；NSIS 的深度冒烟（G-18 PATH 冲突、
REG_EXPAND_SZ、升级/卸载保留）已在 `nsis-installer.yml` 的 windows-2022 runner 内联执行，
VM 侧负责的是"真 Windows + 真 GUI"这一层（见 3.1）。

### 3.1 VM 侧验收清单（2026-09-14 首轮实测全过）

1. 布局：`%LOCALAPPDATA%\AISC Workbench\` 下 `workbench.exe`（主程序）、`aisc.exe`
   （sidecar，注意安装后不带 target triple 后缀）、`aisc-bundle\`、`wg-transcode.ps1`、
   `uninstall.exe`。
2. sidecar 冒烟：
   - `aisc.exe version --format json` → `aisc.cli/v1` envelope，version/capabilities 齐全；
     zh-CN GBK 控制台下 JSON 保持纯 ASCII（正是 S2 `_frame`/envelope `ensure_ascii` 修复
     保护的场景，此 VM 即复现环境）。
   - `aisc.exe build --dry-run --format json` → exit 0，docker argv 完整（CN mirror
     build-args、labels、Windows 路径正确）。
3. GUI：`Start-Process workbench.exe` 后进程存活；`virsh ... screendump` 可确认窗口渲染
   ——标题 "AISC Workbench"、左侧 rail + 菜单栏（操作/编辑/帮助）、状态区给出
   "AISC CLI 需要更新：2.1.11.dev0（开发版本）" 与 Provider 卡片。无 Docker 时应用正常
   展示可操作状态而非崩溃（对应 S2 验收项"稳定可操作错误"）。
4. 远程 SSH 输出中文乱码属预期（GBK 控制台 vs UTF-8 终端），验证命令尽量用英文输出。

## 4. 已知问题与边界

- **Docker Desktop in VM**：winget 安装本身成功，但启用 WSL2/Hyper-V 后的重启在本机
  （q35+OVMF SecureBoot+嵌套 KVM）上触发过一次"自动修复失败"（SrtTrail）。复现一次，
  未见系统性结论。**安装 Docker 前请先完成当轮安装包测试**，把它当作独立风险步骤；
  排查方向：Hyper-V hypervisor launch 与 OVMF 的交互、`bcdedit /set hypervisorlaunchtype off`
  后用 Docker 的 Hyper-V 后端替代 WSL2 后端。
- **NSIS 安装器只能由 CI 构建**（windows-2022 runner），Linux 本地无法验证 installer.nsi
  （workflow 注释原话）。`gh` 已登录即可拉产物。
- **vendor checksums**：改 `container/` 忘了 `tools/vendor-refresh.sh` 会红 CI
  （nsis 与 bundle 两个 workflow 的 Stage 步骤都会被挡）。local-gates.sh 会按改动面提示。
- 真 Windows 手测（ConPTY 手感、GBK 控制台、Docker Desktop 集成、安装器 GUI 交互）仍需
  virt-manager 窗口人工过一遍；SSH 能覆盖的是静默安装 + 进程级校验 + smoke 脚本。

## 5. 首轮全流程实测记录（2026-09-14）

| 环节 | 实测 |
|---|---|
| Linux 门禁 | ALL GREEN（pytest 1275 / cargo --lib 全过 / vitest 481/481 / vue-tsc 净） |
| vendor checksums 修复（8b0e38e） | 推送后 nsis CI 由连红转绿 |
| CI NSIS 构建（8b0e38e，run 34770092784） | ~14 分钟，产物 44,145,297 字节 |
| VM 无人值守安装 | ~40 分钟（含三次因探索踩坑重装；按本文流程一次 ~35 分钟） |
| VM 静默安装 + 3.1 验收 | 全过（envelope / dry-run / GUI 渲染见 3.1） |
| Docker Desktop in VM | 未纳入本轮（见第 4 节已知问题） |

## 6. 迁移与复刻 checklist（换机器时）

1. 装 1.1 的工具链，跑 1.4 门禁确认 ALL GREEN
2. 拷贝 `/mnt/data/vm/aisc-win11/`（answer-root、vm.sh、askpass.sh、credentials）与
   `/mnt/data/iso/` 两个 ISO
3. 按 2.2 建机（约 40 分钟无人值守）
4. 按 3.4–3.5 跑一轮安装包冒烟闭环
5. 首次 `gh auth login` + `git remote` 指向仓库
