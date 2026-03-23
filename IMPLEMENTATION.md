# frappe-next-bridge — Implementation Reference

Complete record of everything implemented across both repositories.

---

## Repository Map

```
frappe-next-sdk/                     → npm package  (@frappe-next/core)
  packages/core/src/
    types/index.ts                   → shared TypeScript types
    server/index.ts                  → Server Component helpers
    client/index.ts                  → browser-side fetch + router
    middleware/index.ts              → Next.js Edge middleware
    components/FrappeProvider.tsx    → React context provider

frappe_next_bridge/                  → Frappe app  (bench CLI)
  frappe_next_bridge/
    commands/
      __init__.py                    → bench add-nextjs + deploy-nextjs entry points
      nextjs_generator.py            → scaffold logic
      boilerplates.py                → all generated file templates
      deploy_nextjs.py               → dedicated server deployment
    hooks.py                         → CORS allow_cors for dev
    api.py                           → (reserved for future Frappe whitelisted APIs)
```

---

## @frappe-next/core — Package

### Package Exports

| Export path | What it provides |
|---|---|
| `@frappe-next/core/server` | `getDoc`, `getDocOrNull`, `getList`, `getCount`, `frappeGet`, `frappePost`, `getFrappeBootData`, `fetchCsrfToken`, `revalidateDoc`, `revalidateList`, error classes |
| `@frappe-next/core/client` | `frappeClientGet`, `frappeClientPost`, `frappeLogin`, `useFrappeRouter` |
| `@frappe-next/core/middleware` | `createFrappeAuthMiddleware` |
| `@frappe-next/core/components` | `FrappeNextProvider`, `useFrappeNext` |
| `@frappe-next/core/actions` | Server Actions helpers |
| `@frappe-next/core/types` | All shared TypeScript interfaces |

Ships source TypeScript directly — no build step. Installed via:
```json
"@frappe-next/core": "github:Ujjwal-Aggrawal2279/frappe-next-sdk#path:packages/core"
```

---

### `@frappe-next/core/server`

All functions are **server-only** (`import 'server-only'`). Safe to use in Server Components, `generateStaticParams`, `generateMetadata`, and Server Actions.

#### URL Resolution (priority order)
```
FRAPPE_INTERNAL_URL  →  Docker (http://backend:8000, direct to gunicorn)
FRAPPE_URL           →  explicit override
http://127.0.0.1:8000  →  local bench fallback
```

#### Auth Strategy
Every server-side Frappe call builds auth headers from two sources:

**Session headers** (`buildSessionHeaders`):
- Reads `sid` cookie from the incoming Next.js request via `cookies()`
- Reads `csrf_token` cookie for CSRF protection
- **Always includes `X-Frappe-Site-Name`** from `FRAPPE_SITE_NAME` env var
  *(Critical fix: without this, direct calls to Frappe backend fail to resolve the session to the correct site)*
- Falls back gracefully if called outside request context (build time, cron jobs)

**API key headers** (`buildApiKeyHeaders`):
- Uses `FRAPPE_API_KEY:FRAPPE_API_SECRET` from env
- Returns `null` if not configured
- Used by `frappePost` as preference over session (bypasses CSRF server-to-server)

#### `getDoc<T>(doctype, name, options?)`
Fetches a single Frappe document. Uses React `cache()` to deduplicate — 10 Server Components calling `getDoc('Item','ITEM-001')` in the same request = exactly 1 Frappe API call. Tagged for ISR invalidation as `${doctype}::${name}`.

#### `getDocOrNull<T>(doctype, name, options?)`
Same as `getDoc` but returns `null` on 404 instead of throwing. Use when the document may or may not exist.

#### `getList<T>(doctype, args?, options?)`
Fetches a list of documents. Supports:
- `fields` — which fields to return (default: `['name', 'modified']`)
- `filters` — `[fieldname, operator, value][]`
- `or_filters` — OR-combined filters
- `limit` / `limit_start` — pagination
- `order_by` — sort order

Tagged with `doctype` for ISR invalidation.

#### `getCount(doctype, filters?, options?)`
Returns the count of matching documents.

#### `frappeGet<T>(method, params?, options?)`
Low-level GET to any `frappe.whitelist()` method. Used internally by `getDoc`/`getList`. Pass `options.next` for ISR:
```typescript
frappeGet('myapp.api.get_products', {}, { next: { revalidate: 60, tags: ['Product'] } })
```

#### `frappePost<T>(method, body?, options?)`
Low-level POST to any `frappe.whitelist()` method. Prefers API key auth, falls back to session cookie.

