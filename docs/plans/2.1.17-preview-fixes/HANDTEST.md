# Preview 修复逐批验收

## b1 市场更新检查

前置：Docker Desktop 运行。当前已打开隔离候选，主窗口标题为
`aisc217pfb1-workspace · Bash · AISC Workbench`，另有 `workspace-other` 窗口。
主工作区有 caveman 13 个技能、grill-me 1 个技能、frontend-design 插件 1.1.1；无需 Provider。
若已关闭，PowerShell 运行校验式启动器：

```powershell
$repo = 'C:\Users\wangyu\.codex\worktrees\217-b1-proxyless-extension-reliability\AISC'
& "$repo\release-staging\2.1.17-preview-b1\start-handtest.ps1"
```

若出现选择工作区，输入 `C:\pt\aisc217pfb1-workspace`→下一步；启动摘要→更改设置，
镜像选 `super-claude:2.1.17-preview-b1`→启动。不要启动旧安装目录的 Workbench。
预测试细节见 [PRETEST.md](PRETEST.md)，用户验收当前待确认。

1. **T1 检查更新**：左侧扩展→技能→检查更新，等待按钮恢复，再检查一次。
   理想：无 `cli op got non-envelope output: ''`；caveman 13项及另一技能组1项保留，
   C/X 状态不变。插件页仍有 frontend-design / 1.1.1，“暂无可靠版本源”表示上游
   没有可靠比较字段，不应伪称“已是最新”。
2. **T2 独立市场**：扩展市场→技能，输入 research→搜索→点击 research；MCP 搜
   github→点击 GitHub；插件搜 frontend→点击 frontend-design。
   理想：查询结束出现“已刷新/上次成功”，都有结果和详情，无原空输出错误；安装量
   是实时值可变化。模板简介与蓝框属 b2，本批只确认数据链路。
3. **T3 服务和隔离**：关闭市场再检查；切左侧服务，应有“宿主工具”和“注册服务”，
   无协议报错；切回扩展。到另一个 workspace-other 窗口→扩展→插件→检查更新，
   理想：第二工作区保持“暂无内容”；回主窗口 frontend-design / 1.1.1仍在。
   第二窗口若关闭，通过操作→从文件夹打开工作区选择
   `C:\pt\aisc217pfb1-workspace-other`，用同批镜像启动。
4. **T4 失败重试（agent 已预测试，用户可按需复核）**：仅主测试容器仍存在时，
   PowerShell 执行第一条命令→UI 扩展→检查更新→观察错误→执行第二条恢复→UI再检查。

   ```powershell
   docker exec aisc-wb-f8b0d568 mv /usr/local/bin/aisc-extensions-adapter /usr/local/bin/aisc-extensions-adapter.pfb1-backup
   # 观察失败后立即恢复，即使不继续测试也要执行下一条
   docker exec aisc-wb-f8b0d568 mv /usr/local/bin/aisc-extensions-adapter.pfb1-backup /usr/local/bin/aisc-extensions-adapter
   ```

   理想：失败含 `No such file or directory`，列表保留；恢复后再检查无错误且按钮恢复，
   无需重启。重开工作区使容器名变化时跳过固定命令，告知 agent 重新准备，不猜容器名。

异常：原错误复现、按钮卡住、隐藏真实错误、列表丢失/串工作区或后续调用失败均不通过。
请反馈“b1 通过”或 T 编号与实际文案。依 DEVELOP_WIKI §1.4，单批验收/明确放行后才进入 b2。
其它批次精确步骤在对应批实施前补齐。
