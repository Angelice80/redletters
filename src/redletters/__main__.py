"""CLI entry point for Red Letters Source Reader."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from redletters.config import Settings
from redletters.db.connection import get_connection, init_db
from redletters.ingest.loader import load_demo_data
from redletters.engine.query import parse_reference, get_tokens_for_reference
from redletters.engine.generator import CandidateGenerator
from redletters.engine.ranker import RenderingRanker

if TYPE_CHECKING:
    from redletters.ingest.loader import LoadReport

console = Console()
settings = Settings()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Red Letters Source Reader - Multi-reading Greek NT tool."""
    pass


@cli.command()
def init():
    """Initialize database with demo data."""
    console.print("[bold blue]Initializing Red Letters database...[/bold blue]")

    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection(db_path)
    init_db(conn)
    load_demo_data(conn)
    conn.close()

    console.print(f"[green]✓ Database initialized at {db_path}[/green]")


@cli.command()
@click.argument("reference")
@click.option("--style", "-s", default=None, help="Filter by rendering style")
@click.option("--output", "-o", type=click.Path(), help="Output JSON to file")
def query(reference: str, style: str | None, output: str | None):
    """Query a scripture reference for candidate renderings.

    Example: redletters query "Matthew 3:2"
    """
    conn = get_connection(settings.db_path)

    try:
        ref = parse_reference(reference)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    tokens = get_tokens_for_reference(conn, ref)

    if not tokens:
        console.print(f"[yellow]No tokens found for {reference}[/yellow]")
        console.print(
            "[dim]Have you run 'redletters init' to load the demo data?[/dim]"
        )
        sys.exit(1)

    generator = CandidateGenerator(conn)
    ranker = RenderingRanker(conn)

    candidates = generator.generate_all(tokens)
    ranked = ranker.rank(candidates, tokens)

    if style:
        ranked = [r for r in ranked if r["style"] == style]

    # Build output
    greek_text = " ".join(t["surface"] for t in tokens)
    result = {
        "reference": reference,
        "parsed_ref": {"book": ref.book, "chapter": ref.chapter, "verse": ref.verse},
        "greek_text": greek_text,
        "token_count": len(tokens),
        "renderings": ranked,
    }

    if output:
        Path(output).write_text(json.dumps(result, indent=2, ensure_ascii=False))
        console.print(f"[green]✓ Output written to {output}[/green]")
    else:
        # Pretty print to console
        console.print(Panel(f"[bold]{reference}[/bold]\n{greek_text}", title="Query"))

        for r in ranked:
            style_color = {
                "ultra-literal": "cyan",
                "natural": "green",
                "meaning-first": "yellow",
                "jewish-context": "magenta",
            }.get(r["style"], "white")

            console.print(
                f"\n[bold {style_color}]{r['style'].upper()}[/bold {style_color}] (score: {r['score']:.2f})"
            )
            console.print(f"  {r['text']}")

            if r.get("receipts"):
                console.print("  [dim]Receipts:[/dim]")
                for receipt in r["receipts"][:3]:  # Show first 3
                    console.print(
                        f"    • {receipt['lemma']}: {receipt['chosen_gloss']} ({receipt['rationale'][:60]}...)"
                    )

    conn.close()


@cli.command("list-spans")
def list_spans():
    """List all red-letter speech spans in the database."""
    conn = get_connection(settings.db_path)

    cursor = conn.execute("""
        SELECT book, chapter, verse_start, verse_end, speaker, confidence, source
        FROM speech_spans
        ORDER BY book, chapter, verse_start
    """)

    table = Table(title="Red Letter Spans")
    table.add_column("Reference", style="cyan")
    table.add_column("Speaker", style="green")
    table.add_column("Confidence", justify="right")
    table.add_column("Source", style="dim")

    for row in cursor:
        ref = f"{row[0]} {row[1]}:{row[2]}"
        if row[3] != row[2]:
            ref += f"-{row[3]}"
        table.add_row(ref, row[4], f"{row[5]:.0%}", row[6] or "")

    console.print(table)
    conn.close()


@cli.command()
@click.option("--host", default="127.0.0.1", help="Bind host")
@click.option("--port", default=8000, help="Bind port")
def serve(host: str, port: int):
    """Start the API server."""
    import uvicorn

    console.print(
        f"[bold blue]Starting Red Letters API at http://{host}:{port}[/bold blue]"
    )
    uvicorn.run("redletters.api.main:app", host=host, port=port, reload=True)


# Data management commands (Phase 2)
@cli.group()
def data():
    """Manage external data sources (Phase 2)."""
    pass


