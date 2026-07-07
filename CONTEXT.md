# X2Video

抓取 X（Twitter）上某一领域的热点推文，筛选、翻译并制作成中文短视频（抖音/B站竖屏）的自动化管线。

## Language

### 选题侧

**Candidate（候选推文）**:
通过硬指标筛选、进入价值评估的推文。
_Avoid_: 热帖、爆款推文

**Hard Filter（硬指标筛选）**:
第一层筛选——按时间窗口与互动数门槛（赞/转发）在搜索阶段过滤推文，纯规则、无语义判断。
_Avoid_: 初筛、流量筛选

**Curation（价值筛选）**:
第二层筛选——由 LLM 按「适合做成中文短视频的价值」对 Candidate 打分排序，剔除梗图、缺上下文、重复选题。
_Avoid_: 智能筛选、AI 筛选

**Pick（选题）**:
被选中要制作成视频的推文——阻塞模式下由用户从 Candidate 中勾选，直通模式下由 Curation 排名自动决定。
_Avoid_: 已选推文、目标推文

**Ledger（处理台账）**:
已处理推文 ID 与已做选题的持久记录，供 Curation 去重。
_Avoid_: 历史记录、去重表

### 制作侧

**Tweet Card（推文卡片）**:
用推文数据渲染出的仿 X 样式卡片图——原版版式 + 中文翻译区的双语卡片，是视频的画面主体。
_Avoid_: 截图、仿截图、贴图

**Script（解说文案）**:
视频的中文口播文案，由 Script Prompt 生成，也是字幕的来源。
_Avoid_: 稿子、旁白、配音文本

**TTS（语音合成）**:
把 Script 转成中文口播音频的环节。默认使用 Edge 免费 TTS，主要用于本地开发与端到端测试；生产环境可通过通用 API 配置替换为兼容服务。
_Avoid_: 具体模型名、具体厂商名

**Benchmark（对标）**:
用户手工挑选的同领域爆款视频及其口播文案，作为 Distillation 的原料。
_Avoid_: 参考视频、样例

**Distillation（蒸馏）**:
分析 Benchmark 文案的共性，沉淀出 Curation Prompt 与 Script Prompt 的过程；可随 Benchmark 增补反复回炉。
_Avoid_: 训练、微调

**Curation Prompt / Script Prompt（筛选提示词／文案提示词）**:
Distillation 的两份活文档产物，分别驱动 Curation 与 Script 生成。
_Avoid_: 系统提示词、模板

### 编排侧

**Digest（合集）**:
一条视频串讲 N 条 Pick 的目标形态；单推文视频是 N=1 的特例，不是独立形态。
_Avoid_: 单条模式/合集模式（不是两种模式，是同一形态的 N 取值）

**Gate（人工卡点）**:
管线中阻塞等待用户确认的节点。卡点一：从 Candidate 勾选 Pick；卡点二：审片并上传。可配置为直通（跳过卡点一）。
_Avoid_: 审核步骤、人工介入

**Publish Kit（发布包）**:
一次产出的完整交付物：成品 MP4、建议标题、简介、标签、封面图。上传本身在项目范围外。
_Avoid_: 成品、输出文件
