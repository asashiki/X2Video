# 卡片用无头浏览器出图，成片用 FFmpeg 合成

Issue #8 要在「确定性 HTML 时间线」和「纯 FFmpeg 滤镜链」之间做 spike。结论：**两者拆开各用所长**，不引入 Node 时间线框架。

## Decision

1. **Tweet Card** 用 HTML/CSS 模板 + Playwright Chromium 截成 1080×1920 PNG（落实 ADR-0002：仿卡片而非真截图，翻译区写在模板里）。
2. **成片** 用本机 FFmpeg：卡片 PNG + Edge/兼容 TTS 音频 + ASS 字幕 → 竖屏 MP4，再拼成 Digest（ADR-0003 / ADR-0005）。
3. 不引入 Remotion / HyperFrames：Python CLI 保持单一运行时，定时任务不依赖 Node 子进程。

## Consequences

- 依赖增加 Playwright Chromium 与系统 FFmpeg；`x2video doctor` 负责体检。
- 动效以淡入淡出为主，不做复杂网页时间线。若日后确需更强动效，再开旁路，不推翻本决策。
- Issue #8 原文写「结论写成 ADR-0007」——ADR-0007 已被 TTS 占用，故本条为 ADR-0009。
