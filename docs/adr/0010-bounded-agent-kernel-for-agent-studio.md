# Agent Studio 采用有边界的 Agent Kernel

X2Video v0.2 需要从固定流水线升级为能理解目标、制定计划、建立证据、做编辑决策、检查并局部修复成片的内容生产 Agent，同时保留 v0.1 已经可工作的 Python CLI、Tweet Card、TTS、FFmpeg 和 Publish Kit。

## Decision

1. 使用单一 `ContentDirectorAgent` 驱动显式状态机。Planner、Researcher、Curator、Script Critic、Visual Director、QC 和 Learner 是具有版本化输入输出的专业节点或 Tool，不进行无边界的多 Agent 对话。
2. 所有智能输出使用版本化 Pydantic Schema，并记录输入哈希、生产者版本、决策摘要、证据、置信度、风险和输出 Artifact；不保存隐藏思维链。
3. SQLite `RunStore` 是 Agent Run 的本地控制面，保存 Run、Goal、Plan、Task、Event、Tool Call、Artifact、Evidence、Decision、Quality Issue、Feedback、Memory、Metric 和 Prompt Version。媒体文件继续保存在现有文件系统路径。
4. 现有 `pipeline/` 通过 Tool Wrapper 复用。旧 `x2video run` 映射为 Compatibility Plan，旧命令和核心输出路径保持兼容。
5. 所有循环具有最大尝试、费用、时间和退出条件。预算耗尽或高风险/低置信度时保存状态并进入人工 Gate，而不是无限重试。
6. CLI、FastAPI 和 React Studio 只调用同一个 Application Service；UI 不复制业务规则，也不伪造 Agent 活动。
7. 外部推文、网页和转录均是不可信数据。进入模型上下文前进行隔离、长度控制和 Prompt Injection 风险标记；秘密信息必须在日志、Trace、数据库、Fixture 和截图前脱敏。
8. 默认终点仍是 Publish Kit 与 Gate 2。自动发布继续是 non-goal。

## State model

```text
INIT → PLAN → DISCOVER → RESEARCH → CURATE → WAIT_GATE_1
     → SCRIPT → SCRIPT_REVIEW → STORYBOARD → PRODUCE
     → QUALITY_REVIEW → REPAIR → WAIT_GATE_2 → COMPLETE
```

任一状态可以在明确策略下进入 `FAILED` 或 `CANCELED`。Repair 与 Script Review 最多自动循环两轮。

## Considered options

- **继续扩展固定 pipeline**：改动小，但无法可靠表达动态计划、人工 Gate、证据、局部失效、预算和 Replay。
- **引入自由多 Agent 会话框架**：展示上像 Agent，但难以复现、预算不可控，并与 ADR-0004 的确定性 Python 程序方向冲突。
- **以 Studio 前端作为编排中心**：会复制业务逻辑，破坏 CLI 和定时运行，无法作为单一事实来源。
- **把全部 Artifact 放入数据库**：不适合视频、音频和图片；文件系统更便于现有工具与人工检查。

## Consequences

- 新能力必须先有领域契约、存储迁移和 Application Service，Studio 在这些基础上实现。
- File-exists resume 在兼容模式中保留，但新 Run 的成功与恢复以 `RunStore` 状态和幂等键为准。
- 运行可观察、可取消、可恢复、可回放，代价是需要维护数据库迁移、Artifact 依赖和事件语义。
- Demo 和测试使用脱敏冻结 Fixture；实时 X、模型或 TTS 验证必须单独标注，不能替代离线验收。
- 本决策补充而不推翻 ADR-0001 至 ADR-0009。

