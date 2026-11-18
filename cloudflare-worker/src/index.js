/**
 * AgentTrust KYE — Cloudflare Global Edge Cache & Stateless MCP/x402 Gateway
 * 1. Serves `/.well-known/*`, `/llms.txt`, and `/v1/leaderboard` from 300+ global edge PoPs (<15ms, zero origin load).
 * 2. Preserves `X-Payment`, `X-Prepaid-Bearer`, `X-Idempotency-Key`, and `Mcp-Stateless-Mode` headers for paid calls.
 */

const EDGE_CACHEABLE_PATHS = new Set([
  "/",
  "/llms.txt",
  "/.well-known/mcp.json",
  "/.well-known/x402-manifest.json",
  "/v1/leaderboard",
]);

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const originUrl = new URL(url.pathname + url.search, env.ORIGIN_BASE_URL);

    // Handle CORS preflight instantly at edge
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, X-Payment, X-Prepaid-Bearer, X-Idempotency-Key, X-Admin-Token",
          "Access-Control-Max-Age": "86400",
        },
      });
    }

    // Edge-cache public discovery, dynamic badges & viral leaderboard routes
    if (request.method === "GET" && (EDGE_CACHEABLE_PATHS.has(url.pathname) || url.pathname.startsWith("/v1/badge/"))) {
      const cache = caches.default;
      let response = await cache.match(request);
      if (!response) {
        const originResp = await fetch(originUrl.toString(), {
          headers: { "User-Agent": "AgentTrust-Edge-Worker/1.0" },
        });
        response = new Response(originResp.body, originResp);
        response.headers.set("Cache-Control", "public, s-maxage=60, max-age=30");
        response.headers.set("X-Edge-Cache", "MISS");
        ctx.waitUntil(cache.put(request, response.clone()));
      } else {
        response = new Response(response.body, response);
        response.headers.set("X-Edge-Cache", "HIT");
      }
      return response;
    }

    // Forward stateful/paid x402 & stateless MCP calls directly to warm Fly.io origin
    const proxyReq = new Request(originUrl.toString(), {
      method: request.method,
      headers: request.headers,
      body: request.method !== "GET" && request.method !== "HEAD" ? request.body : undefined,
    });
    const originResponse = await fetch(proxyReq);
    const out = new Response(originResponse.body, originResponse);
    out.headers.set("Mcp-Stateless-Mode", "enabled");
    return out;
  },
};
