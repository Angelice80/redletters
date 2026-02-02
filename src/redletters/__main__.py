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
from redletters.engine_spine.cli import register_cli_commands

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


@cli.command()
@click.argument("reference")
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["readable", "traceable"]),
    default="readable",
    help="Enforcement mode (readable restricts claim types)",
)
@click.option(
    "--session",
    "-s",
    default="cli-default",
    help="Session ID for acknowledgement tracking",
)
@click.option(
    "--ack",
    type=str,
    multiple=True,
    help="Acknowledge variant (format: ref:reading_index). Can be repeated or comma-separated.",
)
@click.option("--output", "-o", type=click.Path(), help="Output JSON to file")
@click.option(
    "--scenario",
    default="default",
    help="Translator scenario (default/high_inference/epistemic_pressure/clean)",
)
@click.option(
    "--translator",
    "-t",
    type=click.Choice(["fake", "literal", "fluent", "traceable"]),
    default=None,
    help="Translator type (fake=test data, literal=glosses, fluent=readable, traceable=ledger)",
)
@click.option(
    "--ledger",
    is_flag=True,
    help="Show token ledger in human output (traceable mode only)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON (includes ledger in traceable mode)",
)
@click.option(
    "--data-root",
    type=click.Path(),
    help="Override data root for installed sources",
)
def translate(
    reference: str,
    mode: str,
    session: str,
    ack: tuple[str, ...],
    output: str | None,
    scenario: str,
    translator: str | None,
    ledger: bool,
    output_json: bool,
    data_root: str | None,
):
    """Translate a passage with receipt-grade output.

    Accepts human references like "John 1:18", "Jn 1:18-19", or verse_ids.
    Returns SBLGNT text, variants side-by-side, claims with enforcement,
    layered confidence scoring, and full provenance.

    If a gate is triggered (variant acknowledgement or mode escalation),
    the command returns a gate response instead of a translation.

    Sprint 10: Use --translator traceable with --mode traceable to get
    token-level ledger with gloss provenance and confidence scoring.

    Examples:
        redletters translate "John 1:18"
        redletters translate "John 1:18-19"
        redletters translate "Jn 1:18–19"  # with en-dash
        redletters translate "John 1:18" --mode traceable
        redletters translate "John 1:18" --translator literal
        redletters translate "John 1:18" --translator traceable --mode traceable --json
        redletters translate "John 1:18" --translator traceable --mode traceable --ledger
        redletters translate "John 1:18" --ack "John.1.18:0"
    """
    from redletters.pipeline import (
        translate_passage,
        GateResponsePayload,
        get_translator,
    )
    from redletters.pipeline.orchestrator import acknowledge_variant
    from redletters.sources import (
        SourceInstaller,
        InstalledSpineProvider,
        SpineMissingError,
    )

    conn = get_connection(settings.db_path)

    # Handle acknowledgements if provided (supports multiple --ack or comma-separated)
    if ack:
        # Flatten comma-separated values
        ack_items = []
        for a in ack:
            ack_items.extend([item.strip() for item in a.split(",") if item.strip()])

        for ack_item in ack_items:
            try:
                ref_part, reading_str = ack_item.rsplit(":", 1)
                reading_index = int(reading_str)
                acknowledge_variant(conn, session, ref_part, reading_index, "cli-ack")
                console.print(
                    f"[green]✓ Acknowledged {ref_part} reading {reading_index}[/green]"
                )
            except (ValueError, IndexError) as e:
                console.print(f"[red]Invalid --ack format for '{ack_item}': {e}[/red]")
                console.print(
                    "[dim]Expected format: ref:reading_index (e.g., 'John.1.18:0')[/dim]"
                )
                sys.exit(1)

    # Determine translator and spine provider
    spine_provider = None
    translator_instance = None
    source_id = ""
    source_license = ""

    if translator in ("literal", "fluent", "traceable"):
        # Need installed spine for literal/fluent/traceable translation
        try:
            installer = SourceInstaller(data_root=data_root)

            # Try to find an installed spine
            for spine_id in ["morphgnt-sblgnt", "open-greek-nt"]:
                if installer.is_installed(spine_id):
                    installed = installer.get_installed(spine_id)
                    source_id = installed.source_id
                    source_license = installed.license
                    spine_provider = InstalledSpineProvider(
                        source_id=spine_id,
                        data_root=data_root,
                        require_installed=True,
                    )
                    break

            if spine_provider is None:
                console.print("[red]Error: No spine data installed.[/red]")
                console.print(
                    f"\nTo use --translator {translator}, install spine data first:\n"
                )
                console.print("  redletters sources install morphgnt-sblgnt")
                console.print("  # OR for open-license alternative:")
                console.print("  redletters sources install open-greek-nt\n")
                conn.close()
                sys.exit(1)

            translator_instance = get_translator(
                translator_type=translator,
                source_id=source_id,
                source_license=source_license,
            )
        except SpineMissingError as e:
            console.print(f"[red]Error: {e}[/red]")
            conn.close()
            sys.exit(1)
    else:
        # Use fake translator
        translator_instance = get_translator(
            translator_type="fake",
            scenario=scenario,
        )

    # Build options
    options = {"scenario": scenario}
    if spine_provider:
        options["spine_provider"] = spine_provider

    # Run translate_passage
    try:
        result = translate_passage(
            conn=conn,
            reference=reference,
            mode=mode,  # type: ignore
            session_id=session,
            options=options,
            translator=translator_instance,
        )
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        conn.close()
        sys.exit(1)

    conn.close()

    # Handle gate response
    if isinstance(result, GateResponsePayload):
        console.print(
            Panel(
                f"[bold yellow]{result.title}[/bold yellow]\n\n"
                f"{result.message}\n\n"
                f"[dim]{result.prompt}[/dim]",
                title="Gate Required",
                border_style="yellow",
            )
        )

        # Show required acks for multi-verse passages
        if result.required_acks and len(result.required_acks) > 1:
            console.print("\n[bold]Required Acknowledgements:[/bold]")
            for ra in result.required_acks:
                console.print(
                    f"  [yellow]•[/yellow] {ra.variant_ref} ({ra.significance})"
                )
                console.print(f"    [dim]{ra.message}[/dim]")

        # Show variants side-by-side
        if result.variants_side_by_side:
            console.print("\n[bold]Variants at this passage:[/bold]")
            for v in result.variants_side_by_side:
                ack_marker = (
                    "[green]✓[/green]" if v.acknowledged else "[yellow]?[/yellow]"
                )
                console.print(
                    f"\n  {ack_marker} [cyan]{v.ref}[/cyan] ({v.significance})"
                )
                console.print(f"    [bold]SBLGNT:[/bold] {v.sblgnt_reading}")
                console.print(f"    [dim]Witnesses: {v.sblgnt_witnesses}[/dim]")
                for alt in v.alternate_readings:
                    console.print(
                        f"    [yellow]Alt {alt['index']}:[/yellow] {alt['surface_text']}"
                    )
                    console.print(f"    [dim]Witnesses: {alt['witnesses']}[/dim]")

        # Show options
        console.print("\n[bold]Options:[/bold]")
        for opt in result.options:
            default = " [green](default)[/green]" if opt.is_default else ""
            console.print(f"  • [cyan]{opt.id}[/cyan]{default}: {opt.label}")
            console.print(f"    [dim]{opt.description}[/dim]")

        console.print("\n[dim]To acknowledge, re-run with --ack option:[/dim]")
        if result.gate_type == "variant":
            # Build ack command suggestion
            if result.required_acks:
                ack_args = " ".join(
                    f'--ack "{ra.variant_ref}:{ra.reading_index or 0}"'
                    for ra in result.required_acks
                )
                console.print(f'  redletters translate "{reference}" {ack_args}')
            elif result.variants_side_by_side:
                console.print(
                    f'  redletters translate "{reference}" --ack "{result.variants_side_by_side[0].ref}:0"'
                )

            # GUI hint for easier workflow
            console.print(
                "\n[cyan]Tip:[/cyan] Use the GUI for an easier acknowledgement workflow:"
            )
            console.print("  redletters serve  # Start API server")
            console.print("  # Then open GUI and navigate to Translate screen")
        elif result.gate_type == "escalation":
            console.print(f'  redletters translate "{reference}" --mode traceable')

        if output:
            Path(output).write_text(
                json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
            )
            console.print(f"\n[green]✓ Gate response written to {output}[/green]")

        sys.exit(2)  # Exit code 2 indicates gate required

    # Handle translation response
    result_dict = result.to_dict()

    # JSON output mode
    if output_json:
        console.print(json.dumps(result_dict, indent=2, ensure_ascii=False))
        return

    if output:
        Path(output).write_text(json.dumps(result_dict, indent=2, ensure_ascii=False))
        console.print(f"[green]✓ Output written to {output}[/green]")
    else:
        # Show passage info
        display_ref = result.normalized_ref if result.normalized_ref else reference
        verse_count = len(result.verse_ids) if result.verse_ids else 1

        # Pretty print
        console.print(
            Panel(
                f"[bold]{display_ref}[/bold] ({mode} mode, {verse_count} verse{'s' if verse_count > 1 else ''})\n\n"
                f"[cyan]SBLGNT:[/cyan] {result.sblgnt_text}\n\n"
                f"[green]Translation:[/green] {result.translation_text}",
                title="Translation",
            )
        )

        # Show per-verse blocks for multi-verse passages
        if result.verse_blocks and len(result.verse_blocks) > 1:
            console.print("\n[bold]Per-Verse Breakdown:[/bold]")
            for vb in result.verse_blocks:
                console.print(f"\n  [cyan]{vb.verse_id}[/cyan]")
                console.print(f"    Greek: {vb.sblgnt_text}")
                if vb.confidence:
                    console.print(
                        f"    [dim]Confidence: {vb.confidence.composite:.2f}[/dim]"
                    )

        # Variants
        if result.variants:
            console.print("\n[bold]Variants (side-by-side):[/bold]")
            for v in result.variants:
                ack_marker = "[green]✓[/green]" if v.acknowledged else ""
                console.print(
                    f"  {ack_marker} [cyan]{v.ref}[/cyan]: {v.sblgnt_reading} ({v.significance})"
                )
                for alt in v.alternate_readings:
                    console.print(f"    [yellow]Alt:[/yellow] {alt['surface_text']}")

        # Claims
        console.print("\n[bold]Claims:[/bold]")
        for c in result.claims:
            status = "[green]✓[/green]" if c.enforcement_allowed else "[red]✗[/red]"
            console.print(
                f"  {status} [{c.claim_type_label}] {c.content[:60]}{'...' if len(c.content) > 60 else ''}"
            )
            if c.warnings:
                for w in c.warnings[:2]:
                    console.print(f"    [yellow]⚠ {w}[/yellow]")
            if not c.enforcement_allowed:
                console.print(f"    [red]{c.enforcement_reason}[/red]")

        # Confidence
        if result.confidence:
            conf = result.confidence
            console.print(
                f"\n[bold]Confidence:[/bold] {conf.composite:.2f} (weakest: {conf.weakest_layer})"
            )
            console.print(
                f"  Textual:      {conf.textual.score:.2f} - {conf.textual.rationale[:50]}..."
            )
            console.print(
                f"  Grammatical:  {conf.grammatical.score:.2f} - {conf.grammatical.rationale[:50]}..."
            )
            console.print(
                f"  Lexical:      {conf.lexical.score:.2f} - {conf.lexical.rationale[:50]}..."
            )
            console.print(
                f"  Interpretive: {conf.interpretive.score:.2f} - {conf.interpretive.rationale[:50]}..."
            )

        # Receipts summary
        console.print(
            f"\n[dim]Checks run: {len(result.receipts.checks_run)} | Gates satisfied: {len(result.receipts.gates_satisfied)} | Verses: {', '.join(result.verse_ids)}[/dim]"
        )

        # Ledger display (Sprint 10: traceable mode)
        if ledger and result_dict.get("ledger"):
            console.print("\n[bold cyan]Token Ledger:[/bold cyan]")
            for verse_ledger in result_dict["ledger"]:
                console.print(
                    f"\n  [cyan]{verse_ledger['normalized_ref']}[/cyan] ({len(verse_ledger['tokens'])} tokens)"
                )

                # Create token table
                token_table = Table(show_header=True, header_style="bold dim")
                token_table.add_column("#", style="dim", width=4)
                token_table.add_column("Surface", style="cyan")
                token_table.add_column("Lemma", style="cyan")
                token_table.add_column("Morph", style="dim")
                token_table.add_column("Gloss")
                token_table.add_column("Source", style="dim")
                token_table.add_column("T/G/L/I", style="yellow")

                for token in verse_ledger["tokens"]:
                    conf = token["confidence"]
                    conf_str = (
                        f"{conf['textual']:.1f}/{conf['grammatical']:.1f}/"
                        f"{conf['lexical']:.1f}/{conf['interpretive']:.1f}"
                    )
                    token_table.add_row(
                        str(token["position"] + 1),
                        token["surface"],
                        token["lemma"] or "—",
                        token["morph"] or "—",
                        token["gloss"],
                        token["gloss_source"],
                        conf_str,
                    )

                console.print(token_table)

                # Provenance
                prov = verse_ledger["provenance"]
                ecs = prov["evidence_class_summary"]
                console.print(f"  [dim]Spine: {prov['spine_source_id']}[/dim]")
                if prov["comparative_sources_used"]:
                    console.print(
                        f"  [dim]Comparative: {', '.join(prov['comparative_sources_used'])}[/dim]"
                    )
                evidence_parts = []
                if ecs["manuscript_count"] > 0:
                    evidence_parts.append(f"{ecs['manuscript_count']} MSS")
                if ecs["edition_count"] > 0:
                    evidence_parts.append(f"{ecs['edition_count']} Ed")
                if ecs["tradition_count"] > 0:
                    evidence_parts.append(f"{ecs['tradition_count']} Trad")
                if ecs["other_count"] > 0:
                    evidence_parts.append(f"{ecs['other_count']} Other")
                if evidence_parts:
                    console.print(f"  [dim]Evidence: {', '.join(evidence_parts)}[/dim]")
        elif ledger and not result_dict.get("ledger"):
            console.print(
                "\n[dim]No ledger data. Use --translator traceable --mode traceable for token ledger.[/dim]"
            )


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


