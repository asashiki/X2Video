# TTS 配置

TTS 默认使用 Edge 免费 TTS，供本地开发、端到端测试和低成本验证使用。项目里的外显文案只说"配置 API"或"兼容 API"，避免展示具体厂商或模型名称。

## 默认行为

- `TTS_PROVIDER=edge`
- `TTS_VOICE=zh-CN-XiaoxiaoNeural`
- `TTS_RATE=+0%`
- `TTS_VOLUME=+0%`
- `TTS_PITCH=+0Hz`
- 输出格式默认交给实现层选择，优先生成 FFmpeg 可直接读取的音频文件。

## API 兼容配置

当需要切换到外部语音合成服务时，使用通用字段表达能力，不把厂商名写进配置键、命令行参数或用户界面：

- `TTS_PROVIDER=api`
- `TTS_API_BASE_URL=<endpoint>`
- `TTS_API_KEY=<secret>`
- `TTS_API_MODEL=<model-or-voice-id>`
- `TTS_API_VOICE=<voice-id>`
- `TTS_API_FORMAT=mp3`
- `TTS_API_TIMEOUT_SECONDS=60`

实现层应把 `TTS_PROVIDER=edge` 作为无密钥默认路径；只有 `TTS_PROVIDER=api` 时才读取 API 相关字段。日志、错误信息和帮助文本应使用"语音合成 API"、"TTS API"、"兼容 API"这类中性说法。

## 禁止外显内容

- 不在 README、CLI help、配置示例、日志和错误信息里写具体厂商名或模型名。
- 不把特定厂商名做成 provider 枚举值。
- 不把特定厂商名写入文件名、目录名或环境变量名。
