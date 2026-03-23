import json
import subprocess
import sys
from pathlib import Path

import click

from .boilerplates import (
    DEV_SH,
    DOCKERFILE,
    DOCKER_COMPOSE_YAML,
    DOCKER_NGINX_CONF,
    ENV_LOCAL,
    GITIGNORE,
    GLOBALS_CSS,
    LAYOUT_TSX,
    LOGIN_MODULE_CSS,
    LOGIN_PAGE_TSX,
    NEXT_CONFIG_TS,
    PACKAGE_JSON,
    PAGE_MODULE_CSS,
    PAGE_TSX,
    PROD_SH,
    PROXY_JS,
    PROXY_TS,
    TSCONFIG_JSON,
)


def _render(template: str, app: str, project: str, port: str, site: str) -> str:
    return (
        template
        .replace("{{app}}", app)
        .replace("{{project}}", project)
        .replace("{{port}}", port)
        .replace("{{site}}", site)
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    click.echo(f"  wrote  {path}")


def _read_bench_config(sites_dir: Path) -> tuple[str, str]:
    """Return (webserver_port, default_site) from common_site_config.json.

    When bench commands run, cwd is bench_root/sites/, so the config
    file is simply sites_dir/common_site_config.json.
    """
    cfg_path = sites_dir / "common_site_config.json"
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text())
            port = str(data.get("webserver_port", 8000))
            site = data.get("default_site", "site1.localhost")
            return port, site
        except Exception:
            pass
    return "8000", "site1.localhost"


