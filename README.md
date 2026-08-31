# X2Video Agent Studio

把一个自然语言内容目标变成可追溯、可审查、可修复的竖屏视频 Publish Kit。v0.2 在保留 v0.1 CLI 和确定性视频管线的基础上，加入有边界 Content Director、EvidencePack、编辑组合、脚本 Critic、成片 QC、局部修复和本地 Agent Studio。

**为什么做这个**：外网（尤其 X）上的优质热点内容与中文短视频平台之间存在信息差。这个项目把"发现热帖 → 翻译 → 解说 → 成片"的搬运链路自动化，人只保留两个把关点：选题和审片。

## 三分钟跑通离线 Demo

Demo Mode 使用仓库内冻结数据，不调用实时 X、LLM 或 TTS 网络；FFmpeg 仍会真实生成 MP4、封面和前后 QC 报告。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

x2video doctor
x2video agent run --goal "做一条 60 秒以内的今日 AI 新闻，避免重复，优先可信信息" --autonomy auto
x2video studio
# 打开终端打印的地址，默认 http://127.0.0.1:8765
# Windows 上 8765 可能被系统保留，命令会自动改用 8877 等可用端口
```

Studio 默认只监听 `127.0.0.1`。已登录 SuperGrok 时，网页「生成并运行」走原来的 `fetch → curate → card → script → render` 速览管线（真实 X 热帖 + 中文口播成片）。未登录时才使用仓库内冻结 Demo 数据。

常用控制面命令：

```bash
x2video replay RUN_ID
x2video feedback RUN_ID --comment "以后优先保留有公开评测集的消息"
x2video eval run --profile baseline
x2video eval run --profile v0.2
x2video eval compare BASELINE_ID NEW_ID
```

可复现证明位于：

- `artifacts/golden-publish-kit/`：真实 MP4、封面、Trace、脚本 Diff、修复前后 QC；
- `artifacts/demo-stability.json`：10 次连续离线 Demo 的逐次结果；
- `artifacts/ui-qa/2026-08-30/`：浅色/深色主题在 1440×1000 与 390×844 下的 32 张真实浏览器截图；
- `evals/reports/`：固定 30-case 的 JSON、Markdown、HTML 与基线对比。

更多说明见 [Agent 架构](./docs/architecture-agent-studio.md)、[三分钟演示](./docs/demo/three-minute-demo.md) 和 [验证报告](./docs/demo/verification-report.md)。

## 项目状态

两条路径并存：原 `fetch → curate → card → script → render` 管线继续产出 `final/`；新 Agent Kernel 通过版本化 Schema、SQLite、Trace 和 Tool Registry 驱动冻结 Demo 与 Studio。X 官方 MCP（issue #1）仍是占位，默认真实数据路径仍为 SuperGrok；这项非比赛 P0，不应被描述成已完成。Issue #6 的对标原料目录仍为空，因此本次只交付版本化 Eval/报告和可审批 Memory，不宣称已完成真实样本蒸馏。

MVP 范围：AI/科技圈领域、Digest（N=1 为单推文特例）、人工上传。后期方向：领域可配置、多内容源、英文版输出、剪映草稿导出等。

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

## 开发环境

```bash
# 1. 克隆仓库
git clone https://github.com/asashiki/X2Video.git
cd X2Video

# 2. 创建虚拟环境（Python >= 3.11）
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. 安装项目（可编辑模式）
pip install -e .
playwright install chromium