# ============================================================================
# Source Pack commands (Sprint 2)
# ============================================================================


@cli.group()
def sources():
    """Manage source packs from sources_catalog.yaml."""
    pass


@sources.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def sources_list(as_json: bool):
    """List all configured sources and their status."""
    from redletters.sources.catalog import SourceCatalog
    from redletters.sources.resolver import SourceResolver

    catalog = SourceCatalog.load()
    resolver = SourceResolver(catalog)

    if as_json:
        import json as json_lib

        output = []
        for key, source in catalog.sources.items():
            resolved = resolver.resolve(key)
            output.append(
                {
                    **source.to_dict(),
                    "exists": resolved.exists,
                    "is_complete": resolved.is_complete,
                    "root_path": str(resolved.root_path),
                }
            )
        console.print(json_lib.dumps(output, indent=2, ensure_ascii=False))
        return

    table = Table(title="Source Packs")
    table.add_column("Key", style="cyan")
    table.add_column("Name")
    table.add_column("Role", style="yellow")
    table.add_column("License")
    table.add_column("Status")

    for key, source in catalog.sources.items():
        resolved = resolver.resolve(key)
        if resolved.is_complete:
            status = "[green]✓ Ready[/green]"
        elif resolved.exists:
            status = "[yellow]⚠ Partial[/yellow]"
        else:
            status = "[dim]Not installed[/dim]"

        role_display = source.role.value.replace("_", " ").title()
        table.add_row(key, source.name, role_display, source.license, status)

    console.print(table)

    # Show spine info
    spine = catalog.spine
    if spine:
        console.print(f"\n[bold]Canonical Spine (ADR-007):[/bold] {spine.key}")


