# DSH-LOCAL-MODEL-RECON — 把本地 14B 以 OpenAI 兼容 provider 接进 DSH（只读侦察 + mock 验证）

**任务**：只读侦察 + mock 验证；**未修改** `cordis.patch.yml`、未装插件、零 GPU/模型/联网（仅本机 127.0.0.1 mock）。
**结论**：**可行，且不需要面板插件**——DSH 的 `llm-pi-ai` 路由就是配置驱动的 OpenAI 兼容适配器，在现有 profile patch 的
`llm-pi-ai.providers` 里**加一个 `local14b` 兄弟条目**即可；改 patch 后由宿主 HMR 自动生效（无需重启）。

---

## 1 DSH 的重载机制：改 `cordis.patch.yml` 是**自动热重载**（不是重启）

- 该 profile 的补丁层 = `C:\Users\lezige\.dsh\profiles\desktop\cordis.patch.yml`（447 行；`llm-pi-ai` 在第 5 行，`agent-default-model` 在 377 行，`ui-chat` 在 422 行）。
- **宿主 HMR 确实在跑**（证据 = 运行日志）：
  `~/.dsh/logs/desktop-next-2026-10-26.0.jsonl` 有
  `"source":"host.kernel.hmr","event":"log","pluginId":"include:hmr","message":"watching []"`（2026-10-26T15:04:51.636Z）。
  即桌面端在 profile 启动时挂载了 `dsh-hmr`（include 层），而不是只有浏览器侧 `client-hmr`。
- `@deepseek-ai/dsh-hmr/README.zh.md:61`：HMR 在初始化时注册 **profile manifest 和两份用户 patch** 的监听，
  "profile 与 home patch 变化也会触发重新组合"；`runExclusive()` 把配置变更串行化。
- 因此：**只改 `cordis.patch.yml` 里 `providers` 的配置** → 文件事件 → 重新组合 → `llm-pi-ai` 原子更新路由注册
  （该包 README"运行时更改配置"：路由集合变化时原子更新注册）。**无需重启 DSH**。
- 仍可能需要重启的情形：`dsh.profile.bundles`/package.json 依赖变化（安装新包）、或 HMR 报告 `restart-required`。
  兜底一律是：关掉 DSH 再启动。
- 观察入口：DSH 日志（`~/.dsh/logs/desktop-next.log`）出现 reload/plugin 相关行；模型选择器里出现新 provider。

## 2 Provider 条目必填字段（schema 取自解包的 `@deepseek-ai/dsh-llm-pi-ai`，非猜测）

Schema：`kvmem/dsh-recon/asar-selected/node_modules/@deepseek-ai/dsh-llm-pi-ai/lib/index.js:1044-1080`（schemastery `profile` / `Config`）。

| 字段 | 必填 | 说明 / 证据 |
|---|---|---|
| `providers.<name>` | — | dict，键是路由名（任意大小写/连字符；要登录存凭据的才限小写连字符）。本机用 `local14b` |
| `api` | **非目录路由必填** | 取值来自 `PROTOCOLS`，含 `openai-completions`（本地 Chat Completions 用这个）、`openai-responses`、`anthropic-messages`（`lib/index.js:847-850`, `:2241`） |
| `baseURL` | **必填**（非目录路由） | 指向 `http://127.0.0.1:8765/v1`；`resolveProfiles` 拒绝空串（`:1124`） |
| `models` | **必填且非空**（非目录路由） | `[{id, name?, contextWindow?, maxTokens?, input?, reasoningEfforts?}]`；模型无描述时回退 `defaultContextWindow=262144` / `defaultMaxTokens=32768`（`:959-961`, `:693-695`） |
| `apiKeyEnv` | **可省** | 省略 = 故意无鉴权（`lib/index.js:854-870` 注释：keyless route 交给协议层）。但 pi-ai 的 OpenAI 兼容实现**仍要求 key 或 `Authorization` 头**（`pi-ai/dist/api/openai-completions.js:31-37`）⇒ 本地路由要么给 `headers.authorization`（下面补丁就这么做），要么给 `apiKeyEnv` 指向一个值为 dummy 的环境变量 |
| `headers` | 可选 | dict<string,string>；会进入请求头（`lib/index.js:1060`, `:1989` `requestHeaders(profile.headers)`）→ 用它带 `authorization: Bearer local` 最省事 |
| `displayName` | 可选 | 模型选择器显示名（默认= provider 键） |
| `compat` | 可选 | 逐路由/逐模型协议兼容开关，见下 |
| `retryPolicy` / `timeoutMs` / `streamIdleTimeoutMs` | 可选 | 默认重试 5 次；流空闲超时默认 **300000 ms**（`:943`） |