# 4. 验证
x2video doctor
x2video --help
```

系统还需本机 `ffmpeg` / `ffprobe`（合成竖屏 MP4）。

若 Chromium 安装在非 Playwright 默认位置，可设置：

```bash
export X2VIDEO_BROWSER_EXECUTABLE=/absolute/path/to/chromium
x2video doctor
```

## 配置

### 创建配置文件

```bash
cp x2video.example.toml x2video.toml
# 按需编辑：领域关键词、互动门槛、LLM 服务地址、TTS 方案等
# 本地 x2video.toml 已被 gitignore，不要提交密钥或个人偏好
```

### 配置文件查找顺序

1. `--config` / `-c` 命令行参数
2. `X2VIDEO_CONFIG` 环境变量
3. 当前目录下的 `x2video.toml`
4. `~/.config/x2video/config.toml`

### 数据源：X MCP 或 SuperGrok 订阅

管线的 fetch 阶段支持可替换的数据源（见 ADR-0001）：

| `source.provider` | 鉴权方式 | 计费 |
| --- | --- | --- |
| `x_mcp`（默认） | X Developer Portal Bearer token（`X_BEARER_TOKEN`） | X API 按量 |
| `grok` | 浏览器 OAuth 登录 SuperGrok / X Premium+ | 订阅 token 额度 |

**用 SuperGrok 订阅拉 X 热点（推荐本地先试）：**

```bash
# 1. 浏览器授权（与 Grok Build 同类的 loopback OAuth）
x2video auth login
# 终端会打开 accounts.x.ai 授权页；浏览器已登录 Grok 时点「允许」即可

# 2. 查看会话状态 / 退出
x2video auth status
x2video auth logout

# 3. 配置数据源
# 在 x2video.toml:
#   [source]
#   provider = "grok"

# 4. 拉取候选推文（消耗的是 SuperGrok 订阅 token，不是 X API）
x2video fetch -k AI -k LLM

# 5. 一键跑通（Gate 1 直通，取 top N）
x2video run --auto

# 或分步：
x2video curate --auto
x2video card
x2video script
x2video render
```

`x2video run` 会复用 `work/YYYY-MM-DD/` 里已有产物；`--force` 重跑，`--from-stage card` 从指定环节续跑。

### 定时任务（直通模式）

把 `[curation].blocking_mode` 设为 `false`，或始终加 `--auto`。Windows 计划任务示例（每天 8:00）：

```bat
schtasks /create /tn X2Video /sc daily /st 08:00 /tr "cmd /c cd /d C:\path\to\X2Video && .venv\Scripts\x2video.exe run --auto"
```

Linux/macOS 用 cron：`0 8 * * * cd /path/to/X2Video && .venv/bin/x2video run --auto`。

产出在 `final/`，上传仍是人工 Gate 2。

LLM 未配置 `X2VIDEO_LLM_API_KEY` 时，会复用 SuperGrok 登录会话。TTS 默认 Edge 免费语音。

OAuth 凭证落在 `~/.config/x2video/grok_auth.json`（本地权限 600），access token 会自动 refresh。

### 密钥与私密信息

API key 等私密信息不写入 TOML，通过 `.env` 或环境变量注入（`X2VIDEO_` 前缀）：

```bash
# .env 文件（仓库根目录）
X2VIDEO_LLM_API_KEY=sk-...
X2VIDEO_TTS_API_KEY=...

# 或者直接 export
export X2VIDEO_LLM_API_BASE_URL=https://api.example.com/v1
```

SuperGrok OAuth **不要**把 token 写进 `.env`；一律走 `x2video auth login`。

## 环境约定

- 最好用 Codex 或者 Claude Code 做开发，开发的时候注意不要出现国产模型的名字，不然Claude会被封号
- Python CLI 项目（`x2video` 命令），见 ADR-0004
- 凭据放仓库根目录 `.env`（已 gitignore）：`X_BEARER_TOKEN` 等
- TTS：按 AGENTS.md「TTS config」约定使用既有配置（默认 Edge 免费 TTS），管线代码只调用、不改动 TTS 模块
- 文档与界面文案中不出现具体 AI 厂商/模型名，用中性表述
- 比较推荐用'mattpocock/skills'的'/implement'来对应issues开发
- 合成层决策见 [ADR-0009](./docs/adr/0009-playwright-cards-ffmpeg-compose.md)：HTML 卡片 + FFmpeg 成片
