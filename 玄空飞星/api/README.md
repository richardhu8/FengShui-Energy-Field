# AI 堪舆师 · Serverless 后端

一个 Cloudflare Worker，把浏览器端**已算好的盘面数据**连同用户问题转给 Claude 解读。
API Key 只存在 Worker 环境变量里，永不下发前端。

## 为什么需要后端

前端页面不能直接调 Claude API —— 那样 API Key 会暴露在浏览器里，任何人都能拿去用。
所以必须有一层服务端代理。这是整个项目里**唯一**需要服务器的部分，其余全是纯静态。

## 设计要点：模型只解读，不重算

系统提示明确要求：山星、向星、八宅、缺角、炁流强度**一律以传入的盘面数据为准，不得自行推算**。

这是我们和同类产品的关键差别 —— 盘面数字来自经 1229 条测试校验的引擎，
模型的角色是把数字翻译成居住建议，而不是自己臆造命理结论。数字错不了，解读才有意义。

## 部署

```bash
cd api
npm install
npx wrangler login
```

**1. 设置 API Key**（存为加密 secret，不会出现在代码或日志里）

```bash
npx wrangler secret put ANTHROPIC_API_KEY
```

**2. 建限流用的 KV**（可选，不建则不限流）

```bash
npx wrangler kv namespace create RATE_KV
```

把返回的 id 填进 `wrangler.toml` 并取消那三行注释。

**3. 收紧允许来源**

编辑 `wrangler.toml` 的 `ALLOW_ORIGIN`，改成你的站点域名，别留 `*`：

```toml
[vars]
ALLOW_ORIGIN = "https://你的域名"
```

**4. 部署**

```bash
npx wrangler deploy
```

拿到形如 `https://fengshui-ai.<账号>.workers.dev` 的地址。

**5. 前端接上**

在 `玄空飞星排盘.html` 的 `<script>` 之前加一行：

```html
<script>window.FENGSHUI_AI_ENDPOINT="https://fengshui-ai.<账号>.workers.dev";</script>
```

不设这个变量，AI 面板会显示「未配置后端」并保持禁用 —— 其余功能不受影响。

## 接口

`POST /`

```jsonc
// 请求
{
  "messages": [{"role":"user","content":"主卧放哪间好？"}],  // 最近 8 条
  "context":  "坐向：丑山未向…"                              // 盘面数据，≤4000 字
}
// 成功
{"reply":"…", "left":2, "model":"claude-opus-5"}
// 失败
{"error":"rate_limited", "message":"每日免费提问 3 次已用完"}
```

## 参数与成本

| 项 | 取值 | 说明 |
|---|---|---|
| 模型 | `claude-opus-5` | $5 / $25 每百万 token |
| thinking | `adaptive` | 自适应思考 |
| effort | `medium` | **公开免费工具的成本取舍**，要更好的解读可调 `high` |
| max_tokens | 8000 | |
| fallbacks | `default` | 触发安全拒答时自动换模型续跑 |
| 限流 | 3 次 / IP / 天 | 改 `worker.js` 的 `DAILY_LIMIT` |

一次问答通常几千 token，成本约几分钱。上线前建议在 Cloudflare 控制台设用量告警。

## 换别的 Serverless

Worker 逻辑是标准 fetch handler，移植成本低：

- **Vercel Edge Functions** —— 改导出为 `export default async function handler(req)`；注意 Vercel 在中国大陆访问不稳
- **Deno Deploy** —— 几乎可直接跑，`env.X` 换成 `Deno.env.get("X")`
- **Netlify Functions** —— 换成 `export default async (req, ctx) => {}`

限流那段依赖 Cloudflare KV，换平台需换成对应的 KV / Redis。

## 安全

- API Key 只在 Worker 环境变量，前端拿不到
- 校验消息结构与长度上限，超长截断
- CORS 白名单（生产环境务必收紧）
- 按 IP 限流，KV 记录 26 小时过期
- 上游错误按类型分别处理，不把内部错误原文透给前端
