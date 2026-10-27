// dsh-local-memory — browser half.
//
// DSH 客户端插件的 bundle 约定：脚本只注册 factory，模块体在首次物化时运行
// （`window.__ModuleLoader__.load({ id, factory })`）。平台 seed 表里有
// react / react/jsx-runtime，其余一律不可 require。本文件因此只用
// `require("react")` + `React.createElement`，不引入任何外部依赖。
//
// 面板注册进设置页的 `settings.section`（与 dsh-context-length 同一扩展点），
// 所有请求都走同源 `/local-memory/*`，由宿主半侧代理到 http://127.0.0.1:8765，
// 因此页面侧没有跨源/CORS 依赖。
window.__ModuleLoader__.load({
	id: "dsh-local-memory",
	factory: (require) => {
		var module = { exports: {} };
		var exports = module.exports;
		Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });

		const React = require("react");
		const e = React.createElement;

		const API = "/local-memory";
		const CSS_ID = "dsh-local-memory/panel.css";
		if (typeof document !== "undefined" && document.querySelector('style[data-plugin-css="' + CSS_ID + '"]') === null) {
			const tag = document.createElement("style");
			tag.dataset.plugin = "dsh-local-memory";
			tag.dataset.pluginCss = CSS_ID;
			tag.textContent = [
				".dlm-wrap{box-sizing:border-box;width:100%;max-width:860px;display:flex;flex-direction:column;gap:14px;color:var(--dsw-alias-label-primary,#e6e6e6)}",
				".dlm-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}",
				".dlm-title{margin:0;font-size:18px;font-weight:600;line-height:26px}",
				".dlm-sub{margin:0;font-size:12px;color:var(--dsw-alias-label-tertiary,#9aa0a6)}",
				".dlm-pill{font-size:12px;padding:3px 10px;border-radius:999px;border:1px solid var(--dsw-alias-border-l2,#3a3a3a);white-space:nowrap}",
				".dlm-pill.is-ok{border-color:#2f7d4f;color:#7fd6a4}",
				".dlm-pill.is-down{border-color:#8a3b3b;color:#ff9b9b}",
				".dlm-pill.is-busy{border-color:#5b5b8a;color:#b9b9ff}",
				".dlm-list{box-sizing:border-box;min-height:220px;max-height:46vh;overflow-y:auto;display:flex;flex-direction:column;gap:8px;padding:10px;border:1px solid var(--dsw-alias-border-l1,#333);border-radius:12px;background:var(--dsw-alias-bg-layer-1,rgba(255,255,255,.03))}",
				".dlm-empty{margin:auto;font-size:13px;color:var(--dsw-alias-label-tertiary,#9aa0a6);text-align:center;line-height:1.7}",
				".dlm-msg{box-sizing:border-box;max-width:92%;padding:8px 11px;border-radius:10px;font-size:13px;line-height:20px;white-space:pre-wrap;word-break:break-word}",
				".dlm-msg.user{align-self:flex-end;background:rgba(59,130,246,.22);border:1px solid rgba(59,130,246,.4)}",
				".dlm-msg.bot{align-self:flex-start;background:rgba(255,255,255,.05);border:1px solid var(--dsw-alias-border-l1,#333)}",
				".dlm-msg.sys{align-self:flex-start;background:transparent;border:1px dashed var(--dsw-alias-border-l2,#3a3a3a);font-size:12px;color:var(--dsw-alias-label-tertiary,#9aa0a6)}",
				".dlm-meta{margin-top:4px;font-size:11px;color:var(--dsw-alias-label-tertiary,#9aa0a6)}",
				".dlm-row{display:flex;gap:8px;align-items:flex-end}",
				".dlm-input{box-sizing:border-box;flex:1;min-height:64px;max-height:160px;resize:vertical;font:inherit;font-size:13px;line-height:20px;color:var(--dsw-alias-label-primary,#e6e6e6);background:var(--dsw-alias-bg-layer-1,rgba(255,255,255,.03));border:1px solid var(--dsw-alias-border-l2,#3a3a3a);border-radius:10px;padding:9px 11px;outline:none}",
				".dlm-input:focus{border-color:var(--dsw-alias-brand-primary,#3b82f6)}",
				".dlm-btn{box-sizing:border-box;height:36px;padding:0 14px;font:inherit;font-size:13px;border-radius:9px;border:1px solid var(--dsw-alias-border-l2,#3a3a3a);background:var(--dsw-alias-bg-layer-1,rgba(255,255,255,.04));color:inherit;cursor:pointer}",
				".dlm-btn:hover:not(:disabled){border-color:var(--dsw-alias-brand-primary,#3b82f6)}",
				".dlm-btn:disabled{opacity:.45;cursor:not-allowed}",
				".dlm-btn.primary{background:rgba(59,130,246,.24);border-color:rgba(59,130,246,.55)}",
				".dlm-actions{display:flex;gap:8px;flex-wrap:wrap}",
				".dlm-err{font-size:12px;line-height:18px;color:#ff9b9b;border:1px solid #8a3b3b;border-radius:9px;padding:7px 10px;background:rgba(138,59,59,.12)}",
				".dlm-ok{font-size:12px;color:#7fd6a4}",
			].join("\n");
			document.head.appendChild(tag);
		}

		/**
		 * 读 JSON 响应；失败时抛出带有服务端 error/hint 的可读错误。
		 * @param {Response} response
		 * @returns {Promise<any>}
		 */
		async function readJson(response) {
			const text = await response.text();
			let payload;
			try {
				payload = text ? JSON.parse(text) : {};
			} catch {
				payload = { raw: text };
			}
			if (!response.ok) {
				const detail = payload && (payload.error || payload.detail || payload.raw);
				throw new Error(
					`HTTP ${response.status}${detail ? " — " + String(detail).slice(0, 300) : ""}` +
						(payload && payload.hint ? "\n提示：" + payload.hint : "")
				);
			}
			return payload;
		}

		/**
		 * 一次同源 API 调用，计时并返回 { data, latencyMs }。
		 * @param {string} path
		 * @param {{ method?: string, body?: unknown, timeoutMs?: number }} [options]
		 */
		async function call(path, options) {
			const opts = options || {};
			const startedAt = performance.now();
			let response;
			try {
				response = await fetch(API + path, {
					method: opts.method || "GET",
					headers: opts.body !== undefined ? { "content-type": "application/json" } : undefined,
					body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
					signal: AbortSignal.timeout(opts.timeoutMs || 120000),
				});
			} catch (error) {
				const latencyMs = Math.round(performance.now() - startedAt);
				if (error && (error.name === "TimeoutError" || error.name === "AbortError")) {
					throw Object.assign(new Error(`请求超时（${latencyMs} ms）：${path}`), { latencyMs });
				}
				throw Object.assign(
					new Error(
						`连不上本地记忆代理（${path}）。\n` +
							"若页面刚启动或 DSH 未重载插件，请刷新后重试；仍失败则确认 DSH 宿主已加载 dsh-local-memory。"
					),
					{ latencyMs }
				);
			}
			const data = await readJson(response);
			return { data, latencyMs: Math.round(performance.now() - startedAt) };
		}

		/** 从多种可能字段名里取出回答文本（本地服务字段命名未强约束）。 */
		function answerText(payload) {
			if (payload === null || payload === undefined) return "";
			if (typeof payload === "string") return payload;
			for (const key of ["answer", "reply", "text", "response", "content", "message"]) {
				if (typeof payload[key] === "string" && payload[key].length > 0) return payload[key];
			}
			return "（返回里没有 answer/reply/text 字段）\n" + JSON.stringify(payload, null, 2).slice(0, 2000);
		}

		/** 把 /memories 的常见形状摊平为字符串列表。 */
		function memoryLines(payload) {
			const list = Array.isArray(payload) ? payload : payload && (payload.memories || payload.items || payload.results);
			if (!Array.isArray(list)) return ["（未识别的 /memories 返回）", JSON.stringify(payload, null, 2).slice(0, 2000)].join("\n");
			if (list.length === 0) return "（记忆库为空）";
			return list
				.map((item, index) => {
					if (typeof item === "string") return `${index + 1}. ${item}`;
					const text = item && (item.text || item.content || item.memory || item.value);
					const createdAt = item && (item.created_at || item.createdAt || item.ts || item.time);
					return `${index + 1}. ${text !== undefined ? String(text) : JSON.stringify(item).slice(0, 300)}${createdAt ? "  ·" + String(createdAt) : ""}`;
				})
				.join("\n");
		}

		let seq = 0;

		/** 面板主组件（注册进 settings.section）。 */
		function LocalMemoryPanel() {
			const [messages, setMessages] = React.useState([]);
			const [draft, setDraft] = React.useState("");
			const [busy, setBusy] = React.useState("");
			const [error, setError] = React.useState("");
			const listRef = React.useRef(null);

			const push = React.useCallback((role, text, meta) => {
				seq += 1;
				setMessages((prev) => prev.concat([{ id: seq, role, text, meta: meta || "" }]));
			}, []);

			React.useEffect(() => {
				const node = listRef.current;
				if (node) node.scrollTop = node.scrollHeight;
			}, [messages]);

			const run = React.useCallback(
				async (label, fn) => {
					setBusy(label);
					setError("");
					try {
						await fn();
					} catch (err) {
						const message = String((err && err.message) || err);
						setError(message);
						push("sys", message, err && err.latencyMs !== undefined ? `耗时 ${err.latencyMs} ms` : "");
					} finally {
						setBusy("");
					}
				},
				[push]
			);

			const ask = React.useCallback(() => {
				const question = draft.trim();
				if (question.length === 0 || busy) return;
				setDraft("");
				push("user", question, "");
				run("ask", async () => {
					const { data, latencyMs } = await call("/ask", { method: "POST", body: { text: question, question, prompt: question } });
					push("bot", answerText(data), `延迟 ${latencyMs} ms`);
				});
			}, [draft, busy, push, run]);

			const remember = React.useCallback(() => {
				const text = draft.trim();
				if (text.length === 0 || busy) return;
				setDraft("");
				push("user", "请记住：" + text, "");
				run("remember", async () => {
					const { data, latencyMs } = await call("/remember", { method: "POST", body: { text, content: text, memory: text } });
					push("sys", "已提交写入请求：" + (data && (data.status || data.ok ? "ok" : JSON.stringify(data).slice(0, 400))), `延迟 ${latencyMs} ms`);
				});
			}, [draft, busy, push, run]);

			const loadMemories = React.useCallback(() => {
				run("memories", async () => {
					const { data, latencyMs } = await call("/memories", { timeoutMs: 15000 });
					push("bot", memoryLines(data), `延迟 ${latencyMs} ms`);
				});
			}, [push, run]);

			const checkStatus = React.useCallback(() => {
				run("status", async () => {
					const { data, latencyMs } = await call("/status", { timeoutMs: 8000 });
					push("sys", "服务在线：" + JSON.stringify(data).slice(0, 600), `延迟 ${latencyMs} ms`);
				});
			}, [push, run]);

			const onKeyDown = (event) => {
				if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
					event.preventDefault();
					ask();
				}
			};

			const pillClass = busy ? "dlm-pill is-busy" : error ? "dlm-pill is-down" : "dlm-pill";

			return e(
				"div",
				{ className: "dlm-wrap" },
				e(
					"div",
					{ className: "dlm-head" },
					e(
						"div",
						null,
						e("h2", { className: "dlm-title" }, "本地记忆助手"),
						e("p", { className: "dlm-sub" }, "14B 记忆服务 · http://127.0.0.1:8765（经 DSH 同源代理 /local-memory）")
					),
					e("span", { className: pillClass }, busy ? "运行中…" : error ? "出错" : "就绪")
				),
				error ? e("div", { className: "dlm-err" }, error) : null,
				e(
					"div",
					{ className: "dlm-list", ref: listRef },
					messages.length === 0
						? e(
								"div",
								{ className: "dlm-empty" },
								"向本地记忆提问，或把一段话写入记忆库。",
								e("br"),
								"服务未启动时这里会显示可读的错误与排查提示。"
							)
						: messages.map((msg) =>
								e(
									"div",
									{ key: msg.id, className: "dlm-msg " + msg.role },
									msg.text,
									msg.meta ? e("div", { className: "dlm-meta" }, msg.meta) : null
								)
							)
				),
				e("textarea", {
					className: "dlm-input",
					value: draft,
					placeholder: "问你的记忆…（Enter 发送，Shift+Enter 换行）",
					onChange: (event) => setDraft(event.target.value),
					onKeyDown,
					disabled: Boolean(busy),
				}),
				e(
					"div",
					{ className: "dlm-actions" },
					e("button", { className: "dlm-btn primary", onClick: ask, disabled: Boolean(busy) }, busy === "ask" ? "思考中…" : "发送"),
					e("button", { className: "dlm-btn", onClick: remember, disabled: Boolean(busy) }, "记住这段"),
					e("button", { className: "dlm-btn", onClick: loadMemories, disabled: Boolean(busy) }, "查看记忆"),
					e("button", { className: "dlm-btn", onClick: checkStatus, disabled: Boolean(busy) }, "检查服务")
				),
				e(
					"p",
					{ className: "dlm-sub" },
					"提示：模型推理期间延迟包含本地服务端排队；/ask 超时为 120 s，可在 dsh-local-memory/lib/client.js 调整。"
				)
			);
		}

		// ── cordis 客户端插件入口 ──
		const inject = ["slots"];

		/**
		 * 把面板注册进设置页 sections；slot 由 shell 的 settings 面板声明。
		 * @param {import("@deepseek-ai/cordis").Context} ctx 客户端根上下文
		 */
		function apply(ctx) {
			ctx.slots.inject("settings.section", () =>
				ctx.slots.register(
					{
						name: "settings.section",
						id: "local-memory",
						order: 90,
						label: () => "本地记忆",
						inject: () => ({}),
					},
					LocalMemoryPanel
				)
			);
		}

		exports.apply = apply;
		exports.inject = inject;
		exports.name = "dsh-local-memory";
		return module.exports;
	},
});