#### `getFrappeBootData()`
Returns `{ csrfToken, user, siteName }` for injecting into `FrappeNextProvider`. Reads `x-frappe-user` header injected by middleware (set during session verification, no extra Frappe call). Uses React `cache()`.

#### `fetchCsrfToken()`
Fetches CSRF token from `frappe.sessions.get_csrf_token`. Memoized per request with React `cache()`.

#### ISR Cache Invalidation
```typescript
revalidateDoc('Item', 'ITEM-001')   // invalidates getDoc cache for this doc
revalidateList('Item')              // invalidates all getList caches for Item
```
Call from Server Actions after mutations. Pairs with the `tags` set by `getDoc`/`getList`.

#### Error Classes
| Class | HTTP status | When thrown |
|---|---|---|
| `FrappeApiError` | any non-ok | base class, includes `status`, `method`, `details` |
| `FrappeAuthError` | 403 | session expired or insufficient permissions |
| `FrappeNotFoundError` | 404 | document or resource not found |

#### Request Timeout
Default 8 seconds. Override with `FRAPPE_REQUEST_TIMEOUT=10000` (ms) in `.env.local`.

---

### `@frappe-next/core/client`

All functions are **client-side** (`'use client'`). Use in Client Components. All fetches use relative URLs — the browser auto-sends cookies.

#### `frappeClientGet<T>(method, params?)`
Browser-side GET to any Frappe method. Returns `data.message`.

#### `frappeClientPost<T>(method, body?)`
Browser-side POST. Reads CSRF token from `window.csrf_token` (injected by `FrappeNextProvider`) or from the `csrf_token` cookie. Returns `data.message`.

#### `frappeLogin(usr, pwd)`
Dedicated login function. Unlike `frappeClientPost`, returns the **full Frappe response body** (not just `.message`) because the login response includes `home_page` and `full_name` as siblings to `message`:
```typescript
interface FrappeLoginResponse {
  message:    string    // "Logged In" | "No App"
  home_page?: string    // e.g. "/me", "/" — use for post-login redirect
  full_name?: string
}
```
Use this to redirect after login:
```typescript
const result = await frappeLogin(email, password)
const dest = nextPath !== '/' ? nextPath : (result.home_page ?? '/')
navigate(dest)
```

#### `useFrappeRouter()`
Smart router hook that automatically decides between Next.js client-side navigation and full-page navigation for Frappe-owned paths.

```typescript
const { navigate, toDesk, toDoc } = useFrappeRouter()

navigate('/products')           // → router.push (SPA, no reload)
navigate('/me')                 // → window.location.href (Frappe path, full reload)
navigate('/app/sales-order')    // → window.location.href (Frappe desk)

toDesk()                        // → /app
toDesk('item')                  // → /app/item
toDoc('Sales Order', 'SO-0001') // → /app/sales-order/SO-0001
```

**Frappe-owned paths** (always full-page):
```
/app  /api  /assets  /files  /private
/me  /update-password  /print  /list  /form  /tree  /report  /dashboard
```

---

### `@frappe-next/core/middleware`

#### `createFrappeAuthMiddleware(config)`
Returns a Next.js middleware function. Call once at module level in `src/proxy.ts`.

```typescript
const handler = createFrappeAuthMiddleware({
  loginPath:        '/login',       // default
  publicPaths:      ['/api/', '/health'],
  sessionTimeoutMs: 4000,           // default
  frappeUrl:        '...',          // optional override (reads env vars by default)
})
```

**Request processing order:**
1. Skip `/_next/`, `/favicon.ico`, `loginPath`, and `publicPaths` — no session check
2. **Root-path `?cmd=` intercept** — `/?cmd=web_logout` etc. → redirect to `/api/?cmd=...`
   *(Critical: `[...frappe]` catch-all requires ≥1 path segment, so root Frappe commands never reach it. This redirect sends them through nginx → Frappe)*
3. No `sid` cookie or `sid === 'Guest'` → redirect to `loginPath?next=...&reason=no_session`
4. Verify session against Frappe (`frappe.auth.get_logged_user`) with `X-Frappe-Site-Name` header
5. Session invalid → redirect to login, delete `sid` cookie
6. Session valid → inject `x-frappe-user: <email>` into request headers for downstream Server Components

**Session verification:**
- Calls `FRAPPE_INTERNAL_URL/api/method/frappe.auth.get_logged_user`
- Sends `Cookie: sid=<value>` and `X-Frappe-Site-Name: <site>`
- Times out after `sessionTimeoutMs` (AbortController)
- Returns `null` on timeout, network error, or non-ok response

**Edge Runtime compatible** — zero Node.js-only APIs (no `Buffer`, `fs`, `crypto`).

