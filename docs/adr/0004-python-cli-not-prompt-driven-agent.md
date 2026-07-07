# 项目形态为 Python CLI，而非 prompt 驱动的 agent 工作流

参考.md 展示的是"AGENTS.md + 提示词，每次靠人喂给通用 agent 现场发挥"的模式；本项目不走这条路，而是做成 Python CLI（`x2video run`）：确定性环节（拉数据、渲卡片、TTS、FFmpeg）是普通代码，智能环节（Curation、翻译、Script 生成）是程序内部的 LLM API 调用。

理由：① 全自动定时任务模式只有独立程序能兑现；② 开源协作者需要 `pip install` 能跑的项目，而非特定 agent 环境；③ 运行结果可复现、token 成本可控。开发期由 agent 陪跑，但每个环节从第一天起固化为可独立运行的脚本。

## Consequences

TTS 与 LLM 均为 provider 抽象配置层，不绑死任何厂商。TTS 默认使用 Edge 免费 TTS 作为本地开发与端到端测试方案；需要更换时只配置兼容 API，不在界面、文档或默认配置中展示具体厂商或模型名称。