@data.command("fetch")
@click.argument("source", required=False)
@click.option("--force", is_flag=True, help="Re-download even if cached")
def data_fetch(source: str | None, force: bool):
    """Fetch external data sources.

    Downloads data at runtime (not bundled in repo) to respect licenses.

    Examples:
        redletters data fetch              # Fetch all sources
        redletters data fetch morphgnt-sblgnt  # Fetch specific source
    """
    from redletters.ingest.fetch import fetch_source, fetch_all, SOURCES

    if source:
        if source not in SOURCES:
            console.print(f"[red]Unknown source: {source}[/red]")
            console.print(f"[dim]Available: {', '.join(SOURCES.keys())}[/dim]")
            sys.exit(1)

        console.print(f"[bold blue]Fetching {source}...[/bold blue]")
        result = fetch_source(source, force=force)
        if result.get("already_cached"):
            console.print(
                "[yellow]Already cached (use --force to re-download)[/yellow]"
            )
        console.print(f"[green]✓ {result['name']} ready[/green]")
    else:
        console.print("[bold blue]Fetching all data sources...[/bold blue]")
        console.print(
            "[dim]This downloads data at runtime to respect licenses.[/dim]\n"
        )
        results = fetch_all(force=force)
        for r in results:
            if "error" in r:
                console.print(f"[red]✗ {r['name']}: {r['error']}[/red]")
            else:
                console.print(f"[green]✓ {r['name']} ({r['license']})[/green]")


@data.command("list")
def data_list():
    """List available data sources and their status."""
    from redletters.ingest.fetch import SOURCES, get_source_path

    table = Table(title="Data Sources")
    table.add_column("Key", style="cyan")
    table.add_column("Name")
    table.add_column("License", style="yellow")
    table.add_column("Status")

    for key, spec in SOURCES.items():
        path = get_source_path(key)
        status = "[green]✓ Fetched[/green]" if path else "[dim]Not fetched[/dim]"
        table.add_row(key, spec.name, spec.license, status)

    console.print(table)
    console.print("\n[dim]Use 'redletters data fetch' to download sources[/dim]")


@data.command("load")
@click.argument("source", required=False)
def data_load(source: str | None):
    """Load fetched data into the database with provenance tracking.

    This is the provenance gate - it verifies integrity before loading:
    - Checks SHA256 matches expected value
    - Records source metadata in sources table
    - Validates all required fields before insertion

    Examples:
        redletters data load morphgnt-sblgnt  # Load specific source
        redletters data load strongs          # Load Strong's dictionary
        redletters data load all              # Load all fetched sources
    """
    from redletters.db.schema_v2 import init_schema_v2
    from redletters.ingest.fetch import SOURCES
    from redletters.ingest.loader import (
        LoaderError,
        MissingSourceError,
        SHAMismatchError,
        load_source,
        load_all,
    )

    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection(db_path)
    init_schema_v2(conn)

    if source == "all" or source is None:
        # Load all available sources
        console.print("[bold blue]Loading all fetched data sources...[/bold blue]")
        console.print("[dim]Verifying integrity and recording provenance.[/dim]\n")

        reports = load_all(conn)

        if not reports:
            console.print("[yellow]No sources fetched yet.[/yellow]")
            console.print("[dim]Run: redletters data fetch[/dim]")
        else:
            for report in reports:
                _print_load_report(report)

    else:
        # Normalize source key
        source_key = source.lower().replace("_", "-")
        if source_key == "strongs":
            source_key = "strongs-greek"
        elif source_key == "morphgnt":
            source_key = "morphgnt-sblgnt"

        if source_key not in SOURCES:
            console.print(f"[red]Unknown source: {source}[/red]")
            console.print(f"[dim]Available: {', '.join(SOURCES.keys())}[/dim]")
            sys.exit(1)

        console.print(f"[bold blue]Loading {source_key}...[/bold blue]")
        console.print("[dim]Verifying integrity and recording provenance.[/dim]\n")

        try:
            report = load_source(conn, source_key)
            _print_load_report(report)
        except MissingSourceError as e:
            console.print(f"[red]✗ {e}[/red]")
            sys.exit(1)
        except SHAMismatchError as e:
            console.print("[red]✗ Integrity check failed![/red]")
            console.print(f"[red]  Expected: {e.expected[:16]}...[/red]")
            console.print(f"[red]  Actual:   {e.actual[:16]}...[/red]")
            console.print(
                "[yellow]  Data may have been modified. Re-fetch with --force.[/yellow]"
            )
            sys.exit(1)
        except LoaderError as e:
            console.print(f"[red]✗ Load failed: {e}[/red]")
            sys.exit(1)

    conn.close()


def _print_load_report(report: "LoadReport") -> None:
    """Print a load report with nice formatting."""
    if report.success:
        console.print(f"[green]✓ {report.source_key}[/green]")
        console.print(f"  [dim]SHA256: {report.sha256_actual[:16]}...[/dim]")
        for key, value in report.counts_inserted.items():
            console.print(f"  [dim]{key}: {value:,}[/dim]")
        if report.warnings:
            for warning in report.warnings:
                console.print(f"  [yellow]⚠ {warning}[/yellow]")
    else:
        console.print(f"[red]✗ {report.source_key}: {report.error}[/red]")


@cli.command()
def licenses():
    """Show license and provenance report for all data sources.

    Displays attribution requirements, share-alike obligations,
    and retrieval timestamps for transparency.
    """
    from redletters.ingest.fetch import print_license_report

    print_license_report()


if __name__ == "__main__":
    cli()
