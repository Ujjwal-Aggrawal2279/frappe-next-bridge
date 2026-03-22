# ─── Template strings for bench add-nextjs ────────────────────────────────────
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
    "@frappe-next/core": "github:Ujjwal-Aggrawal2279/frappe-next-sdk#main",
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
import type { NextConfig } from "next";

function getFrappeUrl(): string {
  return (
    process.env.FRAPPE_INTERNAL_URL ??
    process.env.FRAPPE_URL          ??
    "http://127.0.0.1:8000"
  );
}

const nextConfig: NextConfig = {
  output: "standalone",

  async rewrites() {
    const frappe = getFrappeUrl();
    return [
      { source: "/api/method/:path*",   destination: `${frappe}/api/method/:path*`   },
      { source: "/api/resource/:path*", destination: `${frappe}/api/resource/:path*` },
      { source: "/assets/:path*",       destination: `${frappe}/assets/:path*`       },
      { source: "/files/:path*",        destination: `${frappe}/files/:path*`        },
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
    "/api/",  // ALL Frappe API calls bypass our auth check
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
  const users = await getList<FrappeUser>("User", {
    fields:  ["name", "full_name", "user_type", "enabled"],
    filters: [["enabled", "=", "1"]],
    limit:   10,
  });

  return (
    <main className={styles.container}>
      <h1 className={styles.title}>{{app}} · Frappe Next</h1>
      <p className={styles.subtitle}>
        Server-side rendered with Next.js App Router + Frappe Framework
      </p>

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

import { useState, type FormEvent }   from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { frappeClientPost }           from "@frappe-next/core/client";
import styles                         from "./login.module.css";

export default function LoginPage() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const nextPath     = searchParams.get("next") ?? "/";

  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [error,    setError]    = useState<string | null>(null);
  const [loading,  setLoading]  = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // frappeClientPost returns data.message — Frappe returns "Logged In" (string)
      const result = await frappeClientPost<string>("login", {
        usr: email,
        pwd: password,
      });

      if (result === "Logged In") {
        router.push(nextPath);
        router.refresh();
      } else {
        setError("Login failed. Check your credentials.");
      }
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