---

### `@frappe-next/core/components`

#### `FrappeNextProvider`
React context provider. Place in `layout.tsx`. Injects CSRF token into `window.csrf_token` for client-side POST calls.

```typescript
// layout.tsx (Server Component)
const boot = await getFrappeBootData()
return <FrappeNextProvider {...boot}>{children}</FrappeNextProvider>
```

#### `useFrappeNext()`
Returns `{ csrfToken, siteName, user, hydrated }` in Client Components.

---

### `@frappe-next/core/types`

Key interfaces:

| Type | Description |
|---|---|
| `FrappeDoc` | Base document fields (`name`, `owner`, `creation`, `modified`, `docstatus`, etc.) |
| `FrappeEnvelope<T>` | Frappe API response wrapper `{ message: T, exc_type?, ... }` |
| `FrappeFilter` | `[fieldname, operator, value]` tuple |
| `GetListArgs` | `getList` options |
| `FrappeFetchOptions` | `{ next?, headers?, skipSession? }` for ISR + custom headers |
| `BootData` | `{ csrfToken, user, siteName }` |
| `ActionResult<T>` | `{ ok: true, data: T } \| { ok: false, error: string }` for Server Actions |

---

## frappe_next_bridge — Frappe App (CLI)

### Installation

```bash
bench get-app frappe_next_bridge https://github.com/Ujjwal-Aggrawal2279/frappe-next-bridge
bench install-app frappe_next_bridge
```

Adds two bench commands: `bench add-nextjs` and `bench deploy-nextjs`.

---

### `bench add-nextjs`

Scaffolds a complete production-ready Next.js App Router project inside any Frappe app directory.

```bash
bench add-nextjs                              # interactive app picker
bench add-nextjs --app my_erp                 # direct
bench add-nextjs --app my_erp --project-name dashboard
```

#### What it generates

```
apps/
  <app>/
    <project>/                 default: next_web
      package.json             Next.js + @frappe-next/core dependencies
      tsconfig.json            strict TypeScript, bundler resolution
      next.config.ts           ISR rewrites, standalone output, HMR origins
      .env.local               FRAPPE_INTERNAL_URL, FRAPPE_SITE_NAME, API key slots
      .gitignore               excludes .next/, node_modules/, .env.local
      Dockerfile               multi-stage build, standalone output
      src/
        proxy.ts               Next.js middleware (auth guard)
        app/
          globals.css
          layout.tsx           FrappeNextProvider wired up
          page.tsx             demo home page (getList with try/catch)
          page.module.css
          login/
            page.tsx           login form (frappeLogin + home_page redirect)
            login.module.css
          health/
            route.ts           GET /health → {"status":"ok"}
          [...frappe]/
            route.ts           dynamic Frappe fallback proxy
    dev.sh                     local dev launcher (chmod +x)
    prod.sh                    production simulation launcher (chmod +x)
    proxy.js                   zero-dep Node.js reverse proxy
    docker/
      compose.nextjs.yaml      frappe_docker override
      nginx.conf.template      nginx routing template
```

#### `next.config.ts` — Rewrites

```typescript
{ source: "/api/:path*",    destination: `${frappe}/api/:path*`    }
{ source: "/assets/:path*", destination: `${frappe}/assets/:path*` }
{ source: "/files/:path*",  destination: `${frappe}/files/:path*`  }
```

`/api/:path*` is intentionally broad (not just `/api/method/` and `/api/resource/`) so that middleware-redirected `/?cmd=web_logout` → `/api/?cmd=web_logout` is proxied to Frappe in dev mode.

#### `src/proxy.ts` — Middleware

```typescript
createFrappeAuthMiddleware({
  loginPath: '/login',
  publicPaths: [
    '/api/',    // Frappe API — Frappe handles its own auth
    '/health',  // Docker healthcheck — must be unauthenticated
  ],
  sessionTimeoutMs: 4000,
})
```

Matcher excludes `_next/static`, `_next/image`, favicon, and common image formats.

#### `app/health/route.ts`

```typescript
export function GET() { return Response.json({ status: 'ok' }) }
```

Lives at `/health` (not `/api/health`) because Frappe owns the `/api/` namespace. Used by Docker healthcheck and load balancers. **Do not delete.**

#### `app/[...frappe]/route.ts` — Dynamic Frappe Fallback

Catch-all route handler. Any path that does NOT match a Next.js page is proxied transparently to Frappe. This handles `/me`, `/update-password`, `/print`, `/list`, `/form`, etc. without maintaining a static list.