@sources.command("validate")
def sources_validate():
    """Validate sources_catalog.yaml structure and completeness."""
    from redletters.sources.catalog import SourceCatalog, CatalogValidationError

    try:
        catalog = SourceCatalog.load()
    except CatalogValidationError as e:
        console.print(f"[red]Catalog validation failed:[/red] {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]Catalog not found:[/red] {e}")
        sys.exit(1)

    warnings = catalog.validate()

    if warnings:
        console.print("[yellow]Validation warnings:[/yellow]")
        for warning in warnings:
            console.print(f"  [yellow]⚠[/yellow] {warning}")
    else:
        console.print("[green]✓ Catalog valid[/green]")

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Total sources: {len(catalog.sources)}")
    console.print(f"  Spine: {catalog.spine.key if catalog.spine else 'MISSING'}")
    console.print(f"  Comparative editions: {len(catalog.comparative_editions)}")


@sources.command("info")
@click.argument("pack_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def sources_info(pack_id: str, as_json: bool):
    """Show detailed info about a source pack."""
    from redletters.sources.catalog import SourceCatalog
    from redletters.sources.resolver import SourceResolver

    catalog = SourceCatalog.load()
    source = catalog.get(pack_id)

    if not source:
        console.print(f"[red]Source not found: {pack_id}[/red]")
        console.print(f"[dim]Available: {', '.join(catalog.sources.keys())}[/dim]")
        sys.exit(1)

    resolver = SourceResolver(catalog)
    resolved = resolver.resolve(pack_id)

    if as_json:
        import json as json_lib

        output = {
            **source.to_dict(),
            "resolved": {
                "root_path": str(resolved.root_path),
                "exists": resolved.exists,
                "is_complete": resolved.is_complete,
                "files": [str(f) for f in resolved.files],
                "missing_files": resolved.missing_files,
            },
        }
        console.print(json_lib.dumps(output, indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(f"[bold]{source.name}[/bold]\n{source.key}", title="Source Pack")
    )
    console.print(f"  [cyan]Role:[/cyan] {source.role.value}")
    console.print(f"  [cyan]License:[/cyan] {source.license}")
    if source.version:
        console.print(f"  [cyan]Version:[/cyan] {source.version}")
    if source.repo:
        console.print(f"  [cyan]Repository:[/cyan] {source.repo}")
    if source.commit:
        pin_status = (
            "[green]pinned[/green]"
            if source.has_pinned_commit
            else "[yellow]not pinned[/yellow]"
        )
        console.print(f"  [cyan]Commit:[/cyan] {source.commit[:12]}... ({pin_status})")

    console.print("\n[bold]Resolution:[/bold]")
    console.print(f"  [cyan]Path:[/cyan] {resolved.root_path}")
    console.print(f"  [cyan]Exists:[/cyan] {'Yes' if resolved.exists else 'No'}")
    if resolved.files:
        console.print(f"  [cyan]Files found:[/cyan] {len(resolved.files)}")
    if resolved.missing_files:
        console.print(
            f"  [yellow]Missing files:[/yellow] {len(resolved.missing_files)}"
        )
        for f in resolved.missing_files[:5]:
            console.print(f"    - {f}")

    if source.notes:
        console.print(f"\n[bold]Notes:[/bold]\n{source.notes.strip()}")


@sources.command("install")
@click.argument("source_id")
@click.option(
    "--data-root",
    type=click.Path(),
    help="Override data root directory",
)
@click.option(
    "--accept-eula",
    is_flag=True,
    help="Accept EULA for licensed content",
)
@click.option(
    "--force",
    is_flag=True,
    help="Reinstall even if already installed",
)
def sources_install(
    source_id: str,
    data_root: str | None,
    accept_eula: bool,
    force: bool,
):
    """Install a source pack.

    Downloads and installs data from the configured source.
    EULA-licensed sources require --accept-eula flag.

    Examples:
        redletters sources install morphgnt-sblgnt
        redletters sources install open-greek-nt --accept-eula
    """
    from redletters.sources.installer import SourceInstaller

    installer = SourceInstaller(data_root=data_root)
    result = installer.install(source_id, accept_eula=accept_eula, force=force)

    if result.success:
        console.print(f"[green]✓ {result.message}[/green]")
        if result.eula_required:
            console.print(
                "[dim]EULA accepted. License terms apply to usage of this data.[/dim]"
            )
    else:
        if result.needs_eula:
            console.print("[yellow]⚠ EULA Required[/yellow]")
            console.print(f"\n{result.message}")
            sys.exit(2)  # Exit code 2 indicates EULA required
        else:
            console.print(f"[red]✗ {result.message}[/red]")
            sys.exit(1)


@sources.command("status")
@click.option(
    "--data-root",
    type=click.Path(),
    help="Override data root directory",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def sources_status(data_root: str | None, as_json: bool):
    """Show installation status of all sources."""
    from redletters.sources.installer import SourceInstaller

    installer = SourceInstaller(data_root=data_root)
    status = installer.status()

    if as_json:
        import json as json_lib

        console.print(json_lib.dumps(status, indent=2, ensure_ascii=False))
        return

    console.print(f"[bold]Data Root:[/bold] {status['data_root']}")
    console.print(f"[bold]Manifest:[/bold] {status['manifest_path']}\n")

    table = Table(title="Source Installation Status")
    table.add_column("Source ID", style="cyan")
    table.add_column("Name")
    table.add_column("License")
    table.add_column("EULA?")
    table.add_column("Status")

    for source_id, info in status["sources"].items():
        if info["installed"]:
            install_status = "[green]✓ Installed[/green]"
            if info.get("eula_accepted"):
                install_status += " [dim](EULA accepted)[/dim]"
        else:
            install_status = "[dim]Not installed[/dim]"

        eula = "[yellow]Yes[/yellow]" if info["requires_eula"] else "No"

        table.add_row(
            source_id,
            info["name"],
            info["license"],
            eula,
            install_status,
        )

    console.print(table)

    # Show installed details
    installed_count = sum(1 for info in status["sources"].values() if info["installed"])
    if installed_count > 0:
        console.print(f"\n[bold]Installed sources:[/bold] {installed_count}")


@sources.command("uninstall")
@click.argument("source_id")
@click.option(
    "--data-root",
    type=click.Path(),
    help="Override data root directory",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation",
)
def sources_uninstall(source_id: str, data_root: str | None, yes: bool):
    """Uninstall a source pack.

    Removes the installed data for a source pack.

    Examples:
        redletters sources uninstall morphgnt-sblgnt
    """
    from redletters.sources.installer import SourceInstaller

    installer = SourceInstaller(data_root=data_root)

    if not installer.is_installed(source_id):
        console.print(f"[yellow]Source not installed: {source_id}[/yellow]")
        sys.exit(0)

    installed = installer.get_installed(source_id)

    if not yes:
        console.print(f"[bold]Uninstall {source_id}?[/bold]")
        console.print(f"  Path: {installed.install_path}")
        if not click.confirm("Proceed?"):
            console.print("[dim]Cancelled[/dim]")
            sys.exit(0)

    result = installer.uninstall(source_id)

    if result.success:
        console.print(f"[green]✓ {result.message}[/green]")
    else:
        console.print(f"[red]✗ {result.message}[/red]")
        sys.exit(1)


# ============================================================================
# Variants commands (Sprint 2)
# ============================================================================


@cli.group()
def variants():
    """Build and manage textual variants."""
    pass


@variants.command("build")
@click.argument("reference")
@click.option(
    "--scope",
    type=click.Choice(["verse", "chapter", "book"]),
    default="chapter",
    help="Build scope (default: chapter)",
)
@click.option(
    "--all-installed",
    is_flag=True,
    default=True,
    help="Use all installed comparative packs (default: True)",
)
@click.option(
    "--pack",
    "-p",
    multiple=True,
    help="Specific pack(s) to use (overrides --all-installed)",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def variants_build(
    reference: str,
    scope: str,
    all_installed: bool,
    pack: tuple,
    as_json: bool,
):
    """Build variants by comparing editions against spine (Sprint 9: B5).

    Uses all installed comparative packs by default to aggregate variants.
    Identical readings from multiple packs are merged with combined support sets.

    Examples:
        redletters variants build "John.1" --scope chapter
        redletters variants build "John.1.18" --scope verse
        redletters variants build "John" --scope book
        redletters variants build "John.1" --pack westcott-hort-john --pack byzantine-john
    """
    from redletters.variants.store import VariantStore
    from redletters.variants.builder import VariantBuilder
    from redletters.sources.installer import SourceInstaller
    from redletters.sources.pack_loader import PackLoader
    from redletters.sources.spine import SBLGNTSpine, PackSpineAdapter

    conn = get_connection(settings.db_path)

    try:
        # Initialize variant store
        variant_store = VariantStore(conn)
        variant_store.init_schema()

        # Get spine
        installer = SourceInstaller()
        spine_source = installer.catalog.spine
        if not spine_source or not installer.is_installed(spine_source.key):
            console.print("[red]Error: Spine not installed.[/red]")
            console.print("[dim]Run: redletters sources install morphgnt-sblgnt[/dim]")
            conn.close()
            sys.exit(1)

        spine_installed = installer.get_installed(spine_source.key)
        spine = SBLGNTSpine(spine_installed.install_path, spine_source.key)

        # Initialize variant builder
        builder = VariantBuilder(spine, variant_store)

        # Determine which packs to use
        packs_to_use = []
        if pack:
            # Specific packs requested
            packs_to_use = list(pack)
        elif all_installed:
            # All installed comparative packs
            for source in installer.catalog.comparative_editions:
                if installer.is_installed(source.key):
                    packs_to_use.append(source.key)

        if not packs_to_use:
            console.print("[yellow]No comparative packs installed.[/yellow]")
            console.print("[dim]Install packs first, e.g.:[/dim]")
            console.print("  redletters sources install westcott-hort-john")
            conn.close()
            sys.exit(0)

        # Add editions from packs
        packs_loaded = 0
        for pack_id in packs_to_use:
            source = installer.catalog.get(pack_id)
            if not source:
                console.print(f"[yellow]Pack not found: {pack_id}[/yellow]")
                continue

            installed = installer.get_installed(pack_id)
            if not installed:
                console.print(f"[yellow]Pack not installed: {pack_id}[/yellow]")
                continue

            if source.is_pack:
                pack_loader = PackLoader(installed.install_path)
                if pack_loader.load():
                    pack_spine = PackSpineAdapter(pack_loader, source.key)
                    builder.add_edition(
                        edition_key=source.key,
                        edition_spine=pack_spine,
                        witness_siglum=source.witness_siglum or source.key,
                        date_range=source.date_range,
                        source_pack_id=source.key,
                    )
                    packs_loaded += 1
                    if not as_json:
                        console.print(f"  [dim]Loaded: {source.key}[/dim]")

        if packs_loaded == 0:
            console.print("[red]No packs could be loaded.[/red]")
            conn.close()
            sys.exit(1)

        if not as_json:
            console.print(
                f"[bold blue]Building variants for {reference} ({scope})...[/bold blue]"
            )
            console.print(f"[dim]Using {packs_loaded} comparative pack(s)[/dim]")

        # Build based on scope
        if scope == "book":
            book = reference.split()[0] if " " in reference else reference.split(".")[0]
            result = builder.build_book(book)
        elif scope == "chapter":
            parts = reference.replace(".", " ").split()
            book = parts[0]
            chapter = int(parts[1]) if len(parts) > 1 else 1
            result = builder.build_chapter(book, chapter)
        else:
            result = builder.build_verse(reference)

        conn.close()

        if as_json:
            import json as json_lib

            output = {
                "reference": reference,
                "scope": scope,
                "packs_used": packs_to_use,
                "verses_processed": result.verses_processed,
                "variants_created": result.variants_created,
                "variants_updated": result.variants_updated,
                "variants_unchanged": result.variants_unchanged,
                "errors": result.errors,
            }
            console.print(json_lib.dumps(output, indent=2))
        else:
            console.print("\n[green]✓ Build complete[/green]")
            console.print(f"  Verses processed: {result.verses_processed}")
            console.print(f"  Variants created: {result.variants_created}")
            console.print(f"  Variants updated: {result.variants_updated}")
            console.print(f"  Variants unchanged: {result.variants_unchanged}")
            if result.errors:
                console.print(f"\n[yellow]Errors ({len(result.errors)}):[/yellow]")
                for err in result.errors[:5]:
                    console.print(f"  [yellow]⚠[/yellow] {err}")

    except Exception as e:
        conn.close()
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@variants.command("dossier")
@click.argument("reference")
@click.option(
    "--scope",
    type=click.Choice(["verse", "passage", "chapter", "book"]),
    default="verse",
    help="Scope of dossier (default: verse)",
)
@click.option("--session-id", help="Session ID for ack state")
@click.option("--output", "-o", type=click.Path(), help="Output file")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON (default)")
def variants_dossier(
    reference: str,
    scope: str,
    session_id: str | None,
    output: str | None,
    as_json: bool,
):
    """Export variant dossier for a reference.

    Creates a detailed dossier with:
    - Spine reading (SBLGNT) marked default
    - All readings side-by-side with witness support
    - Reason fields and gating requirements
    - Acknowledgement state (if session_id provided)
    - Provenance (which packs contributed each reading)

    Examples:
        redletters variants dossier "John.1.18"
        redletters variants dossier "John.1.18" --scope verse
        redletters variants dossier "John.1" --scope chapter
        redletters variants dossier "John.1.18" --session-id abc123 -o dossier.json
    """
    from redletters.variants.store import VariantStore
    from redletters.variants.dossier import generate_dossier

    conn = get_connection(settings.db_path)
    store = VariantStore(conn)

    try:
        store.init_schema()
    except Exception:
        pass

    # TODO: Load ack state from session if session_id provided
    ack_state: dict[str, int] = {}

    dossier = generate_dossier(
        variant_store=store,
        reference=reference,
        scope=scope,
        ack_state=ack_state,
        session_id=session_id,
    )

    conn.close()

    import json as json_lib

    dossier_dict = dossier.to_dict()

    if output:
        Path(output).write_text(
            json_lib.dumps(dossier_dict, indent=2, ensure_ascii=False)
        )
        console.print(f"[green]✓ Dossier written to {output}[/green]")
    else:
        # Always output as JSON for dossier
        console.print(json_lib.dumps(dossier_dict, indent=2, ensure_ascii=False))


@variants.command("list")
@click.option("--verse", "-v", help="Filter by verse (e.g., John.1.18)")
@click.option(
    "--significance",
    "-s",
    type=click.Choice(["trivial", "minor", "significant", "major"]),
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def variants_list(verse: str | None, significance: str | None, as_json: bool):
    """List variants in the database."""
    from redletters.variants.store import VariantStore
    from redletters.variants.models import SignificanceLevel

    conn = get_connection(settings.db_path)
    store = VariantStore(conn)

    try:
        store.init_schema()
    except Exception:
        pass

    if verse:
        variants_list = store.get_variants_for_verse(verse)
    elif significance:
        sig_level = SignificanceLevel(significance)
        # Get all variants of this significance (simplified)
        variants_list = store.get_significant_variants()
        variants_list = [v for v in variants_list if v.significance == sig_level]
    else:
        # Get all significant variants
        variants_list = store.get_significant_variants()

    conn.close()

    if as_json:
        import json as json_lib

        output = [v.to_dict() for v in variants_list]
        console.print(json_lib.dumps(output, indent=2, ensure_ascii=False))
        return

    if not variants_list:
        console.print("[dim]No variants found.[/dim]")
        return

    table = Table(title="Variants")
    table.add_column("Reference", style="cyan")
    table.add_column("Position")
    table.add_column("Classification")
    table.add_column("Significance", style="yellow")
    table.add_column("Readings")

    for v in variants_list:
        sig_style = {
            "major": "red",
            "significant": "yellow",
            "minor": "white",
            "trivial": "dim",
        }.get(v.significance.value, "white")

        table.add_row(
            v.ref,
            str(v.position),
            v.classification.value,
            f"[{sig_style}]{v.significance.value}[/{sig_style}]",
            str(v.reading_count),
        )

    console.print(table)


# ============================================================================
# Packs commands (Sprint 8)
# ============================================================================


@cli.group()
def packs():
    """Manage data packs (Pack Spec v1.1)."""
    pass


@packs.command("validate")
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--strict",
    is_flag=True,
    help="Treat warnings as errors",
)
@click.option(
    "--format-version",
    default="1.1",
    help="Expected format version (default: 1.1)",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def packs_validate(path: str, strict: bool, format_version: str, as_json: bool):
    """Validate a pack against Pack Spec v1.1.

    Checks manifest fields, TSV format, verse_id patterns, and coverage.

    Examples:
        redletters packs validate data/packs/westcott-hort-john
        redletters packs validate data/packs/mypack --strict
    """
    from redletters.sources.pack_validator import validate_pack

    result = validate_pack(path, strict=strict, expected_version=format_version)

    if as_json:
        import json as json_lib

        output = {
            "valid": result.valid,
            "manifest_version": result.manifest_version,
            "verse_count": result.verse_count,
            "books_found": result.books_found,
            "errors": [{"path": e.path, "message": e.message} for e in result.errors],
            "warnings": [
                {"path": w.path, "message": w.message} for w in result.warnings
            ],
        }
        console.print(json_lib.dumps(output, indent=2, ensure_ascii=False))
        if not result.valid:
            sys.exit(1)
        return

    if result.valid:
        console.print(
            f"[green]✓ Pack valid[/green] (format version: {result.manifest_version})"
        )
        console.print(f"  Verses: {result.verse_count}")
        console.print(f"  Books: {', '.join(result.books_found)}")
    else:
        console.print("[red]✗ Pack validation failed[/red]")

    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for err in result.errors:
            console.print(f"  [red]✗[/red] {err.path}: {err.message}")

    if result.warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warn in result.warnings:
            console.print(f"  [yellow]⚠[/yellow] {warn.path}: {warn.message}")

    if not result.valid:
        sys.exit(1)


@packs.command("index")
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--output-manifest",
    is_flag=True,
    help="Update manifest.json in place",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print index without writing",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def packs_index(path: str, output_manifest: bool, dry_run: bool, as_json: bool):
    """Generate or update pack index.

    Creates a lightweight index (book -> chapters -> verse count) for
    faster status display and variant building.

    Examples:
        redletters packs index data/packs/westcott-hort-john
        redletters packs index data/packs/mypack --output-manifest
        redletters packs index data/packs/mypack --dry-run
    """
    from redletters.sources.pack_indexer import PackIndexer

    indexer = PackIndexer(path)
    index = indexer.generate()

    if as_json:
        import json as json_lib

        console.print(json_lib.dumps(index.to_dict(), indent=2, ensure_ascii=False))
        return

    # Show summary
    summary = indexer.get_summary()
    console.print(f"[bold]Pack Index[/bold] ({path})")
    console.print(f"  Total verses: {summary['total_verses']}")
    console.print(f"  Total books: {summary['total_books']}")

    for book_name, book_info in summary["books"].items():
        console.print(
            f"    {book_name}: {book_info['chapters']} chapters, {book_info['verses']} verses"
        )

    if output_manifest and not dry_run:
        indexer.update_manifest()
        console.print("\n[green]✓ manifest.json updated[/green]")
    elif dry_run:
        console.print("\n[dim](dry-run: no files modified)[/dim]")


@packs.command("list")
@click.option(
    "--data-root",
    type=click.Path(),
    help="Override data root directory",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def packs_list(data_root: str | None, as_json: bool):
    """List installed packs with status.

    Shows all packs from sources_catalog.yaml that use format: pack.

    Examples:
        redletters packs list
        redletters packs list --json
    """
    from redletters.sources.catalog import SourceCatalog
    from redletters.sources.pack_loader import PackLoader

    catalog = SourceCatalog.load()

    packs_info = []
    for key, source in catalog.sources.items():
        if source.format != "pack":
            continue

        pack_path = Path(source.pack_path) if source.pack_path else None
        if not pack_path:
            continue

        # Try to load pack
        loader = PackLoader(pack_path)
        loaded = loader.load()

        info = {
            "id": key,
            "name": source.name,
            "pack_path": str(pack_path),
            "exists": pack_path.exists(),
            "loaded": loaded,
            "format_version": "unknown",
            "siglum": source.witness_siglum or "",
            "witness_type": source.witness_type or "",
            "verse_count": 0,
            "coverage": [],
        }

        if loaded and loader.manifest:
            info["format_version"] = loader.manifest.format_version
            info["siglum"] = loader.manifest.effective_siglum
            info["witness_type"] = loader.manifest.witness_type
            info["verse_count"] = len(loader)
            info["coverage"] = loader.manifest.effective_coverage

        packs_info.append(info)

    if as_json:
        import json as json_lib

        console.print(json_lib.dumps(packs_info, indent=2, ensure_ascii=False))
        return

    if not packs_info:
        console.print("[dim]No packs configured in sources_catalog.yaml[/dim]")
        return

    table = Table(title="Installed Packs")
    table.add_column("ID", style="cyan")
    table.add_column("Siglum", style="yellow")
    table.add_column("Type")
    table.add_column("Coverage")
    table.add_column("Verses", justify="right")
    table.add_column("Status")

    for info in packs_info:
        if info["loaded"]:
            status = "[green]✓ Loaded[/green]"
        elif info["exists"]:
            status = "[yellow]⚠ Exists (load failed)[/yellow]"
        else:
            status = "[dim]Not installed[/dim]"

        coverage = ", ".join(info["coverage"][:3])
        if len(info["coverage"]) > 3:
            coverage += f" (+{len(info['coverage']) - 3})"

        table.add_row(
            info["id"],
            info["siglum"],
            info["witness_type"],
            coverage,
            str(info["verse_count"]) if info["verse_count"] > 0 else "-",
            status,
        )

    console.print(table)
    console.print(
        f"\n[dim]Total: {len(packs_info)} pack(s), {sum(p['verse_count'] for p in packs_info)} verses[/dim]"
    )


# Register engine spine CLI commands
register_cli_commands(cli)


if __name__ == "__main__":
    cli()