`compat` 常用开关（`lib/index.js:1017-1040`）：`maxTokensField: "max_tokens" | "max_completion_tokens"`（本地 llama.cpp/vLLM 只认 `max_tokens` 时用它）、
`supportsUsageInStreaming`、`supportsTemperature`、`supportsStore`、`supportsDeveloperRole`、`thinkingFormat`、`chatTemplateKwargs/Args`。
**白名单/校验**：provider 列表**没有内置白名单**——`providers` 是任意 dict（`Config = z.object({providers: z.dict(profile)})`）。
现成证据：`bailian` 就是手工声明的非目录路由（`api: openai-completions` + 自建 baseURL），且 `agent-default-model` 已把默认模型设成它家的
`deepseek-v4.1-flash-1017` ⇒ 手声明的 provider 能被模型选择器列出并被 agent 选用。校验只要求「`api` + `baseURL` + 非空 `models`」可服务
（`lib/index.js:690-696`, README"失败与恢复"）。

`agent-default-model` 配置 = `{provider, model}`（`cordis.patch.yml:377-381`），可整体切到 `local14b/local14b`；也可只在选择器里临时切。

## 3 DSH 对 OpenAI 兼容端点的最低要求（pi-ai 实际发什么）

实现：`@earendil-works/pi-ai/dist/api/openai-completions.js`（官方 `openai` npm SDK，`createClient` → `new OpenAI({baseURL, apiKey, defaultHeaders})`）。

| 项 | 要求 | 证据 |
|---|---|---|
| `POST /v1/chat/completions` | **始终 `stream: true`** | `openai-completions.js:575` |
| SSE 格式 | 官方 SDK 解析：每帧 `data: {json}\n\n`，以 `data: [DONE]\n\n` 结束 | openai SDK 标准；mock 实测（§5） |
| `stream_options` | 默认发 `{include_usage:true}`（`compat.supportsUsageInStreaming:false` 可关） | `:581-583` |
| 输出上限字段 | 默认 `max_completion_tokens`；`compat.maxTokensField:"max_tokens"` 时改发 `max_tokens` | `:589-595` |
| `temperature` | 有则透传 | `:597-599` |
| `tools` / `tool_choice` | agent 有工具时**会带 `tools`**（函数 JSON Schema）；`tool_choice` 仅显式设置时带 | `:601-615` |
| 工具历史 | 若历史里有 tool_calls/tool_result，即使无新工具也会带 `tools: []` | `:612-615` |
| 鉴权 | `Authorization: Bearer …`（SDK 发 key，或我们配置的 `headers.authorization`） | `createClient`（`:532-565`） |
| 模型发现 | 可选：`GET {baseURL}/models`（bearer）；**只要 `models` 列表显式给出，就不需要它** | dsh-llm-pi-ai README"从端点发现模型" |

**14B 侧影响**：会收到 `tools` 字段。若本地服务不支持 function calling，最省事是让服务忽略 `tools`、只回文本；
agent 的纯对话轮仍可用，但"让模型改文件/调工具"的任务会退化（DSH 可能报无工具调用或重试）。不需要实现 `/v1/models`，但实现了更好（配置界面可"发现模型"）。

## 4 最小补丁片段（只加 provider，不动 bailian）

> **关键语义**：patch 层里**同 id 条目替换整段 config**（`dsh-app-boot/README.zh.md:61`），所以**不能新增第二个 `- id: llm-pi-ai`**，
> 必须把 `local14b:` 作为 `bailian:` 的兄弟插进**现有 `providers:` 映射**。只做这一处插入，其他行一律不动。

插入到 `cordis.patch.yml` 第 5 行 `- id: llm-pi-ai` 的 `config.providers` 下（`bailian:` 块结束、`compat:` 之前/之后同缩进，YAML 映射顺序无关）：

```yaml
      local14b:
        displayName: 本地 14B（OpenAI 兼容）
        api: openai-completions
        baseURL: http://127.0.0.1:8765/v1
        # 本地服务无鉴权：pi-ai 仍要 Authorization 头，用 headers 喂一个占位值
        headers:
          authorization: Bearer local
        models:
          - id: local14b
            name: 本地 14B
            contextWindow: 32768
            maxTokens: 4096
        compat:
          maxTokensField: max_tokens
          supportsUsageInStreaming: true
          supportsStore: false
          supportsDeveloperRole: false
```