- Forwards all headers except hop-by-hop (`connection`, `transfer-encoding`, etc.)
- Sets `X-Frappe-Site-Name` from `FRAPPE_SITE_NAME` env var
- Strips `host` header (let Frappe use its own)
- Uses `redirect: 'manual'` — Frappe redirects pass through to the browser unchanged
- Supports `GET`, `POST`, `PUT`, `DELETE`
- 30-second timeout via `AbortSignal.timeout`

Next.js App Router routing priority guarantees static pages always win over this catch-all:
```
/login     → app/login/page.tsx      (your page, wins)
/products  → app/products/page.tsx   (your page, wins)
/me        → app/[...frappe]/route.ts → proxied to Frappe
/print/x   → app/[...frappe]/route.ts → proxied to Frappe
```

#### `app/login/page.tsx`

- `type="text"` input (not `type="email"`) — accepts both email and username (e.g. `Administrator`)
- Uses `frappeLogin()` which returns the full response including `home_page`
- Post-login redirect: uses `?next=` param if set, otherwise falls back to Frappe's `home_page`
- Client Component — login POST is intentionally browser-side so Frappe sets `sid` cookie directly in the browser

#### `dev.sh`

Starts Frappe bench and Next.js dev server together. Resolves `webserver_port` and `default_site` from `common_site_config.json` dynamically. Handles nvm node version resolution.

#### `prod.sh`

Builds Next.js, starts it in production mode, and launches `proxy.js`. Provides a production-identical environment locally without Docker.

#### `proxy.js` — Local Production Proxy

Zero-dependency Node.js HTTP proxy. Mirrors exactly what nginx does in production — same routing rules, same headers.

Routing:
```
/api/*      → Frappe
/app/*      → Frappe
/assets/*   → Frappe
/files/*    → Frappe
/private/*  → Frappe
/socket.io  → Frappe
/me         → Frappe (explicit prefix match)
/update-password → Frappe
/print/*, /list/*, /form/*, /tree/*, /report/*, /dashboard/* → Frappe
/?cmd=*     → Frappe  (root-path Frappe commands, e.g. web_logout)
/*          → Next.js (everything else)
```

The `/?cmd=` handling is critical — `isForFrappe` explicitly checks `url.startsWith('/?cmd=')` because `[...frappe]` requires ≥1 path segment and can't catch root-path commands.

---

### `bench deploy-nextjs`

Builds and deploys the Next.js project on a dedicated/VM server.

```bash
bench deploy-nextjs --app my_erp
bench deploy-nextjs --app my_erp --project-name dashboard --port 3001
bench deploy-nextjs --app my_erp --skip-nginx   # manage nginx manually
bench deploy-nextjs --app my_erp --skip-pm2     # use different process manager
```

#### What it does

1. **Build** — runs `pnpm build` (Next.js standalone output) with correct env vars injected
2. **Copy static assets** — copies `.next/static/` and `public/` into `.next/standalone/` (Next.js requirement)
3. **PM2** — starts `<app>-nextjs` process, auto-deletes old instance, saves process list, prints `pm2 startup` command for reboot persistence
4. **Nginx patch** — reads `bench/config/nginx.conf`, backs it up as `nginx.conf.pre-nextjs`, then surgically patches it:
   - Adds `upstream nextjs-server { server 127.0.0.1:<port>; }`
   - Adds explicit `location /api/`, `/app`, `/files/` blocks routing to Frappe
   - Replaces `location / { try_files ... @webserver }` with a proxy to Next.js
5. **nginx -t** validation before applying — auto-restores backup on failure
6. **nginx reload** via `systemctl reload nginx` (falls back to `service nginx reload`)

---

### Docker Deployment

#### Files involved

| File | Purpose |
|---|---|
| `docker/compose.nextjs.yaml` | frappe_docker override — adds `nextjs` service, extends `frontend` |
| `docker/nginx.conf.template` | Custom nginx routing template replacing frappe_docker's default |
| `<project>/Dockerfile` | Multi-stage Next.js standalone build |

#### Environment variables required in frappe_docker `.env`

```env
NEXTJS_BUILD_CONTEXT=/abs/path/to/apps/<app>/<project>
NEXTJS_DOCKER_DIR=/abs/path/to/apps/<app>/docker/
FRAPPE_SITE_NAME_HEADER=mysite.localhost
```

`NEXTJS_BUILD_CONTEXT` and `NEXTJS_DOCKER_DIR` must be absolute paths. Docker Compose resolves relative paths from the CWD of the first `-f` file, not from each override file's directory.

#### Full startup command