class NextJSGenerator:
    """
    Scaffolds a Next.js App Router project inside a Frappe app directory.

    Called by `bench add-nextjs --app <frappe_app>`.

    Directory layout after generation:
        apps/
          <frappe_app>/
            <project>/          ← Next.js project (default: next_web)
              package.json
              tsconfig.json
              next.config.ts
              .env.local
              .gitignore
              src/
                proxy.ts
                app/
                  globals.css
                  layout.tsx
                  page.tsx
                  page.module.css
                  login/
                    page.tsx
                    login.module.css
            dev.sh               ← convenience launcher
    """

    def __init__(self, app: str, project: str = "next_web", include_pro: bool = False):
        self.app      = app
        self.project  = project
        self.include_pro = include_pro

        # Bench commands run with cwd = bench_root/sites/
        # apps/ is at ../apps/ relative to the sites/ directory.
        self.apps_dir   = Path("../apps")
        self.bench_root = self.apps_dir.parent.resolve()
        self.app_path   = self.apps_dir / app
        self.proj_path  = self.app_path / project

        self._validate()

        # common_site_config.json lives in the sites/ dir (= cwd when bench runs)
        self.port, self.site = _read_bench_config(Path("."))

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate(self) -> None:
        if not self.app_path.exists():
            click.echo(
                f"[frappe-next] ERROR: App '{self.app}' not found at {self.app_path}",
                err=True,
            )
            sys.exit(1)

        if self.proj_path.exists():
            if not click.confirm(
                f"[frappe-next] '{self.proj_path}' already exists. Overwrite?",
                default=False,
            ):
                click.echo("Aborted.")
                sys.exit(0)

    # ── Public entry point ───────────────────────────────────────────────────

    def generate(self) -> None:
        click.echo(
            f"\n[frappe-next] Scaffolding Next.js project '{self.project}' "
            f"in app '{self.app}'...\n"
        )

        self._scaffold_nextjs_project()
        self._write_dev_sh()
        self._write_docker_files()
        self._patch_hooks_py()
        self._install_dependencies()

        self._print_success()

    # ── Steps ────────────────────────────────────────────────────────────────

    def _scaffold_nextjs_project(self) -> None:
        def r(tpl: str) -> str:
            return _render(tpl, self.app, self.project, self.port, self.site)
        p = self.proj_path

        _write(p / "package.json",                 r(PACKAGE_JSON))
        _write(p / "tsconfig.json",                r(TSCONFIG_JSON))
        _write(p / "next.config.ts",               r(NEXT_CONFIG_TS))
        _write(p / ".env.local",                   r(ENV_LOCAL))
        _write(p / ".gitignore",                   r(GITIGNORE))
        _write(p / "src" / "proxy.ts",             r(PROXY_TS))
        _write(p / "src" / "app" / "globals.css",  r(GLOBALS_CSS))
        _write(p / "src" / "app" / "layout.tsx",   r(LAYOUT_TSX))
        _write(p / "src" / "app" / "page.tsx",     r(PAGE_TSX))
        _write(p / "src" / "app" / "page.module.css",          r(PAGE_MODULE_CSS))
        _write(p / "src" / "app" / "login" / "page.tsx",       r(LOGIN_PAGE_TSX))
        _write(p / "src" / "app" / "login" / "login.module.css", r(LOGIN_MODULE_CSS))

        # Empty public dir so Next.js doesn't warn
        (p / "public").mkdir(parents=True, exist_ok=True)

    def _write_dev_sh(self) -> None:
        dev_sh_path = self.app_path / "dev.sh"
        content = _render(DEV_SH, self.app, self.project, self.port, self.site)
        _write(dev_sh_path, content)
        dev_sh_path.chmod(0o755)
        click.echo(f"  wrote  {dev_sh_path}  (chmod +x)")

        prod_sh_path = self.app_path / "prod.sh"
        content = _render(PROD_SH, self.app, self.project, self.port, self.site)
        _write(prod_sh_path, content)
        prod_sh_path.chmod(0o755)
        click.echo(f"  wrote  {prod_sh_path}  (chmod +x)")

        proxy_js_path = self.app_path / "proxy.js"
        _write(proxy_js_path, PROXY_JS)
        click.echo(f"  wrote  {proxy_js_path}")

    def _write_docker_files(self) -> None:
        """Write Docker deployment files into apps/<app>/docker/."""
        def r(tpl: str) -> str:
            return _render(tpl, self.app, self.project, self.port, self.site)

        docker_dir = self.app_path / "docker"

        # Dockerfile lives inside the Next.js project (build context = project dir)
        _write(self.proj_path / "Dockerfile",           DOCKERFILE)

        # nginx template and compose override live in app-level docker/ dir
        _write(docker_dir / "nginx.conf.template",      DOCKER_NGINX_CONF)
        _write(docker_dir / "compose.nextjs.yaml",      r(DOCKER_COMPOSE_YAML))

    def _patch_hooks_py(self) -> None:
        """Add CORS allow_cors entry to the Frappe app's hooks.py."""
        hooks_py = self.app_path / self.app / "hooks.py"
        if not hooks_py.exists():
            click.echo(
                f"  skip   {hooks_py} not found — add allow_cors manually",
                err=True,
            )
            return

        text = hooks_py.read_text()

        cors_block = (
            '\n# ── CORS: allow Next.js dev server ──────────────────────────────────────\n'
            'allow_cors = [\n'
            '    "http://localhost:3000",\n'
            '    "http://127.0.0.1:3000",\n'
            ']\n'
        )

        if "allow_cors" in text:
            click.echo(f"  skip   {hooks_py} — allow_cors already present")
            return

        hooks_py.write_text(text + cors_block)
        click.echo(f"  patched {hooks_py} — added allow_cors")

    def _install_dependencies(self) -> None:
        """Run pnpm install inside the new project folder."""
        pnpm = self._find_pnpm()
        if not pnpm:
            click.echo(
                "\n[frappe-next] pnpm not found — run manually:\n"
                f"  cd {self.proj_path} && npm install -g pnpm && pnpm install",
                err=True,
            )
            return

        click.echo("\n[frappe-next] Installing dependencies with pnpm...")
        result = subprocess.run(
            [pnpm, "install"],
            cwd=self.proj_path,
        )
        if result.returncode != 0:
            click.echo(
                "[frappe-next] pnpm install failed — run it manually inside "
                f"{self.proj_path}",
                err=True,
            )

    def _find_pnpm(self) -> str | None:
        """Return path to pnpm executable, checking nvm directories too."""
        import shutil

        # 1. System PATH
        found = shutil.which("pnpm")
        if found:
            return found

        # 2. Common nvm locations
        home = Path.home()
        candidates = [
            home / ".nvm" / "versions" / "node",
        ]
        for base in candidates:
            if not base.exists():
                continue
            for node_dir in sorted(base.iterdir(), reverse=True):
                pnpm_bin = node_dir / "bin" / "pnpm"
                if pnpm_bin.exists():
                    return str(pnpm_bin)

        return None

    # ── Success message ───────────────────────────────────────────────────────

    def _print_success(self) -> None:
        click.echo(f"""
╔══════════════════════════════════════════════════════╗
║   frappe-next: scaffold complete                     ║
╚══════════════════════════════════════════════════════╝

  App     : {self.app}
  Project : {self.proj_path}
  Frappe  : http://127.0.0.1:{self.port}  (site: {self.site})

  Next steps:
  ──────────────────────────────────────────────────────
  1. Verify your Frappe API key in:
       {self.proj_path}/.env.local

  2. Dev server (hot reload):
       cd apps/{self.app} && bash dev.sh
       → http://localhost:3000

     Production preview (nginx-identical proxy):
       cd apps/{self.app} && bash prod.sh
       → http://localhost:8080

  Docs: https://github.com/frappe-next/frappe-next-bridge
""")
