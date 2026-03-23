# ─── Template strings for bench add-nextjs / bench deploy-nextjs ──────────────
# Placeholders:  {{app}}  {{project}}  {{port}}  {{site}}
# Use: tpl.replace("{{app}}", app).replace("{{project}}", project) etc.

# ── package.json ──────────────────────────────────────────────────────────────
PACKAGE_JSON = """\
{
  "name": "{{project}}",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev":        "next dev",
    "build":      "next build",
    "start":      "next start",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "@frappe-next/core": "github:Ujjwal-Aggrawal2279/frappe-next-sdk#path:packages/core",
    "next":              "latest",
    "react":             "latest",
    "react-dom":         "latest",
    "server-only":       "latest"
  },
  "devDependencies": {
    "@types/node":     "^20",
    "@types/react":    "^19",
    "@types/react-dom":"^19",
    "typescript":      "^5"
  }
}
"""

# ── tsconfig.json ─────────────────────────────────────────────────────────────
TSCONFIG_JSON = """\
{
  "compilerOptions": {
    "target":           "ES2017",
    "lib":              ["dom", "dom.iterable", "esnext"],
    "allowJs":          true,
    "skipLibCheck":     true,
    "strict":           true,
    "noEmit":           true,
    "esModuleInterop":  true,
    "module":           "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule":true,
    "isolatedModules":  true,
    "jsx":              "preserve",
    "incremental":      true,
    "plugins":          [{ "name": "next" }],
    "paths":            { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
"""

# ── next.config.ts ────────────────────────────────────────────────────────────
NEXT_CONFIG_TS = """\
import os   from "os";
import type { NextConfig } from "next";

function getFrappeUrl(): string {
  return (
    process.env.FRAPPE_INTERNAL_URL ??
    process.env.FRAPPE_URL          ??
    "http://127.0.0.1:8000"
  );
}

// Auto-detect all non-loopback IPv4 addresses on this machine so that
// HMR WebSocket works from any LAN/VM host without manual configuration.
// Only relevant in development — skipped entirely in production builds.
function getAllowedDevOrigins(): string[] {
  if (process.env.NODE_ENV === "production") return [];
  const hosts: string[] = [];
  for (const iface of Object.values(os.networkInterfaces())) {
    for (const addr of iface ?? []) {
      if (addr.family === "IPv4" && !addr.internal) hosts.push(addr.address);
    }
  }
  return hosts;
}

const nextConfig: NextConfig = {
  output: "standalone",
  transpilePackages: ["@frappe-next/core"],
  allowedDevOrigins: getAllowedDevOrigins(),

  async rewrites() {
    const frappe = getFrappeUrl();
    return [
      { source: "/api/:path*", destination: `${frappe}/api/:path*` },
      { source: "/assets/:path*", destination: `${frappe}/assets/:path*` },
      { source: "/files/:path*",  destination: `${frappe}/files/:path*`  },
    ];
  },
};

export default nextConfig;
"""

# ── .env.local ────────────────────────────────────────────────────────────────
ENV_LOCAL = """\
# Frappe backend URL (internal/Docker or local bench)
# Local bench: read webserver_port from sites/common_site_config.json
FRAPPE_INTERNAL_URL=http://127.0.0.1:{{port}}

# API Key for Server Actions (mutations that bypass CSRF)
# Generate: Frappe Desk → Settings → Users → <user> → API Access → Generate Keys
FRAPPE_API_KEY=
FRAPPE_API_SECRET=

# Site name (must match your bench site)
FRAPPE_SITE_NAME={{site}}

# Baked into client bundle at BUILD TIME — no secrets here
NEXT_PUBLIC_FRAPPE_SITE={{site}}
"""

# ── .gitignore ────────────────────────────────────────────────────────────────
GITIGNORE = """\
# Next.js
.next/
out/

# Production
build/

# Dependencies
node_modules/
.pnp
.pnp.js

# Environment — NEVER commit secrets
.env.local
.env.*.local

# TypeScript
*.tsbuildinfo
next-env.d.ts

# Misc
.DS_Store
*.pem
npm-debug.log*
yarn-debug.log*
yarn-error.log*
"""