```bash
docker compose \
  -f compose.yaml \
  -f overrides/compose.mariadb.yaml \
  -f overrides/compose.redis.yaml \
  -f overrides/compose.noproxy.yaml \          ← required: publishes HTTP_PUBLISH_PORT
  -f /abs/path/to/docker/compose.nextjs.yaml \
  --env-file .env up -d --build
```

#### nginx routing (production)

```
/api/      → Frappe backend (gunicorn)
/app       → Frappe backend (Frappe desk)
/files/    → Frappe backend
/private/  → Frappe backend
/socket.io → Frappe websocket
/assets    → Static files (served from sites volume)
/          → Next.js (catch-all — SSR, ISR, /_next/static, login, custom pages)
```

Frappe paths not handled by nginx explicitly (e.g. `/me`, `/update-password`, `/print`) go to Next.js → `[...frappe]/route.ts` catch-all → proxied back to Frappe.

#### `compose.nextjs.yaml` services

**nextjs:**
- Build context: `${NEXTJS_BUILD_CONTEXT}` (absolute path from env)
- Env: `FRAPPE_INTERNAL_URL=http://backend:8000`, `FRAPPE_SITE_NAME=${FRAPPE_SITE_NAME_HEADER}`
- Healthcheck: `wget -qO- http://localhost:3000/health`
- `start_period: 60s` (Next.js standalone can take time on first boot)

**frontend (extended):**
- Mounts `${NEXTJS_DOCKER_DIR}nginx.conf.template` over the default frappe_docker template
- `depends_on: nextjs` — nginx starts only after Next.js is up

---

## Auth Architecture

### Two independent auth paths

```
1. User session (sid cookie)
   ─────────────────────────
   Browser ──cookie──→ Next.js middleware (verify against Frappe)
                     → Server Components (frappeGet/getList forwards sid)
                     → Client Components (frappeClientGet/Post auto-sends cookies)

2. Service account (API key)
   ─────────────────────────
   Next.js server ──token──→ Frappe
   One key for the whole app (Administrator or dedicated service user)
   Used only for system-level operations beyond user permissions
```

### User types in Frappe

| Type | Desk access | Use case |
|---|---|---|
| System User | Yes — full `/app` desk | Internal staff, admin |
| Website User | No desk access | Ecommerce customers, portal users |

User type is auto-computed from roles. If any assigned role has `desk_access = 1`, the user becomes a System User. To make a role that doesn't grant desk access, set `desk_access = 0` on the role.

### Session flow

```
1. Browser → GET /  →  Next.js middleware
2. No sid cookie    →  307 → /login?next=/&reason=no_session
3. POST /api/method/login  →  Frappe sets sid cookie in browser
4. frappeLogin() returns { home_page: '/me', ... }
5. Browser → GET /me  →  Next.js middleware
6. sid cookie valid   →  x-frappe-user injected into headers → page renders
7. Server Component: getList(...) forwards sid → Frappe checks user permissions
```

### Logout flow

```
1. Browser → GET /?cmd=web_logout
2. Next.js middleware: pathname='/', ?cmd= detected → 307 → /api/?cmd=web_logout
3. nginx: /api/ → Frappe backend
4. Frappe: processes web_logout → sets sid=Guest, clears all session cookies → 200
```

---

## Key Bugs Fixed

| Bug | Root cause | Fix |
|---|---|---|
| `session_invalid` after login | `verifySession` in middleware called Frappe without `X-Frappe-Site-Name` | Added site name header to all direct backend calls |
| `getList` 404 even when logged in | `buildSessionHeaders` forwarded `sid` but no `X-Frappe-Site-Name` | Added site name to server-side session headers |
| `/?cmd=web_logout` not clearing cookies | `[...frappe]` requires ≥1 path segment, root path goes to `page.tsx` | Middleware intercepts `/?cmd=` → redirects to `/api/?cmd=` |
| Docker relative path error | `../ecommerce` in compose.nextjs.yaml resolved from frappe_docker CWD | Switched to absolute `${NEXTJS_BUILD_CONTEXT}` env var |
| `@ts-expect-error` build failure | `duplex: 'half'` didn't need suppression in newer TypeScript | Removed the directive |
| `"No App"` login rejected | `result === "Logged In"` check was too strict | Removed check; `frappeClientPost` throws on 401 |
| Login rejects "Administrator" | `type="email"` triggers browser validation | Changed to `type="text"` |
| Home page 500 on missing API key | `getList` throwing uncaught `FrappeNotFoundError` | Wrapped in `try/catch`, shows helpful error message |
| Post-login redirect to `/` crashes | `frappeClientPost` discards `home_page` from login response | Added `frappeLogin()` returning full response body |
| `/api/health` returning Frappe response | Frappe owns `/api/` namespace | Moved health route to `/health` |
