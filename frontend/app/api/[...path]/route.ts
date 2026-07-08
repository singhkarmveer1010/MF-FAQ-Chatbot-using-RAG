/**
 * Next.js App Router — Catch-all API Proxy Route
 *
 * Proxies every request to /api/<anything> → Railway FastAPI backend.
 * Reads NEXT_PUBLIC_API_URL at *runtime* (not build-time), so changing
 * the env var in Vercel and redeploying always picks up the correct URL.
 */

import { NextRequest, NextResponse } from "next/server";

// Railway backend base URL — set this in Vercel Environment Variables
const RAILWAY_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.RAILWAY_URL ||
  "";

async function handler(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;

  if (!RAILWAY_URL) {
    return NextResponse.json(
      {
        error:
          "Backend URL not configured. Set NEXT_PUBLIC_API_URL in Vercel Environment Variables.",
      },
      { status: 503 }
    );
  }

  // Build the target URL: strip trailing slash from base, then append /api/<path>
  const base = RAILWAY_URL.replace(/\/$/, "");
  const pathStr = path.join("/");
  const search = req.nextUrl.search; // preserve query string e.g. ?background=true
  const targetUrl = `${base}/api/${pathStr}${search}`;

  // Forward all headers except host (which must match the target)
  const forwardHeaders = new Headers(req.headers);
  forwardHeaders.delete("host");

  try {
    const upstream = await fetch(targetUrl, {
      method: req.method,
      headers: forwardHeaders,
      body:
        req.method !== "GET" && req.method !== "HEAD"
          ? await req.arrayBuffer()
          : undefined,
      // @ts-expect-error — Node 18+ fetch supports duplex
      duplex: "half",
    });

    // Stream the response body back
    const responseBody = await upstream.arrayBuffer();
    const responseHeaders = new Headers(upstream.headers);
    // Remove transfer-encoding so Next.js doesn't double-chunk
    responseHeaders.delete("transfer-encoding");

    return new NextResponse(responseBody, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (err) {
    console.error(`[API Proxy] Failed to reach Railway backend at ${targetUrl}:`, err);
    return NextResponse.json(
      {
        error:
          "Unable to reach the Railway backend. Check that your Railway service is running and NEXT_PUBLIC_API_URL is correct.",
        target: targetUrl,
      },
      { status: 502 }
    );
  }
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
export const OPTIONS = handler;