# ── src/proxy.ts (Next.js 16 middleware convention) ───────────────────────────
PROXY_TS = """\
import { createFrappeAuthMiddleware } from "@frappe-next/core/middleware";
import type { NextRequest }           from "next/server";

const handler = createFrappeAuthMiddleware({
  loginPath: "/login",
  publicPaths: [
    "/api/",   // Frappe API rewrites — bypass Next.js auth, Frappe handles its own
    "/health", // Docker healthcheck — must be unauthenticated
  ],
  sessionTimeoutMs: 4000,
});

export function proxy(request: NextRequest) {
  return handler(request);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:svg|png|jpg|jpeg|ico|webp)).*)",
  ],
};
"""

# ── src/app/globals.css ───────────────────────────────────────────────────────
GLOBALS_CSS = """\
*, *::before, *::after {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}
"""

# ── src/app/layout.tsx ────────────────────────────────────────────────────────
LAYOUT_TSX = """\
import type { ReactNode }       from "react";
import { getFrappeBootData }    from "@frappe-next/core/server";
import { FrappeNextProvider }   from "@frappe-next/core/components";
import "./globals.css";

export const metadata = {
  title:       "{{app}} · Frappe Next",
  description: "Next.js + Frappe Framework",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const boot = await getFrappeBootData();

  return (
    <html lang="en">
      <body>
        <FrappeNextProvider
          csrfToken={boot.csrfToken}
          siteName={boot.siteName}
          user={boot.user}
        >
          {children}
        </FrappeNextProvider>
      </body>
    </html>
  );
}
"""

# ── src/app/page.tsx ──────────────────────────────────────────────────────────
PAGE_TSX = """\
import { getList }    from "@frappe-next/core/server";
import styles         from "./page.module.css";

// ISR: re-generate this page every 60 seconds
export const revalidate = 60;

interface FrappeUser {
  name:         string;
  full_name:    string;
  user_type:    string;
  enabled:      number;
}

export default async function HomePage() {
  let users: FrappeUser[] = [];
  let fetchError: string | null = null;

  try {
    users = await getList<FrappeUser>("User", {
      fields:  ["name", "full_name", "user_type", "enabled"],
      filters: [["enabled", "=", "1"]],
      limit:   10,
    });
  } catch (err) {
    fetchError = err instanceof Error ? err.message : "Failed to load users";
  }

  return (
    <main className={styles.container}>
      <h1 className={styles.title}>{{app}} · Frappe Next</h1>
      <p className={styles.subtitle}>
        Server-side rendered with Next.js App Router + Frappe Framework
      </p>

      {fetchError ? (
        <p className={styles.error}>
          {fetchError} — set FRAPPE_API_KEY &amp; FRAPPE_API_SECRET in .env.local
        </p>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Email</th>
              <th>Full Name</th>
              <th>Type</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.name}>
                <td>{u.name}</td>
                <td>{u.full_name}</td>
                <td>{u.user_type}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
"""

# ── src/app/page.module.css ───────────────────────────────────────────────────
PAGE_MODULE_CSS = """\
.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
  margin-bottom: 2rem;
}

.error {
  color: crimson;
  margin-bottom: 2rem;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.table th,
.table td {
  text-align: left;
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid #e5e7eb;
}

.table th {
  background: #f9fafb;
  font-weight: 600;
}
"""

# ── src/app/login/page.tsx ────────────────────────────────────────────────────
LOGIN_PAGE_TSX = """\
"use client";

import { useState, type FormEvent } from "react";
import { useSearchParams }          from "next/navigation";
import { frappeLogin,
         useFrappeRouter }          from "@frappe-next/core/client";
import styles                       from "./login.module.css";

export default function LoginPage() {
  const { navigate }  = useFrappeRouter();
  const searchParams  = useSearchParams();
  const nextPath      = searchParams.get("next") ?? "/";

  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [error,    setError]    = useState<string | null>(null);
  const [loading,  setLoading]  = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await frappeLogin(email, password);
      // Use Frappe's home_page only when there's no explicit ?next= destination.
      // home_page is e.g. "/me" for admin, "/" for regular users.
      const dest = nextPath !== "/" ? nextPath : (result.home_page ?? "/");
      navigate(dest);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className={styles.container}>
      <h1 className={styles.title}>Sign In</h1>
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.field}>
          <label htmlFor="email" className={styles.label}>Email</label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={styles.input}
          />
        </div>
        <div className={styles.field}>
          <label htmlFor="password" className={styles.label}>Password</label>
          <input
            id="password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={styles.input}
          />
        </div>
        {error && <p className={styles.error}>{error}</p>}
        <button type="submit" disabled={loading} className={styles.button}>
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>
    </main>
  );
}
"""