（缩进 = 6 空格，与 `bailian:` 同级；放在 `providers:` 下任意位置。若本地服务不支持 `max_tokens` 而只认 `max_completion_tokens`，删掉该行即可。）

**可选**：把默认模型切到本地（想全局默认时；不切则只在选择器里选）——
`agent-default-model`（第 377 行）的 `config.provider: bailian` → `local14b`、`model: deepseek-v4.1-flash-1017` → `local14b`。
不建议一开始就改默认：先验证本地路由可用，再决定是否当默认。

## 5 备份 / 回滚 / 验证（含已跑的 mock 实测）

### 5.1 备份（改前一条命令）

```bash
cp ~/.dsh/profiles/desktop/cordis.patch.yml ~/.dsh/profiles/desktop/cordis.patch.yml.bak-20261027-local14b
sha256sum ~/.dsh/profiles/desktop/cordis.patch.yml*   # 记下两值
```

### 5.2 回滚

```bash
cp ~/.dsh/profiles/desktop/cordis.patch.yml.bak-20261027-local14b ~/.dsh/profiles/desktop/cordis.patch.yml
# HMR 会自动重载回原状；没生效就重启 DSH
```
回滚后模型选择器里 `local14b` 消失即成功。若 DSH 起不来（YAML 解析失败）：恢复备份再启动。

### 5.3 验证步骤（用 mock，不需要真模型）

1) 起 mock（已在 `kvmem/dsh-recon/mock/openai_mock.py`，仅本机 stdlib，无网络）：
   `python -X utf8 kvmem/dsh-recon/mock/openai_mock.py 8765`
2) 确认 mock：`GET http://127.0.0.1:8765/v1/models` → `{"object":"list","data":[{"id":"local14b",...}]}`（**本文件 §5.4 已实测**）。
3) 加 §4 的 `local14b` 块 → 保存 → 等 1–2 s（HMR 自动重载）→ DSH 模型选择器应出现「本地 14B（OpenAI 兼容） → 本地 14B」。
   - 若未出现：看 `~/.dsh/logs/desktop-next.log` 是否有配置错误（YAML/校验失败会点名 provider 与字段）；必要时重启 DSH。
4) 选该模型发一句话 → mock 会回 `[mock local14b] 收到 N 条消息，tools=1；…`，界面显示回答与延迟。
   mock 日志/响应证明 DSH 的请求形状（stream、tools、stream_options）到达。
5) 收尾：`kill` mock；决定是否保留 provider 配置。

### 5.4 已跑的实测（本轮，mock 在 8765，验证后已 kill）

- mock 脚本：`kvmem/dsh-recon/mock/openai_mock.py`；模拟 pi-ai 请求（`stream:true`、`stream_options.include_usage`、`max_completion_tokens`、`temperature`、`tools` 各一）。
- 结果：
  - `GET /v1/models` → `{"object":"list","data":[{"id":"local14b","object":"model","owned_by":"local"}]}`
  - `POST /v1/chat/completions` → `200`，`content-type: text/event-stream`
  - 读到 **8 个 SSE data 帧 + `[DONE]`**；`usage={"prompt_tokens":12,"completion_tokens":49,"total_tokens":61}`；端到端 **116 ms**
  - 文本 = `[mock local14b] 收到 2 条消息，tools=1；最后一条用户消息：你好，本地模型`（证明 `tools`/`stream_options` 字段被正确接收）
- 未做（需用户在场）：真正改 `cordis.patch.yml` 并观察 DSH 重载——按 §4/§5.3 执行即可。

## 6 风险与边界

- **不是**官方内置 provider，但 §2 证据表明 UI/agent 都按配置列 provider（bailian 先例），无需白名单。
- 改 patch 属**用户配置写入**：必须先备份；YAML 写错会导致启动失败（HMR 会拒绝格式错误 patch 并保留运行中配置，但重启时会失败）。
- 本地 14B 对 `tools` 的支持未知：先验证纯对话；工具型任务需服务端支持 function calling，或后续加一层"忽略 tools"的适配。
- 本侦察**未**使用 GPU/真模型；mock 只证明 wire 形状，不证明 14B 推理质量。
- 原「面板插件」方向暂停：`kvmem/dsh-plugin/dsh-local-memory/` 保留为未安装实验件（未复制到 `~/.dsh`、未改 profile）；
  若后续只差 `/remember` 入口，优先考虑在 provider 可用后用一个极小命令入口，而不是重造面板。