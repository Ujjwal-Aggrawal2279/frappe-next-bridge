import sys
from pathlib import Path

import click

from .nextjs_generator import NextJSGenerator

# Apps that are infrastructure — skip them from the selection menu
_SKIP_APPS = {"frappe", "frappe_types", "doppio", "frappe_next_bridge", "erpnext"}


def _get_bench_apps() -> list[str]:
    """Return custom apps present in this bench (reads ../apps/ directory)."""
    apps_dir = Path("../apps")
    if not apps_dir.exists():
        return []
    return sorted(
        d.name
        for d in apps_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name not in _SKIP_APPS
    )


def _pick_app_interactively() -> str:
    """Show a numbered menu of available apps and return the chosen one."""
    apps = _get_bench_apps()

    if not apps:
        click.echo(
            "[frappe-next] No custom apps found in apps/.\n"
            "Create one first:  bench new-app my_erp",
            err=True,
        )
        sys.exit(1)

    click.echo("")
    click.echo("  Available apps:")
    click.echo("  ───────────────")
    for i, name in enumerate(apps, start=1):
        click.echo(f"  {i}. {name}")
    click.echo("")

    while True:
        raw = click.prompt("  Select app (number or name)", default="1")
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(apps):
                return apps[idx]
            click.echo(f"  Please enter a number between 1 and {len(apps)}")
        elif raw in apps:
            return raw
        else:
            click.echo(f"  '{raw}' not found. Type the name exactly or pick a number.")


@click.command("add-nextjs")
@click.option(
    "--app",
    default=None,
    help="Frappe app to scaffold Next.js inside (skips interactive menu)",
)
@click.option(
    "--project-name",
    default="next_web",
    show_default=True,
    help="Name of the Next.js project folder inside the app",
)
@click.option(
    "--pro",
    is_flag=True,
    default=False,
    help="Include @frappe-next/pro live-hooks scaffold (Socket.IO realtime)",
)
def add_nextjs(app: str | None, project_name: str, pro: bool) -> None:
    """Scaffold a production-ready Next.js App Router project inside a Frappe app.

    \b
    Run without arguments for an interactive app picker:
      bench add-nextjs

    Or specify directly:
      bench add-nextjs --app my_erp
      bench add-nextjs --app my_erp --project-name dashboard --pro
    """
    if not app:
        app = _pick_app_interactively()

    generator = NextJSGenerator(app, project_name, pro)
    generator.generate()


commands = [add_nextjs]
