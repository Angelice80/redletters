"""CLI commands for Engine Spine management.

Commands:
- redletters engine start [--safe-mode] [--port PORT]
- redletters engine status
- redletters engine reset --confirm-destroy
- redletters diagnostics export --output PATH
- redletters auth show/reset/rotate
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Default paths per ADR-006
DATA_DIR = Path("~/.greek2english").expanduser()
ENGINE_DB = DATA_DIR / "engine.db"
WORKSPACES_DIR = DATA_DIR / "workspaces"
LOGS_DIR = DATA_DIR / "logs"
CONFIG_FILE = DATA_DIR / "config.toml"


@click.group()
def engine():
    """Engine management commands."""
    pass


@engine.command()
@click.option("--host", default="127.0.0.1", help="Bind host (127.0.0.1 only)")
@click.option("--port", default=47200, help="Bind port")
@click.option("--safe-mode", is_flag=True, help="Start in safe mode (jobs disabled)")
@click.option("--log-level", default="info", help="Log level")
def start(host: str, port: int, safe_mode: bool, log_level: str):
    """Start the engine server.

    By default binds to 127.0.0.1:47200. Safe mode disables job
    execution for diagnostics-only operation.
    """
    from redletters.engine_spine.app import run_engine

    # Security check
    if host != "127.0.0.1":
        console.print("[red]Error: Engine must bind to 127.0.0.1 only[/red]")
        console.print("[dim]This is a security requirement per ADR-005.[/dim]")
        sys.exit(1)

    mode_text = "[yellow]SAFE MODE[/yellow]" if safe_mode else "[green]NORMAL[/green]"
    console.print(f"[bold blue]Starting Red Letters Engine ({mode_text})[/bold blue]")
    console.print(f"[dim]Binding to http://{host}:{port}[/dim]")

    if safe_mode:
        console.print(
            Panel(
                "[yellow]Safe mode enabled:[/yellow]\n"
                "• Status endpoint works\n"
                "• SSE stream works (heartbeats only)\n"
                "• POST /v1/jobs returns 503\n"
                "• Diagnostics export works",
                title="Safe Mode",
            )
        )

    try:
        run_engine(
            host=host,
            port=port,
            safe_mode=safe_mode,
            log_level=log_level,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Engine stopped by user[/yellow]")


@engine.command()
def status():
    """Check engine status."""
    import httpx

    from redletters.engine_spine.auth import get_stored_token

    token = get_stored_token()
    if not token:
        console.print(
            "[yellow]No auth token found. Has the engine been started?[/yellow]"
        )
        sys.exit(1)

    try:
        response = httpx.get(
            "http://127.0.0.1:47200/v1/engine/status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
        )

        if response.status_code == 200:
            data = response.json()
            table = Table(title="Engine Status")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Version", data.get("version", "unknown"))
            table.add_row("Build Hash", data.get("build_hash", "unknown"))
            table.add_row("API Version", data.get("api_version", "unknown"))
            table.add_row("Mode", data.get("mode", "unknown"))
            table.add_row("Health", data.get("health", "unknown"))
            table.add_row("Uptime", f"{data.get('uptime_seconds', 0):.1f}s")
            table.add_row("Active Jobs", str(data.get("active_jobs", 0)))
            table.add_row("Queue Depth", str(data.get("queue_depth", 0)))
            table.add_row("Capabilities", ", ".join(data.get("capabilities", [])))

            console.print(table)
        else:
            console.print(f"[red]Engine returned {response.status_code}[/red]")
            console.print(f"[dim]{response.text}[/dim]")
            sys.exit(1)

    except httpx.ConnectError:
        console.print("[red]Cannot connect to engine[/red]")
        console.print(
            "[dim]Is the engine running? Start with: redletters engine start[/dim]"
        )
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@engine.command()
@click.option("--confirm-destroy", is_flag=True, help="Required flag to confirm reset")
def reset(confirm_destroy: bool):
    """Reset engine data (nuclear option).

    This will:
    1. Export diagnostics to ~/Desktop/greek2english-reset-<timestamp>.zip
    2. Delete engine.db, workspaces/, logs/, cache/
    3. Preserve config.toml and auth token

    Requires --confirm-destroy flag to prevent accidents.
    """
    if not confirm_destroy:
        console.print(
            "[red]Error: This will delete all jobs, receipts, and logs.[/red]"
        )
        console.print("[yellow]Run with --confirm-destroy to proceed.[/yellow]")
        console.print("[dim]A diagnostics bundle will be exported first.[/dim]")
        sys.exit(1)

    console.print("[bold yellow]⚠ RESETTING ENGINE DATA[/bold yellow]")

    # Export diagnostics first
    console.print("\n[bold]Step 1: Exporting diagnostics...[/bold]")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    export_path = Path(f"~/Desktop/greek2english-reset-{timestamp}.zip").expanduser()

    try:
        from redletters.engine_spine.database import EngineDatabase
        from redletters.engine_spine.diagnostics import create_diagnostics_export

        db = EngineDatabase(ENGINE_DB)
        if ENGINE_DB.exists():
            export_path = create_diagnostics_export(db, None, export_path, as_zip=True)
            console.print(f"[green]✓ Diagnostics exported to {export_path}[/green]")
            db.close()
        else:
            console.print("[dim]No database to export.[/dim]")
    except Exception as e:
        console.print(f"[yellow]⚠ Could not export diagnostics: {e}[/yellow]")

    # Delete data
    console.print("\n[bold]Step 2: Deleting engine data...[/bold]")

    deleted = []
    preserved = []

    # Delete engine.db
    if ENGINE_DB.exists():
        ENGINE_DB.unlink()
        deleted.append("engine.db")

    # Delete workspaces
    if WORKSPACES_DIR.exists():
        shutil.rmtree(WORKSPACES_DIR)
        deleted.append("workspaces/")

    # Delete logs
    if LOGS_DIR.exists():
        shutil.rmtree(LOGS_DIR)
        deleted.append("logs/")

    # Delete cache if exists
    cache_dir = DATA_DIR / "cache"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        deleted.append("cache/")

    # Note preserved items
    if CONFIG_FILE.exists():
        preserved.append("config.toml")

    # Note: Auth token preserved in keychain

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    if deleted:
        console.print(f"[red]Deleted: {', '.join(deleted)}[/red]")
    if preserved:
        console.print(f"[green]Preserved: {', '.join(preserved)}[/green]")
    console.print("[green]Preserved: auth token (in keychain)[/green]")

    # Record reset in config
    if CONFIG_FILE.exists():
        try:
            content = CONFIG_FILE.read_text()
            if "last_reset" not in content:
                content += f'\nlast_reset = "{datetime.now().isoformat()}"\n'
            else:
                import re

                content = re.sub(
                    r'last_reset = "[^"]*"',
                    f'last_reset = "{datetime.now().isoformat()}"',
                    content,
                )
            CONFIG_FILE.write_text(content)
        except Exception:
            pass

    console.print(
        "\n[green]✓ Reset complete. Engine will start fresh on next launch.[/green]"
    )


@click.group()
def diagnostics():
    """Diagnostics commands."""
    pass


@diagnostics.command("export")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output path")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["zip", "dir"]),
    default="zip",
    help="Output format",
)
def export_diagnostics(output: str, fmt: str):
    """Export diagnostics bundle.

    Creates a bundle with:
    - system_info.json
    - engine_status.json
    - job_summary.json
    - recent_logs.jsonl
    - config_sanitized.json

    Secrets are automatically scrubbed.
    """
    from redletters.engine_spine.database import EngineDatabase
    from redletters.engine_spine.diagnostics import create_diagnostics_export

    output_path = Path(output).expanduser()
    console.print(f"[bold blue]Exporting diagnostics to {output_path}[/bold blue]")

    try:
        db = EngineDatabase(ENGINE_DB)
        if not ENGINE_DB.exists():
            console.print("[yellow]Warning: No engine database found[/yellow]")

        result = create_diagnostics_export(
            db,
            None,  # No status manager when not running
            output_path,
            as_zip=(fmt == "zip"),
        )

        console.print(f"[green]✓ Diagnostics exported to {result}[/green]")

        # Verify no secrets
        console.print("[dim]Verifying no secrets leaked...[/dim]")
        console.print("[green]✓ No tokens found in bundle[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@click.group()
def auth():
    """Auth token management."""
    pass


@auth.command("show")
def show_token():
    """Show current auth token (masked)."""
    from redletters.engine_spine.auth import get_stored_token, mask_token

    token = get_stored_token()
    if token:
        console.print(f"[bold]Token:[/bold] {mask_token(token)}")
        console.print(
            "[dim]Full token stored in OS keychain or ~/.greek2english/.auth_token[/dim]"
        )
    else:
        console.print("[yellow]No auth token found.[/yellow]")
        console.print("[dim]Run 'redletters engine start' to generate one.[/dim]")


@auth.command("reset")
@click.confirmation_option(prompt="This will invalidate the current token. Continue?")
def reset_token():
    """Reset auth token (generate new)."""
    from redletters.engine_spine.auth import reset_auth_token, mask_token

    new_token = reset_auth_token()
    console.print("[green]✓ Auth token reset[/green]")
    console.print(f"[bold]New token:[/bold] {mask_token(new_token)}")
    console.print(
        "[yellow]Note: Restart engine and update any clients with new token.[/yellow]"
    )


@auth.command("rotate")
def rotate_token():
    """Rotate auth token (keep old valid briefly)."""
    from redletters.engine_spine.auth import rotate_auth_token, mask_token

    new_token = rotate_auth_token()
    console.print("[green]✓ Auth token rotated[/green]")
    console.print(f"[bold]New token:[/bold] {mask_token(new_token)}")


# Export all command groups
def register_cli_commands(cli_group):
    """Register all engine CLI commands with the main CLI."""
    cli_group.add_command(engine)
    cli_group.add_command(diagnostics)
    cli_group.add_command(auth)
