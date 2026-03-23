"""
bench deploy-nextjs — dedicated server deployment

Builds the Next.js standalone bundle, starts it under PM2,
and patches the bench-managed nginx config to route Next.js
paths alongside Frappe — all in one command.

Works for:
  - Ubuntu/Debian servers with bench install
  - Any server where `bench setup nginx` was already run

Usage:
  bench deploy-nextjs --app my_erp
  bench deploy-nextjs --app my_erp --project-name dashboard --port 3001
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import click

# Paths that belong to Frappe — anything else is routed to Next.js
_FRAPPE_PATHS = ["/api/", "/app", "/files/", "/private/", "/assets", "/socket.io"]


# ─── Nginx config patcher ────────────────────────────────────────────────────

def _find_block_end(text: str, start: int) -> int:
    """Return the index just AFTER the closing '}' of the block that opens at `start`."""
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("Unbalanced braces — nginx.conf may be malformed")


def patch_nginx_for_nextjs(nginx_conf: str, nextjs_port: int) -> str:
    """
    Patch a bench-generated nginx.conf to route Next.js alongside Frappe.

    Changes:
      1. Add `upstream nextjs-server` after the last existing upstream block.
      2. Add explicit /api/, /app, /files/ locations inside each server block
         so these go to Frappe even though the default location now goes to Next.js.
      3. Replace the generic `location / { try_files … @webserver; }` block
         with a proxy to Next.js.
    """
    # ── 1. Add nextjs upstream ────────────────────────────────────────────────
    nextjs_upstream = (
        f"\nupstream nextjs-server {{\n"
        f"\tserver 127.0.0.1:{nextjs_port} fail_timeout=0;\n"
        f"}}\n"
    )

    # Find positions of all upstream blocks so we can insert after the last one
    upstream_iter = list(re.finditer(r"upstream\s+\S+\s*\{", nginx_conf))
    if not upstream_iter:
        click.echo(
            "[frappe-next] WARNING: No upstream blocks found in nginx.conf — "
            "skipping Next.js upstream injection.",
            err=True,
        )
    else:
        last_upstream_start = upstream_iter[-1].start()
        last_upstream_end = _find_block_end(nginx_conf, last_upstream_start)

        # Only inject if nextjs-server isn't already there
        if "nextjs-server" not in nginx_conf:
            nginx_conf = (
                nginx_conf[:last_upstream_end]
                + nextjs_upstream
                + nginx_conf[last_upstream_end:]
            )

    # ── 2. Extract bench_name and site_name from existing config ─────────────
    bench_name_match = re.search(r"upstream\s+(\S+)-frappe\s*\{", nginx_conf)
    bench_name = bench_name_match.group(1) if bench_name_match else "frappe-bench"

    site_name_match = re.search(r"try_files\s+/([^/\s]+)/public", nginx_conf)
    site_name = site_name_match.group(1) if site_name_match else "$host"

    timeout_match = re.search(r"proxy_read_timeout\s+(\d+)", nginx_conf)
    http_timeout = timeout_match.group(1) if timeout_match else "120"

    # ── 3. Build replacement locations ───────────────────────────────────────
    frappe_location_block = f"""\
\t# ── Frappe REST API ──────────────────────────────────────────────────────────
\tlocation /api/ {{
\t\tproxy_http_version 1.1;
\t\tproxy_set_header X-Forwarded-For   $remote_addr;
\t\tproxy_set_header X-Forwarded-Proto $scheme;
\t\tproxy_set_header X-Frappe-Site-Name {site_name};
\t\tproxy_set_header Host              $host;
\t\tproxy_set_header X-Use-X-Accel-Redirect True;
\t\tproxy_read_timeout {http_timeout};
\t\tproxy_redirect off;
\t\tproxy_pass http://{bench_name}-frappe;
\t}}

