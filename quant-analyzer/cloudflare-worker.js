// Cloudflare Workers 反代脚本
// 将 HuggingFace Spaces 应用反代到国内可访问的域名
// 
// 部署步骤:
// 1. 登录 https://dash.cloudflare.com
// 2. 进入 Workers & Pages → 创建 Worker
// 3. 粘贴此代码 → 保存并部署
// 4. 绑定自定义域名（可选）

// ====== 配置区域 ======
// 将下面的 URL 替换为你的 HuggingFace Space 地址
const HF_SPACE_URL = "https://bondtwilight-quantbrain.hf.space";

// 允许的域名（防盗链，留空则允许所有）
const ALLOWED_ORIGINS = [];

// ====== 反代逻辑 ======
addEventListener("fetch", (event) => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const url = new URL(request.url);

  // 健康检查
  if (url.pathname === "/health") {
    return new Response(JSON.stringify({ status: "ok", proxy: "QuantBrain CF Worker" }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // 构建目标 URL
  const targetUrl = new URL(url.pathname + url.search, HF_SPACE_URL);

  // 复制请求头
  const headers = new Headers(request.headers);
  headers.set("Host", targetUrl.host);
  headers.set("X-Forwarded-Host", url.host);
  headers.set("X-Real-IP", request.headers.get("CF-Connecting-IP") || "");
  headers.delete("CF-Connecting-IP");
  headers.delete("CF-IPCountry");
  headers.delete("CF-RAY");
  headers.delete("CF-Visitor");

  // 处理 WebSocket 升级
  if (headers.get("Upgrade") === "websocket") {
    return fetch(targetUrl.toString(), {
      headers,
    });
  }

  // 创建新请求
  const newRequest = new Request(targetUrl.toString(), {
    method: request.method,
    headers,
    body: request.method !== "GET" && request.method !== "HEAD" ? request.body : undefined,
    redirect: "follow",
  });

  try {
    const response = await fetch(newRequest);

    // 复制响应
    const newResponse = new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });

    // 添加 CORS 头
    newResponse.headers.set("Access-Control-Allow-Origin", "*");
    newResponse.headers.set("X-Proxy-By", "Cloudflare-Workers");

    return newResponse;
  } catch (err) {
    return new Response(
      JSON.stringify({
        error: "Proxy Error",
        message: err.message,
        target: targetUrl.toString(),
      }),
      {
        status: 502,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}
