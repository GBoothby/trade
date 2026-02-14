
export default {
    async fetch(request, env, ctx) {
        const url = new URL(request.url);

        // Handle CORS for browser access
        const corsHeaders = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        };

        if (request.method === "OPTIONS") {
            return new Response(null, { headers: corsHeaders });
        }

        // Extract path and forward to Finnhub
        // e.g. /quote?symbol=AAPL -> https://finnhub.io/api/v1/quote?symbol=AAPL&token=...
        const finnhubBase = "https://finnhub.io/api/v1";
        const path = url.pathname;  // e.g. "/quote" or "/stock/profile2"
        const query = url.search;   // e.g. "?symbol=AAPL"

        // Security check: only allow specific endpoints to prevent abuse
        const allowedPaths = ["/quote", "/stock/profile2"];
        if (!allowedPaths.some(p => path.startsWith(p))) {
            return new Response("Forbidden path", { status: 403, headers: corsHeaders });
        }

        // Inject API Key from Environment Variable
        const apiKey = env.FINNHUB_KEY;
        if (!apiKey) {
            return new Response("Worker config error: FINNHUB_KEY missing", { status: 500, headers: corsHeaders });
        }

        // Construct upstream URL
        // Ensure we append token correctly (handle existing query params)
        const separator = query.includes("?") ? "&" : "?";
        const upstreamUrl = `${finnhubBase}${path}${query}${separator}token=${apiKey}`;

        try {
            const response = await fetch(upstreamUrl, {
                method: request.method,
                headers: {
                    "Content-Type": "application/json"
                }
            });

            // Return response with CORS
            const data = await response.text();
            return new Response(data, {
                status: response.status,
                headers: {
                    ...corsHeaders,
                    "Content-Type": "application/json"
                }
            });
        } catch (err) {
            return new Response(JSON.stringify({ error: err.message }), { status: 500, headers: corsHeaders });
        }
    },
};
