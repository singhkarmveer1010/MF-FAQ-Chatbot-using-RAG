/**
 * Next.js App Router — Catch-all API Proxy Route
 *
 * Proxies every request to /api/<anything> → Railway FastAPI backend.
 * Reads the backend URL from environment variables at REQUEST TIME
 * (inside the handler, not at module scope) to ensure Vercel serverless
 * always picks up the correct value.
 *
 * Supported env vars (checked in order):
 *   1. BACKEND_URL          — server-side only, recommended for Vercel
 *   2. NEXT_PUBLIC_API_URL  — works but exposed to client bundle
 *
 * Timeout: 25s AbortController to stay within Vercel's serverless limit.
 */

import { NextRequest, NextResponse } from "next/server";

/** Maximum time (ms) to wait for the Railway backend before aborting. */
const PROXY_TIMEOUT_MS = 25_000;

function getBackendUrl(): string {
  // Read inside the function, NOT at module scope.
  // This guarantees Vercel serverless reads the env var on every cold start.
  return (
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "https://mf-faq-chatbot-using-rag-production.up.railway.app"
  );
}

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxyToBackend(req, context);
}

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxyToBackend(req, context);
}

export async function PUT(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxyToBackend(req, context);
}

export async function PATCH(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxyToBackend(req, context);
}

export async function DELETE(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxyToBackend(req, context);
}

export async function OPTIONS(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxyToBackend(req, context);
}

async function proxyToBackend(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const backendUrl = getBackendUrl();
  const { path } = await context.params;

  if (!backendUrl) {
    console.error(
      "[API Proxy] No backend URL configured. Set BACKEND_URL or NEXT_PUBLIC_API_URL in Vercel env vars."
    );
    return NextResponse.json(
      {
        error:
          "Backend URL not configured. Set BACKEND_URL (or NEXT_PUBLIC_API_URL) in Vercel → Settings → Environment Variables.",
      },
      { status: 503 }
    );
  }

  // Build target URL
  const base = backendUrl.replace(/\/+$/, "");
  const pathStr = path.join("/");
  const search = req.nextUrl.search; // preserve query params
  const targetUrl = `${base}/api/${pathStr}${search}`;

  // Forward headers (strip host so it matches the target)
  const forwardHeaders = new Headers();
  req.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower !== "host" && lower !== "connection") {
      forwardHeaders.set(key, value);
    }
  });

  console.log(
    `[API Proxy] ${req.method} /api/${pathStr} → ${targetUrl}`
  );

  // AbortController for timeout protection
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), PROXY_TIMEOUT_MS);

  try {
    // Read body for non-GET/HEAD requests
    let body: ArrayBuffer | undefined;
    if (req.method !== "GET" && req.method !== "HEAD") {
      try {
        body = await req.arrayBuffer();
      } catch {
        // empty body is fine
      }
    }

    const upstream = await fetch(targetUrl, {
      method: req.method,
      headers: forwardHeaders,
      body,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    console.log(
      `[API Proxy] ${req.method} /api/${pathStr} ← ${upstream.status} ${upstream.statusText}`
    );

    const responseBody = await upstream.arrayBuffer();
    const responseHeaders = new Headers();
    upstream.headers.forEach((value, key) => {
      const lower = key.toLowerCase();
      // Skip hop-by-hop headers
      if (lower !== "transfer-encoding" && lower !== "connection") {
        responseHeaders.set(key, value);
      }
    });

    return new NextResponse(responseBody, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (err: unknown) {
    clearTimeout(timeoutId);

    // Distinguish timeout from connection errors for better debugging
    const isAbort =
      err instanceof DOMException && err.name === "AbortError";
    const errMsg =
      err instanceof Error ? err.message : String(err);

    if (isAbort) {
      console.error(
        `[API Proxy] TIMEOUT after ${PROXY_TIMEOUT_MS}ms reaching ${targetUrl}`
      );
      return NextResponse.json(
        {
          error: `The backend at ${base} did not respond within ${PROXY_TIMEOUT_MS / 1000}s. The Railway service may be cold-starting or overloaded — please retry in a few seconds.`,
        },
        { status: 504 }
      );
    }

    console.error(
      `[API Proxy] Failed to reach Railway backend at ${targetUrl}:`,
      errMsg
    );

    // Provide actionable error messages
    const isConnectionRefused =
      errMsg.includes("ECONNREFUSED") || errMsg.includes("connect");
    const isDns =
      errMsg.includes("ENOTFOUND") || errMsg.includes("getaddrinfo");

    let userMessage: string;
    if (isDns) {
      userMessage = `DNS resolution failed for ${base}. The Railway service URL may be incorrect — verify BACKEND_URL in Vercel env vars.`;
    } else if (isConnectionRefused) {
      userMessage = `Connection refused by ${base}. The Railway service may not be running — check Railway Dashboard.`;
    } else {
      userMessage = `Unable to reach the Railway backend at ${base}. Verify the service is running and the URL is correct.`;
    }

    return NextResponse.json({ error: userMessage }, { status: 502 });
  }
}
