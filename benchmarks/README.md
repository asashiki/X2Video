# Benchmarks

Distillation 原料（issue #6）。每条对标视频一个 markdown 文件。

蒸馏流程尚未做成自动脚本：当前 `prompts/curation-prompt.md` 与 `prompts/script-prompt.md` 是手写初版，可在收集对标后回炉替换。

## 文件约定

`benchmarks/<slug>.md`：

```markdown
# 标题

- url: https://...
- platform: douyin | bilibili
- duration_s: 45
- stats: 播放/点赞（可选）

## 口播文案

...
```