# ── src/app/login/login.module.css ────────────────────────────────────────────
LOGIN_MODULE_CSS = """\
.container {
  display:         flex;
  flex-direction:  column;
  align-items:     center;
  justify-content: center;
  min-height:      100vh;
  padding:         1rem;
  background:      #f9fafb;
}

.title {
  font-size:     1.75rem;
  font-weight:   700;
  margin-bottom: 1.5rem;
}

.form {
  width:         100%;
  max-width:     380px;
  background:    #fff;
  padding:       2rem;
  border-radius: 8px;
  box-shadow:    0 1px 4px rgba(0,0,0,.08);
}

.field {
  display:        flex;
  flex-direction: column;
  gap:            0.35rem;
  margin-bottom:  1rem;
}

.label {
  font-size:   0.85rem;
  font-weight: 500;
}

.input {
  padding:       0.5rem 0.75rem;
  border:        1px solid #d1d5db;
  border-radius: 6px;
  font-size:     0.95rem;
  outline:       none;
}

.input:focus {
  border-color: #6366f1;
  box-shadow:   0 0 0 2px rgba(99,102,241,.2);
}

.error {
  color:         #ef4444;
  font-size:     0.85rem;
  margin-bottom: 0.75rem;
}

.button {
  width:         100%;
  padding:       0.6rem;
  background:    #6366f1;
  color:         #fff;
  border:        none;
  border-radius: 6px;
  font-size:     1rem;
  font-weight:   500;
  cursor:        pointer;
}

.button:hover:not(:disabled) {
  background: #4f46e5;
}

.button:disabled {
  opacity: 0.6;
  cursor:  not-allowed;
}
"""

# ── dev.sh (placed at app root, alongside the next_web/ folder) ───────────────
DEV_SH = """\
#!/usr/bin/env bash
set -euo pipefail

# ── Resolve Node ≥20 ─────────────────────────────────────────────────────────
if [[ -s "$HOME/.nvm/nvm.sh" ]]; then
  # shellcheck source=/dev/null
  source "$HOME/.nvm/nvm.sh"
  nvm use default 2>/dev/null || nvm use node 2>/dev/null || true
fi

NODE_VERSION=$(node --version 2>/dev/null | sed 's/v//')
NODE_MAJOR="${NODE_VERSION%%.*}"
if [[ "${NODE_MAJOR:-0}" -lt 20 ]]; then
  echo "[frappe-next] ERROR: Node.js ≥20 required (found v${NODE_VERSION:-unknown})"
  echo "  Run: nvm alias default 24 && nvm use 24"
  exit 1
fi

# ── Auto-detect bench port from common_site_config.json ──────────────────────
BENCH_ROOT="$(cd "$(dirname "$0")/../../" && pwd)"   # → bench root
SITE_CONFIG="${BENCH_ROOT}/sites/common_site_config.json"

if [[ -f "$SITE_CONFIG" ]]; then
  DETECTED_PORT=$(python3 -c "import json; d=json.load(open('${SITE_CONFIG}')); print(d.get('webserver_port', 8000))")
  DETECTED_SITE=$(python3 -c "import json; d=json.load(open('${SITE_CONFIG}')); print(d.get('default_site', 'site1.localhost'))")
else
  DETECTED_PORT=8000
  DETECTED_SITE=site1.localhost
fi

FRAPPE_PORT="${FRAPPE_PORT:-${DETECTED_PORT}}"
NEXT_PORT="${NEXT_PORT:-3000}"
FRAPPE_SITE_NAME="${FRAPPE_SITE_NAME:-${DETECTED_SITE}}"

echo "[frappe-next] Checking Frappe at http://127.0.0.1:${FRAPPE_PORT}..."
if ! curl -sf "http://127.0.0.1:${FRAPPE_PORT}/api/method/frappe.ping" > /dev/null 2>&1; then
  echo "[frappe-next] ERROR: Frappe not reachable. Run 'bench start' first."
  exit 1
fi
echo "[frappe-next] Frappe OK"

export FRAPPE_INTERNAL_URL="http://127.0.0.1:${FRAPPE_PORT}"
export FRAPPE_URL="http://127.0.0.1:${FRAPPE_PORT}"
export FRAPPE_SITE_NAME
export NEXT_PUBLIC_FRAPPE_SITE="${FRAPPE_SITE_NAME}"

echo ""
echo "[frappe-next] Frappe : http://127.0.0.1:${FRAPPE_PORT}"
echo "[frappe-next] Next.js: http://localhost:${NEXT_PORT}"
echo ""

cd {{project}}
pnpm dev --port "${NEXT_PORT}"
"""

