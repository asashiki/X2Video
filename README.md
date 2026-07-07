# X2Video

抓取 X（Twitter）上某一领域（MVP：AI/科技圈）的热点推文，经两层筛选、双语卡片渲染、中文解说文案生成，自动合成竖屏短视频（抖音/B站），产出可直接上传的 Publish Kit。

**为什么做这个**：外网（尤其 X）上的优质热点内容与中文短视频平台之间存在信息差。这个项目把"发现热帖 → 翻译 → 解说 → 成片"的搬运链路自动化，人只保留两个把关点：选题和审片。

## 项目状态

方案设计已完成，处于按 issue 实现阶段。开发路线图见 [Issues](https://github.com/asashiki/X2Video/issues)（按里程碑 M1-M7 排序）。

MVP 范围：AI/科技圈领域、单推文视频起步（目标是多条推文的合集形态）、人工上传。后期方向（欢迎讨论与认领）：领域可配置、多内容源、英文版输出、剪映草稿导出等。

## 参与开发

欢迎任何形式的参与，包括与当前路线不同的想法：

- **有新点子/不同方案** → 直接开 issue 讨论。最终成品不必局限于现有设计，方向性分歧请对照 [docs/adr/](./docs/adr/) 里的决策记录来提，说清楚"为什么值得推翻"。
- **想认领任务** → 路线图 issues 按里程碑排序，评论认领即可；标注 `ready-for-agent` 的 issue 表示规格完整、可直接开工。
- **提 PR** → 命名与用词遵循 [CONTEXT.md](./CONTEXT.md) 词汇表；PR 描述里链接对应 issue。

## 必读文档

开工前按顺序读：

1. **[AGENTS.md](./AGENTS.md)** — agent 协作约定（issue 跟踪、triage 标签、TTS 配置约定）
2. **[CONTEXT.md](./CONTEXT.md)** — 领域词汇表（Candidate / Curation / Pick / Tweet Card / Digest / Gate / Publish Kit…），所有代码命名与文档用词以此为准
3. **[docs/adr/](./docs/adr/)** — 关键架构决策（数据源、产品形态、项目形态、合成路线、范围边界），实现时不得与 ADR 冲突；如需推翻，先在 issue 里讨论

## 管线概览

```
fetch（X API 拉取 + Hard Filter + Ledger 去重）
  → curate（LLM 价值评分 → candidates.md，Gate 1 人工勾选 / 可配直通）
  → card（双语推文卡片渲染）
  → script（N 条目合集解说文案，N=1 为单推文特例）
  → render（TTS 配音 + 合成 1080×1920 MP4 + Publish Kit）
  → final/（人工审片上传，Gate 2）
```

## 环境约定

- 最好用 Codex 或者 Claude Code 做开发，开发的时候注意不要出现国产模型的名字，不然Claude会被封号
- Python CLI 项目（`x2video` 命令），见 ADR-0004
- 凭据放仓库根目录 `.env`（已 gitignore）：`X_BEARER_TOKEN` 等
- TTS：按 AGENTS.md「TTS config」约定使用既有配置（默认 Edge 免费 TTS），管线代码只调用、不改动 TTS 模块
- 文档与界面文案中不出现具体 AI 厂商/模型名，用中性表述
