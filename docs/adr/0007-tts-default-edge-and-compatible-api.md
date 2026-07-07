# TTS 默认使用 Edge，外部服务走兼容 API

TTS 是把 Script 转成中文口播音频的确定性环节。MVP 默认使用 Edge 免费 TTS，理由是无需密钥、成本为零、适合本地开发与端到端测试。

## Consequences

- 默认配置为 `TTS_PROVIDER=edge`，不要求用户先准备语音合成 API。
- 外部服务统一走 `TTS_PROVIDER=api` 与 `TTS_API_*` 字段。
- README、配置示例、CLI help、日志和错误信息只使用"配置 API"、"兼容 API"、"语音合成 API"等中性说法。
- 不在 provider 枚举、环境变量名、文件名或文档中展示具体厂商或模型名称。