# ── proxy.js (zero-dep Node.js reverse proxy, mirrors production nginx) ────────
PROXY_JS = """\
#!/usr/bin/env node
/**
 * proxy.js — local production simulation proxy
 *
 * Mirrors exactly what nginx does in production — same routing rules,
 * same headers. Zero npm dependencies, pure Node.js built-ins.
 *
 * Routing:
 *   /api/*      → Frappe  (REST API)
 *   /app/*      → Frappe  (desk)
 *   /assets/*   → Frappe  (static assets)
 *   /files/*    → Frappe  (uploaded files)
 *   /private/*  → Frappe  (private files)
 *   /*          → Next.js (your frontend)
 */

'use strict'

const http = require('http')

const FRAPPE_HOST = process.env.FRAPPE_HOST ?? '127.0.0.1'
const FRAPPE_PORT = parseInt(process.env.FRAPPE_PORT ?? '8000', 10)
const NEXT_HOST   = process.env.NEXT_HOST   ?? '127.0.0.1'
const NEXT_PORT   = parseInt(process.env.NEXT_PORT   ?? '3000', 10)
const PROXY_PORT  = parseInt(process.env.PROXY_PORT  ?? '8080', 10)

// Paths that belong to Frappe — everything else goes to Next.js
const FRAPPE_PREFIXES = [
  '/api/', '/app/', '/assets/', '/files/', '/private/', '/socket.io/',
  '/me', '/update-password', '/print/', '/list/', '/form/', '/tree/', '/report/', '/dashboard/',
]

function isForFrappe(url) {
  if (FRAPPE_PREFIXES.some(p => url === p.slice(0, -1) || url.startsWith(p))) return true
  // Root-path Frappe commands: /?cmd=web_logout etc.
  if (url.startsWith('/?cmd=') || url === '/?cmd') return true
  return false
}

function forward(req, res, host, port) {
  const upstream = http.request(
    {
      hostname: host,
      port,
      path:     req.url,
      method:   req.method,
      headers:  { ...req.headers, host: `${host}:${port}` },
    },
    upstreamRes => {
      res.writeHead(upstreamRes.statusCode ?? 502, upstreamRes.headers)
      upstreamRes.pipe(res, { end: true })
    },
  )

  upstream.on('error', err => {
    if (!res.headersSent) res.writeHead(502, { 'Content-Type': 'text/plain' })
    res.end(`Upstream error (${host}:${port}): ${err.message}`)
  })

  req.pipe(upstream, { end: true })
}

const server = http.createServer((req, res) => {
  const [host, port] = isForFrappe(req.url ?? '/')
    ? [FRAPPE_HOST, FRAPPE_PORT]
    : [NEXT_HOST,   NEXT_PORT]

  forward(req, res, host, port)
})

server.listen(PROXY_PORT, '0.0.0.0', () => {
  const line = '─'.repeat(50)
  console.log(`\\n  ┌${line}┐`)
  console.log(`  │  frappe-next · local production proxy              │`)
  console.log(`  └${line}┘\\n`)
  console.log(`  Open   →  http://localhost:${PROXY_PORT}`)
  console.log(`  Next   →  http://${NEXT_HOST}:${NEXT_PORT}`)
  console.log(`  Frappe →  http://${FRAPPE_HOST}:${FRAPPE_PORT}\\n`)
})
"""

