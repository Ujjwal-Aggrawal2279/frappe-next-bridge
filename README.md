# frappe-next-bridge

**Add a production-ready Next.js App Router project to any Frappe app with one command.**

```bash
bench get-app https://github.com/Ujjwal-Aggrawal2279/frappe-next-bridge.git
bench add-nextjs
```

> This is the Frappe app (CLI tool). For the Next.js SDK, see
> [`@frappe-next/core`](https://github.com/Ujjwal-Aggrawal2279/frappe-next-sdk).

---

## What this does

`bench add-nextjs` scaffolds a full Next.js 15+ App Router project inside your Frappe app — SSR, session middleware, login page, ISR, TypeScript — all wired to Frappe out of the box.

```
bench add-nextjs

  Available apps:
  ───────────────
  1. my_erp
  2. expense_tracker

  Select app (number or name) [1]: 1

  ✓ my_erp/next_web/  scaffolded (12 files)
  ✓ my_erp/dev.sh     created
  ✓ my_erp/hooks.py   patched (allow_cors)
  ✓ pnpm install      done

  → cd apps/my_erp && bash dev.sh
```

## What gets generated

```
my_erp/
  next_web/
    src/
      proxy.ts              ← session middleware (Edge Runtime)
      app/
        layout.tsx          ← boot data + FrappeNextProvider
        page.tsx            ← SSR list from Frappe (ISR 60s)
        login/page.tsx      ← login with Frappe session
    next.config.ts          ← rewrites /api/* → Frappe
    .env.local              ← auto-filled with detected port + site
  dev.sh                    ← auto-detects bench port, starts Next.js
```

---

## Install

### Prerequisites

- Frappe bench (v15+)
- Node.js 18+ and [pnpm](https://pnpm.io)

### 1. Get the app

```bash
bench get-app https://github.com/Ujjwal-Aggrawal2279/frappe-next-bridge.git
```

### 2. Scaffold Next.js inside your Frappe app

```bash
# Interactive (recommended for first-timers)
bench add-nextjs

# Or specify directly
bench add-nextjs --app my_erp
bench add-nextjs --app my_erp --project-name dashboard
```

### 3. Start the dev server

```bash
cd apps/my_erp
bash dev.sh
```

Open [http://localhost:3000](http://localhost:3000).

---

## `bench add-nextjs` options

| Option | Default | Description |
|--------|---------|-------------|
| `--app` | interactive picker | Frappe app to scaffold inside |
| `--project-name` | `next_web` | Subfolder name for the Next.js project |
| `--pro` | off | Include `@frappe-next/pro` live hooks scaffold |

---

## How it works

1. **Auto-detects** your bench's `webserver_port` and `default_site` from `sites/common_site_config.json` — no manual config needed.
2. **Scaffolds** the Next.js project with all files pre-wired to your Frappe instance.
3. **Patches** your app's `hooks.py` with `allow_cors` for the Next.js dev server.
4. **Installs** npm dependencies via pnpm.

---

## Optional: install on a site

The CLI works without this. Only install if you want the CORS hooks and companion API endpoints active:

```bash
bench --site mysite.localhost install-app frappe_next_bridge
```

This enables:
- `GET /api/method/frappe_next_bridge.api.health`
- `GET /api/method/frappe_next_bridge.api.get_boot_info`

---

## License

MIT