\t# ── Frappe Desk ───────────────────────────────────────────────────────────────
\tlocation /app {{
\t\tproxy_http_version 1.1;
\t\tproxy_set_header X-Forwarded-For   $remote_addr;
\t\tproxy_set_header X-Forwarded-Proto $scheme;
\t\tproxy_set_header X-Frappe-Site-Name {site_name};
\t\tproxy_set_header Host              $host;
\t\tproxy_set_header X-Use-X-Accel-Redirect True;
\t\tproxy_read_timeout {http_timeout};
\t\tproxy_redirect off;
\t\tproxy_pass http://{bench_name}-frappe;
\t}}

\t# ── Frappe files ──────────────────────────────────────────────────────────────
\tlocation /files/ {{
\t\tproxy_http_version 1.1;
\t\tproxy_set_header X-Forwarded-For   $remote_addr;
\t\tproxy_set_header X-Forwarded-Proto $scheme;
\t\tproxy_set_header X-Frappe-Site-Name {site_name};
\t\tproxy_set_header Host              $host;
\t\tproxy_set_header X-Use-X-Accel-Redirect True;
\t\tproxy_read_timeout {http_timeout};
\t\tproxy_redirect off;
\t\tproxy_pass http://{bench_name}-frappe;
\t}}

\t# ── Next.js — all other routes (SSR, ISR, /_next/*, custom pages) ────────────
\tlocation / {{
\t\tproxy_http_version 1.1;
\t\tproxy_set_header X-Forwarded-For   $remote_addr;
\t\tproxy_set_header X-Forwarded-Proto $scheme;
\t\tproxy_set_header Host              $host;
\t\tproxy_set_header Upgrade           $http_upgrade;
\t\tproxy_set_header Connection        "upgrade";
\t\tproxy_read_timeout {http_timeout};
\t\tproxy_redirect off;
\t\tproxy_pass http://nextjs-server;
\t}}
"""

    # ── 4. Find and replace the generic `location / { ... }` block ───────────
    # Search for the exact pattern produced by the bench nginx template
    loc_marker = "\n\tlocation / {"
    loc_start = nginx_conf.find(loc_marker)
    if loc_start == -1:
        # fallback: try without leading tab
        loc_marker = "\n\tlocation / {\n"
        loc_start = nginx_conf.find(loc_marker)

    if loc_start == -1:
        click.echo(
            "[frappe-next] WARNING: Could not find 'location / {' in nginx.conf — "
            "manual nginx edit may be needed.",
            err=True,
        )
        return nginx_conf

    brace_start = nginx_conf.index("{", loc_start + len("\n\tlocation / "))
    loc_end = _find_block_end(nginx_conf, brace_start)

    nginx_conf = nginx_conf[:loc_start] + "\n" + frappe_location_block + nginx_conf[loc_end:]
    return nginx_conf


# ─── PM2 helper ──────────────────────────────────────────────────────────────

def _ensure_pm2() -> str:
    """Return pm2 path, auto-installing via npm if not found."""
    found = shutil.which("pm2")
    if found:
        return found

    # Try nvm-managed node locations
    home = Path.home()
    for node_dir in sorted((home / ".nvm" / "versions" / "node").glob("v*"), reverse=True):
        candidate = node_dir / "bin" / "pm2"
        if candidate.exists():
            return str(candidate)

    click.echo("[frappe-next] pm2 not found — installing globally via npm...")
    subprocess.run(["npm", "install", "-g", "pm2"], check=True)

    found = shutil.which("pm2")
    if not found:
        click.echo(
            "[frappe-next] ERROR: pm2 installation failed. "
            "Install manually: npm install -g pm2",
            err=True,
        )
        sys.exit(1)
    return found


def _find_pnpm() -> str | None:
    found = shutil.which("pnpm")
    if found:
        return found
    home = Path.home()
    for node_dir in sorted((home / ".nvm" / "versions" / "node").glob("v*"), reverse=True):
        candidate = node_dir / "bin" / "pnpm"
        if candidate.exists():
            return str(candidate)
    return None


def _read_bench_config(bench_root: Path) -> tuple[str, str]:
    cfg = bench_root / "sites" / "common_site_config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text())
            return str(data.get("webserver_port", 8000)), data.get("default_site", "site1.localhost")
        except Exception:
            pass
    return "8000", "site1.localhost"


# ─── Command ─────────────────────────────────────────────────────────────────

@click.command("deploy-nextjs")
@click.option("--app",          required=True, help="Frappe app that contains the Next.js project")
@click.option("--project-name", default="next_web", show_default=True,
              help="Name of the Next.js project folder inside the app")
@click.option("--port",         default=3000, show_default=True, type=int,
              help="Port for the Next.js production server")
@click.option("--skip-nginx",   is_flag=True, default=False,
              help="Skip nginx config patching (useful if you manage nginx manually)")
@click.option("--skip-pm2",     is_flag=True, default=False,
              help="Skip PM2 setup (useful if you use a different process manager)")
def deploy_nextjs(app: str, project_name: str, port: int, skip_nginx: bool, skip_pm2: bool) -> None:
    """Build and deploy a Next.js project on a dedicated server.

    \b
    What this does:
      1. Builds Next.js standalone (pnpm build)
      2. Starts the production server under PM2 (auto-restart on crash/reboot)
      3. Patches bench nginx to route your custom pages to Next.js
         while Frappe keeps /api/, /app, /files/, etc.
      4. Reloads nginx

    \b
    Run from bench root or sites/ directory:
      bench deploy-nextjs --app my_erp
      bench deploy-nextjs --app my_erp --project-name dashboard --port 3001
    """
    # Bench commands run with cwd = bench_root/sites/
    bench_root = Path("../").resolve()
    apps_dir   = bench_root / "apps"
    app_path   = apps_dir / app
    proj_path  = app_path / project_name

    if not app_path.exists():
        click.echo(f"[frappe-next] ERROR: App '{app}' not found at {app_path}", err=True)
        sys.exit(1)

    if not proj_path.exists():
        click.echo(
            f"[frappe-next] ERROR: Project '{project_name}' not found at {proj_path}\n"
            "  Run 'bench add-nextjs' first.",
            err=True,
        )
        sys.exit(1)

    frappe_port, frappe_site = _read_bench_config(bench_root)

    click.echo(f"\n[frappe-next] Deploying {app}/{project_name} on port {port}...\n")

    # ── Step 1: Build ─────────────────────────────────────────────────────────
    pnpm = _find_pnpm()
    if not pnpm:
        click.echo("[frappe-next] ERROR: pnpm not found. Install Node ≥20 and pnpm.", err=True)
        sys.exit(1)

    click.echo("[frappe-next] Building Next.js standalone bundle...")
    env_vars = {
        "FRAPPE_INTERNAL_URL": f"http://127.0.0.1:{frappe_port}",
        "FRAPPE_URL":          f"http://127.0.0.1:{frappe_port}",
        "FRAPPE_SITE_NAME":    frappe_site,
        "NEXT_PUBLIC_FRAPPE_SITE": frappe_site,
        "NODE_ENV": "production",
    }
    import os
    build_env = {**os.environ, **env_vars}

    result = subprocess.run([pnpm, "build"], cwd=proj_path, env=build_env)
    if result.returncode != 0:
        click.echo("[frappe-next] ERROR: Build failed.", err=True)
        sys.exit(1)

    # Copy static assets into standalone (Next.js requirement)
    standalone = proj_path / ".next" / "standalone"
    static_src  = proj_path / ".next" / "static"
    public_src  = proj_path / "public"

    click.echo("[frappe-next] Copying static assets into standalone...")
    if static_src.exists():
        shutil.copytree(static_src, standalone / ".next" / "static", dirs_exist_ok=True)
    if public_src.exists():
        shutil.copytree(public_src, standalone / "public", dirs_exist_ok=True)

    click.echo("[frappe-next] Build complete.\n")

    # ── Step 2: PM2 ──────────────────────────────────────────────────────────
    if not skip_pm2:
        pm2 = _ensure_pm2()
        server_js = standalone / "server.js"
        pm2_name  = f"{app}-nextjs"

        click.echo(f"[frappe-next] Starting '{pm2_name}' under PM2 on port {port}...")

        # Stop any existing instance gracefully
        subprocess.run([pm2, "delete", pm2_name], capture_output=True)

        pm2_env = {
            **os.environ,
            **env_vars,
            "PORT":     str(port),
            "HOSTNAME": "127.0.0.1",
        }
        result = subprocess.run(
            [pm2, "start", str(server_js), "--name", pm2_name, "--interpreter", "node"],
            env=pm2_env,
        )
        if result.returncode != 0:
            click.echo("[frappe-next] ERROR: PM2 start failed.", err=True)
            sys.exit(1)

        # Persist PM2 process list for auto-restart on reboot
        subprocess.run([pm2, "save"])

        # Suggest PM2 startup — requires sudo, so we just print the command
        startup_result = subprocess.run(
            [pm2, "startup"], capture_output=True, text=True
        )
        startup_cmd = next(
            (line.strip() for line in startup_result.stdout.splitlines() if line.startswith("sudo")),
            None,
        )
        if startup_cmd:
            click.echo(f"\n[frappe-next] To enable auto-restart on reboot, run:\n  {startup_cmd}\n")

        click.echo(f"[frappe-next] PM2: '{pm2_name}' is running on port {port}.\n")

    # ── Step 3: Patch bench nginx ─────────────────────────────────────────────
    if not skip_nginx:
        nginx_conf_path = bench_root / "config" / "nginx.conf"

        if not nginx_conf_path.exists():
            click.echo(
                "[frappe-next] nginx.conf not found at config/nginx.conf.\n"
                "  Run 'bench setup nginx' first, then re-run this command.",
                err=True,
            )
        else:
            click.echo("[frappe-next] Patching bench nginx config for Next.js routing...")

            original = nginx_conf_path.read_text()

            # Back up the original before modifying
            backup_path = nginx_conf_path.with_suffix(".conf.pre-nextjs")
            if not backup_path.exists():
                backup_path.write_text(original)
                click.echo(f"  backup → {backup_path}")

            patched = patch_nginx_for_nextjs(original, nextjs_port=port)
            nginx_conf_path.write_text(patched)
            click.echo(f"  wrote  → {nginx_conf_path}")

            # Test and reload nginx
            test = subprocess.run(["sudo", "nginx", "-t"], capture_output=True, text=True)
            if test.returncode != 0:
                click.echo(
                    f"[frappe-next] ERROR: nginx config test failed:\n{test.stderr}\n"
                    f"  Restoring backup from {backup_path}",
                    err=True,
                )
                nginx_conf_path.write_text(original)
                sys.exit(1)

            reload = subprocess.run(["sudo", "systemctl", "reload", "nginx"])
            if reload.returncode != 0:
                # Fallback for systems not using systemd
                subprocess.run(["sudo", "service", "nginx", "reload"])

            click.echo("[frappe-next] nginx reloaded.\n")

    # ── Done ──────────────────────────────────────────────────────────────────
    click.echo(f"""
╔══════════════════════════════════════════════════════╗
║   frappe-next: deployment complete                   ║
╚══════════════════════════════════════════════════════╝

  App       : {app}
  Project   : {proj_path}
  Next.js   : http://127.0.0.1:{port}  (PM2 managed)
  Routing   : nginx → Next.js for custom routes
              nginx → Frappe for /api/ /app /files/ etc.

  Logs:
    pm2 logs {app}-nextjs        # Next.js app logs
    sudo nginx -t                # verify nginx config
    sudo journalctl -u nginx     # nginx logs
""")