# ── prod.sh (production simulation: build + start + proxy) ───────────────────
PROD_SH = """\
#!/usr/bin/env bash
# prod.sh — local production simulation
# Builds Next.js, runs the production server, and starts the proxy.
# Access everything at http://localhost:${PROXY_PORT} — identical to production nginx.
set -euo pipefail

# ── Resolve Node ≥20 ──────────────────────────────────────────────────────────
# nvm only activates in interactive shells. Load it explicitly so non-interactive
# shells (e.g. `bash prod.sh`) also get the correct node version.
if [[ -s "$HOME/.nvm/nvm.sh" ]]; then
  # shellcheck source=/dev/null
  source "$HOME/.nvm/nvm.sh"
  nvm use default 2>/dev/null || nvm use node 2>/dev/null || true
fi

NODE_VERSION=$(node --version 2>/dev/null | sed 's/v//')
NODE_MAJOR="${NODE_VERSION%%.*}"
if [[ "${NODE_MAJOR:-0}" -lt 20 ]]; then
  echo "[frappe-next] ERROR: Node.js ≥20 required (found v${NODE_VERSION:-unknown})"
  echo "  Run: nvm alias default 24 && nvm use 24"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BENCH_ROOT="$(cd "${SCRIPT_DIR}/../../" && pwd)"
SITE_CONFIG="${BENCH_ROOT}/sites/common_site_config.json"

if [[ -f "$SITE_CONFIG" ]]; then
  FRAPPE_PORT=$(python3 -c "import json; d=json.load(open('${SITE_CONFIG}')); print(d.get('webserver_port', 8000))")
  FRAPPE_SITE=$(python3 -c "import json; d=json.load(open('${SITE_CONFIG}')); print(d.get('default_site', 'site1.localhost'))")
else
  FRAPPE_PORT=8000
  FRAPPE_SITE=site1.localhost
fi

FRAPPE_PORT="${FRAPPE_PORT:-8000}"
NEXT_PORT="${NEXT_PORT:-3000}"
PROXY_PORT="${PROXY_PORT:-8080}"

# ── Release ports from any previous run ───────────────────────────────────────
fuser -k "${NEXT_PORT}/tcp"  2>/dev/null || true
fuser -k "${PROXY_PORT}/tcp" 2>/dev/null || true
sleep 1

echo "[frappe-next] Checking Frappe at http://127.0.0.1:${FRAPPE_PORT}..."
if ! curl -sf "http://127.0.0.1:${FRAPPE_PORT}/api/method/frappe.ping" > /dev/null 2>&1; then
  echo "[frappe-next] ERROR: Frappe not reachable. Run 'bench start' first."
  exit 1
fi
echo "[frappe-next] Frappe OK"

echo ""
echo "[frappe-next] Building Next.js production bundle..."
cd "${SCRIPT_DIR}/{{project}}"

export FRAPPE_INTERNAL_URL="http://127.0.0.1:${FRAPPE_PORT}"
export FRAPPE_URL="http://127.0.0.1:${FRAPPE_PORT}"
export FRAPPE_SITE_NAME="${FRAPPE_SITE}"
export NEXT_PUBLIC_FRAPPE_SITE="${FRAPPE_SITE}"

pnpm build

# standalone server doesn't bundle static assets — copy them in
cp -r .next/static  .next/standalone/.next/static
cp -r public        .next/standalone/public

echo ""
echo "[frappe-next] Starting Next.js production server on port ${NEXT_PORT}..."
PORT="${NEXT_PORT}" HOSTNAME="0.0.0.0" node .next/standalone/server.js &
NEXT_PID=$!

sleep 2

cd "${SCRIPT_DIR}"
FRAPPE_PORT="${FRAPPE_PORT}" \\
NEXT_PORT="${NEXT_PORT}"     \\
PROXY_PORT="${PROXY_PORT}"   \\
node proxy.js &
PROXY_PID=$!

trap "kill ${NEXT_PID} ${PROXY_PID} 2>/dev/null; exit 0" INT TERM

wait
"""

