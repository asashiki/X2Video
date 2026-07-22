# SuperGrok OAuth 作为可选 X 数据源

在 ADR-0001 选定 X 官方 MCP 作为 MVP 默认数据源之后，增加一条 **可替换** 实现：通过 Grok / xAI 的浏览器 OAuth（与 Grok Build 同类的 authorization code + PKCE loopback）登录 SuperGrok 或 X Premium+ 订阅，再调用官方 **X Search** 工具拉热点推文。计费走订阅 token 额度，不消耗 X Developer API 配额。

## Context

- X MCP 需要 Developer Portal 应用与按量 Bearer token，本地试跑门槛高。
- 许多开发者已有 SuperGrok / X Premium+ 订阅；Grok 官方 API 提供 server-side `x_search` 工具，可在 Responses API 中直接搜 X。
- 社区工具（Hermes、OpenCode 插件、LiteLLM 等）已验证公开 client_id `b1a00492-073a-47ea-816f-4c329264a828` 的 PKCE / device 流程可用。

## Decision

1. 新增 `x2video auth login|status|logout`：浏览器 loopback OAuth，凭证存 `~/.config/x2video/grok_auth.json`，自动 refresh。
2. 新增 `[source]` 配置：`provider = "x_mcp" | "grok"`，由 `x2video.source` 工厂分发。
3. `provider = "grok"` 时，`fetch` 使用 Responses API + `x_search`，结构化产出 Candidate 字段。
4. 默认仍为 `x_mcp`，不推翻 ADR-0001；OAuth 路径是可选替代。

## Consequences

- 本地可零 X API 账单试跑 fetch；质量依赖模型从 X Search 结果中抽取字段的准确性。
- 个别订阅档位可能对 OAuth API 返回 403（上游策略），此时仍可回退 `x_mcp` 或 API key 路径。
- 数据访问层抽象已落地，后续再加浏览器抓取 / 其他源只需新 `CandidateSource` 实现。
