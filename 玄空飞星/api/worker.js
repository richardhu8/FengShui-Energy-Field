/**
 * 玄空飞星 AI 堪舆师 —— Cloudflare Worker 代理
 *
 * 职责：把浏览器端算好的**已验证盘面数据**连同用户问题转给 Claude，
 * 由模型只做解读、不重算命理数字。API Key 只存在于 Worker 环境变量中，
 * 永不下发到前端。
 */
import Anthropic from "@anthropic-ai/sdk";

const MODEL = "claude-opus-5";
const DAILY_LIMIT = 3;           // 每 IP 每日免费提问次数
const MAX_MSGS = 8;              // 只带最近 8 条对话

const SYSTEM = `你是一位严谨的玄空飞星与八宅堪舆顾问。

【最重要的规则】
用户消息中会附带一段【盘面数据】，那是由经过校验的排盘引擎算出的结果。
- 所有山星、向星、运盘、流年、八宅游年、格局、缺角、炁流强度，**一律以盘面数据为准**。
- 你**不得自己重算或猜测**这些数字。若数据中没有某项，就说没有，不要编。
- 你的工作是**解读**：把这些数字翻译成人能理解的居住建议。

【回答方式】
- 用中文，300 字以内，直接说结论，不要铺垫。
- 先说最要紧的一两点，再给可操作的建议（家具朝向、开窗、动静区安排等）。
- 化解手段以「移形易位」优先（改布局、调动线），摆件次之。不要推销法器。

【边界】
- 流派有分歧处（下卦替卦分界、井字法与放射法、五入中阴阳），如实说明两派差异，不要装作只有一个答案。
- 不做医疗、投资、法律断言。不预测具体祸福、寿数、生死。
- 若用户问的是情绪困扰或人生重大决定，提醒风水为辅、人为为主。
- 结尾不必每次都加免责声明，页面已有。`;

function cors(origin) {
  return {
    "Access-Control-Allow-Origin": origin || "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}
const json = (obj, status, origin) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...cors(origin) },
  });

async function rateLimit(env, ip) {
  if (!env.RATE_KV) return { ok: true, left: DAILY_LIMIT };   // 未绑定 KV 则不限流
  const day = new Date().toISOString().slice(0, 10);
  const key = `q:${day}:${ip}`;
  const used = parseInt((await env.RATE_KV.get(key)) || "0", 10);
  if (used >= DAILY_LIMIT) return { ok: false, left: 0 };
  await env.RATE_KV.put(key, String(used + 1), { expirationTtl: 60 * 60 * 26 });
  return { ok: true, left: DAILY_LIMIT - used - 1 };
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allow = (env.ALLOW_ORIGIN || "*").split(",").map((s) => s.trim());
    const okOrigin = allow.includes("*") || allow.includes(origin) ? origin || "*" : allow[0];

    if (request.method === "OPTIONS")
      return new Response(null, { status: 204, headers: cors(okOrigin) });
    if (request.method !== "POST")
      return json({ error: "method_not_allowed" }, 405, okOrigin);
    if (!env.ANTHROPIC_API_KEY)
      return json({ error: "server_misconfigured", message: "未配置 ANTHROPIC_API_KEY" }, 500, okOrigin);

    let body;
    try { body = await request.json(); }
    catch { return json({ error: "bad_json" }, 400, okOrigin); }

    const msgs = Array.isArray(body.messages) ? body.messages.slice(-MAX_MSGS) : [];
    const ctx = typeof body.context === "string" ? body.context.slice(0, 4000) : "";
    if (!msgs.length) return json({ error: "empty_messages" }, 400, okOrigin);
    for (const m of msgs) {
      if (!m || (m.role !== "user" && m.role !== "assistant") || typeof m.content !== "string")
        return json({ error: "bad_message_shape" }, 400, okOrigin);
      if (m.content.length > 2000) m.content = m.content.slice(0, 2000);
    }

    const ip = request.headers.get("CF-Connecting-IP") || "anon";
    const rl = await rateLimit(env, ip);
    if (!rl.ok)
      return json({ error: "rate_limited", message: `每日免费提问 ${DAILY_LIMIT} 次已用完，明天再来` }, 429, okOrigin);

    // 盘面数据以 user 消息前缀注入，模型据此解读
    const last = msgs[msgs.length - 1];
    if (ctx && last.role === "user")
      last.content = `【盘面数据】\n${ctx}\n\n【我的问题】\n${last.content}`;

    const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
    try {
      const resp = await client.beta.messages.create({
        model: MODEL,
        max_tokens: 8000,
        system: [{ type: "text", text: SYSTEM, cache_control: { type: "ephemeral" } }],
        messages: msgs,
        thinking: { type: "adaptive" },
        output_config: { effort: "medium" },   // 公开免费工具的成本取舍，可上调
        betas: ["server-side-fallback-2026-07-01"],
        fallbacks: "default",
      });

      if (resp.stop_reason === "refusal")
        return json({ error: "refused", message: "这个问题我不便回答，换个问法试试" }, 200, okOrigin);

      const text = resp.content.filter((b) => b.type === "text").map((b) => b.text).join("\n").trim();
      return json({ reply: text || "（无内容）", left: rl.left, model: resp.model }, 200, okOrigin);
    } catch (e) {
      if (e instanceof Anthropic.RateLimitError)
        return json({ error: "upstream_rate_limited", message: "服务繁忙，稍后再试" }, 429, okOrigin);
      if (e instanceof Anthropic.AuthenticationError)
        return json({ error: "auth", message: "服务端密钥无效" }, 500, okOrigin);
      if (e instanceof Anthropic.APIError)
        return json({ error: "upstream", message: `上游错误 ${e.status}` }, 502, okOrigin);
      return json({ error: "unknown", message: "请求失败" }, 500, okOrigin);
    }
  },
};
