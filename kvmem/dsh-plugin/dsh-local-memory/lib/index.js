// dsh-local-memory — host half.
//
// 职责只有一件事：在 DSH 的 Web 服务上注册同源反向代理 `/local-memory/*`，
// 把请求转发给本地记忆服务 http://127.0.0.1:8765（/ask、/remember、/memories、/status）。
//
// 为什么不让浏览器直接 fetch 127.0.0.1:8765：浏览器页面是 http://127.0.0.1:<dsh端口>，
// 跨源请求需要本地服务自己发 CORS 头；走宿主同源代理则完全不依赖对方 CORS，
// 也不把本地端口暴露给页面脚本。代理是普通 Node http，无第三方依赖。
//
// 浏览器半侧在 lib/client.js，由 client-modules 依据 package.json 的 `dsh.client`
// 声明自动加载（`/plugins/dsh-local-memory/client.js`），这里不注入任何 <script>。

/** 稳定 Cordis 插件名。 */
export const name = "dsh-local-memory";

/** 需要 Web 服务（桌面端 webserver 条目提供；缺它则本插件不激活）。 */
export const inject = ["webServer"];

/** 本地记忆服务基址；可用环境变量覆盖（进程启动前设置）。 */
const UPSTREAM = (process.env.DSH_LOCAL_MEMORY_URL || "http://127.0.0.1:8765").replace(/\/+$/, "");

/** 路由前缀（同源，页面里用相对地址调用）。 */
const PREFIX = "/local-memory";

/** 会等模型生成，给较宽的上限；其余接口短超时。 */
const TIMEOUT_MS = { "/ask": 120000, default: 15000 };

/**
 * 收集请求体。
 * @param {import("node:http").IncomingMessage} req
 * @returns {Promise<Buffer>}
 */
function readBody(req) {
	return new Promise((resolve, reject) => {
		const chunks = [];
		let size = 0;
		req.on("data", (chunk) => {
			size += chunk.length;
			if (size > 4 * 1024 * 1024) {
				reject(new Error("request body too large"));
				req.destroy();
				return;
			}
			chunks.push(chunk);
		});
		req.on("end", () => resolve(Buffer.concat(chunks)));
		req.on("error", reject);
	});
}

/**
 * 统一的 JSON 错误响应。
 * @param {import("node:http").ServerResponse} res
 * @param {number} status
 * @param {Record<string, unknown>} payload
 */
function sendJson(res, status, payload) {
	const body = Buffer.from(JSON.stringify(payload), "utf8");
	res.writeHead(status, {
		"content-type": "application/json; charset=utf-8",
		"content-length": String(body.length),
		"cache-control": "no-store",
	});
	res.end(body);
}

/**
 * 把一个 /local-memory/* 请求代理到本地服务。
 * 上游不可达时返回可读的 502，而不是把 ECONNREFUSED 直接抛给页面。
 * @param {import("node:http").IncomingMessage} req
 * @param {import("node:http").ServerResponse} res
 * @param {string} path 去掉前缀后的上游路径（含查询串）
 */
async function proxy(req, res, path) {
	const timeout = TIMEOUT_MS[path.split("?")[0]] ?? TIMEOUT_MS.default;
	let body;
	try {
		body = await readBody(req);
	} catch (error) {
		sendJson(res, 413, { error: "body_too_large", detail: String(error?.message || error) });
		return;
	}

	const headers = {};
	const contentType = req.headers["content-type"];
	if (contentType) headers["content-type"] = contentType;
	if (body.length > 0) headers["content-length"] = String(body.length);

	try {
		const upstream = await fetch(UPSTREAM + path, {
			method: req.method,
			headers,
			body: body.length > 0 ? body : undefined,
			signal: AbortSignal.timeout(timeout),
		});
		const payload = Buffer.from(await upstream.arrayBuffer());
		res.writeHead(upstream.status, {
			"content-type": upstream.headers.get("content-type") || "application/json; charset=utf-8",
			"content-length": String(payload.length),
			"cache-control": "no-store",
		});
		res.end(payload);
	} catch (error) {
		const code = error?.name === "TimeoutError" ? "upstream_timeout" : "upstream_unreachable";
		sendJson(res, 502, {
			error: code,
			detail: String(error?.cause?.code || error?.message || error),
			upstream: UPSTREAM,
			hint: `本地记忆服务未响应：请确认 ${UPSTREAM} 已启动（/status 可用），再重试。`,
		});
	}
}

/**
 * 挂载反向代理路由。
 * @param {import("cordis").Context} ctx
 */
export function apply(ctx) {
	ctx.effect(
		() =>
			ctx.webServer.register({
				kind: "prefix",
				path: PREFIX,
				handler: (req, res) => {
					const url = req.url || "/";
					// /local-memory/ask?x=1 → /ask?x=1；/local-memory → /
					const path = url.slice(PREFIX.length) || "/";
					if (!path.startsWith("/")) {
						sendJson(res, 404, { error: "bad_path", path: url });
						return;
					}
					void proxy(req, res, path);
				},
			}),
		"dsh-local-memory: /local-memory proxy route",
	);
}