# ── src/app/api/health/route.ts ───────────────────────────────────────────────
# WARNING: Do not delete — used by Docker healthcheck and load balancers.
HEALTH_ROUTE_TS = """\
// ⚠️  Do not delete — required by Docker healthcheck and load balancers.
// GET /health → { status: 'ok' }
export function GET() {
  return Response.json({ status: 'ok' })
}
"""

# ── src/app/[...frappe]/route.ts ───────────────────────────────────────────────
# Dynamic Frappe fallback — proxies any path not matched by a Next.js page.
# App Router guarantees static pages always take priority over this catch-all.
FRAPPE_FALLBACK_ROUTE_TS = """\
// Dynamic Frappe fallback — proxies any path not matched by a Next.js page to Frappe.
//
// Routing priority in App Router guarantees static pages always win:
//   /login             → app/login/page.tsx        (your page)
//   /products          → app/products/page.tsx     (your page)
//   /me                → this file                 (Frappe fallback)
//   /update-password   → this file                 (Frappe fallback)
//
// Do NOT add Frappe paths to any static list — this handles them dynamically.

import { type NextRequest, NextResponse } from 'next/server'

const FRAPPE_URL = process.env.FRAPPE_INTERNAL_URL ?? 'http://localhost:8000'
const SITE_NAME  = process.env.FRAPPE_SITE_NAME    ?? 'site1.localhost'

// Hop-by-hop headers must not be forwarded
const HOP_BY_HOP = new Set([
  'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
  'te', 'trailers', 'transfer-encoding', 'upgrade',
])

async function proxy(req: NextRequest, segments: string[]): Promise<NextResponse> {
  const path   = '/' + segments.join('/')
  const target = new URL(path + req.nextUrl.search, FRAPPE_URL)

  const upstream = new Headers()
  req.headers.forEach((v, k) => {
    if (!HOP_BY_HOP.has(k.toLowerCase())) upstream.set(k, v)
  })
  upstream.set('X-Frappe-Site-Name', SITE_NAME)
  upstream.delete('host')

  const isBodyMethod = req.method !== 'GET' && req.method !== 'HEAD'

  const res = await fetch(target, {
    method:   req.method,
    headers:  upstream,
    body:     isBodyMethod ? req.body : undefined,
    redirect: 'manual',
    ...(isBodyMethod ? { duplex: 'half' } : {}),
    signal: AbortSignal.timeout(30_000),
  })

  const responseHeaders = new Headers()
  res.headers.forEach((v, k) => {
    if (!HOP_BY_HOP.has(k.toLowerCase())) responseHeaders.set(k, v)
  })

  return new NextResponse(res.body, {
    status:  res.status,
    headers: responseHeaders,
  })
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ frappe: string[] }> },
) {
  return proxy(req, (await params).frappe)
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ frappe: string[] }> },
) {
  return proxy(req, (await params).frappe)
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ frappe: string[] }> },
) {
  return proxy(req, (await params).frappe)
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ frappe: string[] }> },
) {
  return proxy(req, (await params).frappe)
}
"""

# ── docker/Dockerfile ──────────────────────────────────────────────────────────
# Multi-stage build: deps → build → minimal runtime (node:24-alpine)
# output: standalone produces a self-contained server.js with zero node_modules
DOCKERFILE = """\
# ─── Stage 1: Install dependencies ───────────────────────────────────────────
FROM node:24-alpine AS deps
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \\
    pnpm install --frozen-lockfile

# ─── Stage 2: Build ───────────────────────────────────────────────────────────
FROM node:24-alpine AS builder
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

# ─── Stage 3: Production runtime ──────────────────────────────────────────────
FROM node:24-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs \\
 && adduser  --system --uid 1001 nextjs

# Standalone server (includes all server-side deps, no node_modules needed)
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./

# Client bundles — must live at .next/static relative to server.js
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Public directory (images, fonts, robots.txt, etc.)
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
"""

# ── docker/nginx.conf.template ─────────────────────────────────────────────────
# Replaces frappe_docker's default nginx template.
# Routes: Frappe-owned paths → backend; everything else → nextjs:3000
# "nextjs" is the Docker Compose service name — always resolves within the network.
DOCKER_NGINX_CONF = """\
# ─── Upstreams ────────────────────────────────────────────────────────────────
upstream backend-server {
    server ${BACKEND} fail_timeout=0;
}

upstream socketio-server {
    server ${SOCKETIO} fail_timeout=0;
}

# Next.js standalone server — service name resolves via Docker DNS
upstream nextjs-server {
    server nextjs:3000 fail_timeout=0;
}

map $http_x_forwarded_proto $proxy_x_forwarded_proto {
    default $scheme;
    https   https;
}

server {
    listen 8080;
    server_name ${FRAPPE_SITE_NAME_HEADER};
    root /home/frappe/frappe-bench/sites;

    proxy_buffer_size       128k;
    proxy_buffers           4 256k;
    proxy_busy_buffers_size 256k;

    include /etc/nginx/snippets/security_headers.conf;

    set_real_ip_from   ${UPSTREAM_REAL_IP_ADDRESS};
    real_ip_header     ${UPSTREAM_REAL_IP_HEADER};
    real_ip_recursive  ${UPSTREAM_REAL_IP_RECURSIVE};

    # ── Frappe static assets (served from sites volume) ────────────────────────
    location /assets {
        try_files $uri =404;
        add_header Cache-Control "max-age=31536000";
    }

    location ~ ^/protected/(.*) {
        internal;
        try_files /${FRAPPE_SITE_NAME_HEADER}/$1 =404;
    }

    # ── Frappe WebSocket (realtime) ────────────────────────────────────────────
    location /socket.io {
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto;
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        "upgrade";
        proxy_set_header X-Frappe-Site-Name ${FRAPPE_SITE_NAME_HEADER};
        proxy_set_header Origin            $proxy_x_forwarded_proto://${FRAPPE_SITE_NAME_HEADER};
        proxy_set_header Host              $host;
        proxy_pass http://socketio-server;
    }

    # ── Frappe REST API ────────────────────────────────────────────────────────
    location /api/ {
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For    $remote_addr;
        proxy_set_header X-Forwarded-Proto  $proxy_x_forwarded_proto;
        proxy_set_header X-Frappe-Site-Name ${FRAPPE_SITE_NAME_HEADER};
        proxy_set_header Host               $host;
        proxy_read_timeout ${PROXY_READ_TIMEOUT};
        proxy_redirect off;
        proxy_pass http://backend-server;
    }

    # ── Frappe Desk ────────────────────────────────────────────────────────────
    # Only /app is routed directly to Frappe for performance.
    # All other Frappe paths (/me, /update-password, /print, etc.) are handled
    # dynamically by Next.js app/[...frappe]/route.ts → proxied to Frappe.
    location /app {
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For    $remote_addr;
        proxy_set_header X-Forwarded-Proto  $proxy_x_forwarded_proto;
        proxy_set_header X-Frappe-Site-Name ${FRAPPE_SITE_NAME_HEADER};
        proxy_set_header Host               $host;
        proxy_set_header X-Use-X-Accel-Redirect True;
        proxy_read_timeout ${PROXY_READ_TIMEOUT};
        proxy_redirect off;
        proxy_pass http://backend-server;
    }

    # ── Frappe file downloads ──────────────────────────────────────────────────
    location /files/ {
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For    $remote_addr;
        proxy_set_header X-Forwarded-Proto  $proxy_x_forwarded_proto;
        proxy_set_header X-Frappe-Site-Name ${FRAPPE_SITE_NAME_HEADER};
        proxy_set_header Host               $host;
        proxy_set_header X-Use-X-Accel-Redirect True;
        proxy_read_timeout ${PROXY_READ_TIMEOUT};
        proxy_redirect off;
        proxy_pass http://backend-server;
    }

    # ── Frappe private files ───────────────────────────────────────────────────
    location /private/ {
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For    $remote_addr;
        proxy_set_header X-Forwarded-Proto  $proxy_x_forwarded_proto;
        proxy_set_header X-Frappe-Site-Name ${FRAPPE_SITE_NAME_HEADER};
        proxy_set_header Host               $host;
        proxy_set_header X-Use-X-Accel-Redirect True;
        proxy_read_timeout ${PROXY_READ_TIMEOUT};
        proxy_redirect off;
        proxy_pass http://backend-server;
    }

    # ── Next.js — everything else (SSR, ISR, /_next/*, custom pages) ──────────
    location / {
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For   $remote_addr;
        proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto;
        proxy_set_header Host              $host;
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        "upgrade";
        proxy_read_timeout ${PROXY_READ_TIMEOUT};
        proxy_redirect off;
        proxy_pass http://nextjs-server;
    }

    sendfile on;
    keepalive_timeout 15;
    client_max_body_size    ${CLIENT_MAX_BODY_SIZE};
    client_body_buffer_size 16K;
    client_header_buffer_size 1k;

    gzip on;
    gzip_http_version 1.1;
    gzip_comp_level   5;
    gzip_min_length   256;
    gzip_proxied      any;
    gzip_vary         on;
    gzip_types
        application/atom+xml
        application/javascript
        application/json
        application/rss+xml
        application/vnd.ms-fontobject
        application/x-font-ttf
        application/font-woff
        application/x-web-app-manifest+json
        application/xhtml+xml
        application/xml
        font/opentype
        image/svg+xml
        image/x-icon
        text/css
        text/plain
        text/x-component;
}
"""

# ── docker/compose.nextjs.yaml ────────────────────────────────────────────────
# Override for frappe_docker — adds the Next.js service and extends the frontend
# nginx with the custom routing template above.
#
# Usage from your frappe_docker directory:
#   docker compose \\
#     -f compose.yaml \\
#     -f overrides/compose.mariadb.yaml \\
#     -f overrides/compose.redis.yaml \\
#     -f overrides/compose.noproxy.yaml \\
#     -f /abs/path/to/apps/{{app}}/docker/compose.nextjs.yaml \\
#     up -d
DOCKER_COMPOSE_YAML = """\
# docker/compose.nextjs.yaml — frappe_docker override for {{app}}/{{project}}
#
# Two env vars must be set in your frappe_docker .env before running:
#
#   NEXTJS_BUILD_CONTEXT=/abs/path/to/apps/{{app}}/{{project}}
#   NEXTJS_DOCKER_DIR=/abs/path/to/apps/{{app}}/docker/
#
# Then from your frappe_docker directory:
#
#   docker compose \\\\
#     -f compose.yaml \\\\
#     -f overrides/compose.mariadb.yaml \\\\
#     -f overrides/compose.redis.yaml \\\\
#     -f overrides/compose.noproxy.yaml \\\\
#     -f /abs/path/to/apps/{{app}}/docker/compose.nextjs.yaml \\\\
#     up -d --build

services:

  # ── Next.js standalone server ─────────────────────────────────────────────
  nextjs:
    build:
      context: ${NEXTJS_BUILD_CONTEXT}   # absolute path — set in frappe_docker .env
      dockerfile: Dockerfile
    image: {{app}}_nextjs:latest
    restart: unless-stopped
    environment:
      NODE_ENV:                production
      FRAPPE_INTERNAL_URL:     http://backend:8000   # direct to gunicorn, no nginx hop
      FRAPPE_SITE_NAME:        ${FRAPPE_SITE_NAME_HEADER:-localhost}
      FRAPPE_API_KEY:          ${FRAPPE_API_KEY:-}
      FRAPPE_API_SECRET:       ${FRAPPE_API_SECRET:-}
      NEXT_PUBLIC_FRAPPE_SITE: ${FRAPPE_SITE_NAME_HEADER:-localhost}
    depends_on:
      backend:
        condition: service_started
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:3000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # ── Extend Frappe's nginx with Next.js routing ────────────────────────────
  frontend:
    volumes:
      - ${NEXTJS_DOCKER_DIR}nginx.conf.template:/templates/nginx/frappe.conf.template:ro
    depends_on:
      nextjs:
        condition: service_started
"""
