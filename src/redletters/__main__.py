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


@cli.command()
@click.option("--port", default=47200, help="Backend port")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
@click.option("--dev", is_flag=True, help="Run GUI in dev mode (npm run dev)")
def gui(port: int, no_browser: bool, dev: bool):
    """Start the GUI with backend.

    Starts the Engine Spine backend and opens the GUI in your browser.
    Press Ctrl+C to stop both.

    Examples:
        redletters gui              # Start backend + open GUI
        redletters gui --dev        # Start backend + GUI dev server
        redletters gui --no-browser # Start backend only, print URL
    """
    import atexit
    import signal
    import subprocess
    import time
    import webbrowser

    import httpx

    from redletters.engine_spine.auth import get_stored_token

    # Find GUI directory
    gui_dir = Path(__file__).parent.parent.parent / "gui"
    gui_dist = gui_dir / "dist" / "index.html"

    if dev and not gui_dir.exists():
        console.print("[red]Error: gui/ directory not found[/red]")
        console.print("[dim]Run from the repository root, or use --no-browser[/dim]")
        sys.exit(1)

    # Track subprocesses for cleanup
    processes: list[subprocess.Popen] = []

    def cleanup():
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()

    atexit.register(cleanup)

    def handle_signal(signum, frame):
        console.print("\n[yellow]Shutting down...[/yellow]")
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Auto-initialize database if needed
    db_path = settings.db_path
    if not db_path.exists():
        console.print("[bold blue]Initializing database with demo data...[/bold blue]")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_connection(db_path)
        init_db(conn)
        load_demo_data(conn)
        conn.close()
        console.print("[green]✓ Database initialized[/green]")

    # Start engine backend
    console.print(f"[bold blue]Starting Engine Spine on port {port}...[/bold blue]")

    engine_proc = subprocess.Popen(
        [sys.executable, "-m", "redletters", "engine", "start", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    processes.append(engine_proc)

    # Wait for engine to be ready
    console.print("[dim]Waiting for engine to start...[/dim]")
    ready = False
    for attempt in range(30):  # 30 attempts, ~6 seconds
        time.sleep(0.2)
        try:
            # Engine generates token on first start, try to get it
            token = get_stored_token()
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            resp = httpx.get(
                f"http://127.0.0.1:{port}/v1/engine/status",
                headers=headers,
                timeout=1.0,
            )
            if resp.status_code == 200:
                ready = True
                break
            elif resp.status_code == 401 and attempt < 10:
                # Token might not be written yet, keep trying
                continue
        except httpx.RequestError:
            pass

    if not ready:
        console.print("[red]Error: Engine failed to start[/red]")
        console.print("[dim]Try running: redletters engine start --port 47200[/dim]")
        cleanup()
        sys.exit(1)

    console.print(f"[green]✓ Engine ready at http://127.0.0.1:{port}[/green]")

    # Get token for auto-injection into GUI URL
    token = get_stored_token()

    if dev:
        # Run GUI dev server
        console.print("[bold blue]Starting GUI dev server...[/bold blue]")

        gui_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=gui_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        processes.append(gui_proc)

        time.sleep(2)  # Let vite start
        gui_base = "http://localhost:5173"
        gui_url = f"{gui_base}#token={token}" if token else gui_base
        console.print(f"[green]✓ GUI dev server at {gui_base}[/green]")

        if not no_browser:
            webbrowser.open(gui_url)
            console.print("[dim]Token auto-configured in browser[/dim]")

        console.print("\n[bold]Press Ctrl+C to stop[/bold]")

        # Stream GUI output
        try:
            while gui_proc.poll() is None:
                line = gui_proc.stdout.readline()
                if line:
                    console.print(f"[dim]{line.decode().rstrip()}[/dim]")
        except KeyboardInterrupt:
            pass

    elif gui_dist.exists():
        # Serve built GUI
        import http.server
        import socket
        import socketserver

        gui_port = 5173

        # Check if port is in use and try to free it
        def is_port_in_use(p: int) -> bool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("localhost", p)) == 0

        if is_port_in_use(gui_port):
            console.print(
                f"[yellow]Port {gui_port} in use, attempting to free...[/yellow]"
            )
            try:
                import subprocess as sp

                # Try to kill process on port (macOS/Linux)
                sp.run(
                    f"lsof -ti:{gui_port} | xargs kill -9",
                    shell=True,
                    capture_output=True,
                )
                time.sleep(0.5)
            except Exception:
                pass

            if is_port_in_use(gui_port):
                console.print(f"[red]Error: Port {gui_port} still in use[/red]")
                console.print(f"[dim]Run: lsof -ti:{gui_port} | xargs kill -9[/dim]")
                cleanup()
                sys.exit(1)

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(gui_dir / "dist"), **kwargs)

            def log_message(self, format, *args):
                pass  # Suppress logging

        gui_base = f"http://localhost:{gui_port}"
        gui_url = f"{gui_base}#token={token}" if token else gui_base
        console.print(f"[green]✓ GUI at {gui_base}[/green]")

        if not no_browser:
            webbrowser.open(gui_url)
            console.print("[dim]Token auto-configured in browser[/dim]")

        console.print("\n[bold]Press Ctrl+C to stop[/bold]")

        with socketserver.TCPServer(("", gui_port), Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass

    else:
        # No GUI available, just run backend
        console.print("[yellow]GUI not built. Run with --dev for dev server.[/yellow]")
        console.print("[dim]Or build GUI: cd gui && npm run build[/dim]")
        console.print(f"\n[bold]Backend running at http://127.0.0.1:{port}[/bold]")
        console.print("[bold]Press Ctrl+C to stop[/bold]")

        try:
            engine_proc.wait()
        except KeyboardInterrupt:
            pass


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


@packs.command("lock")
@click.option(
    "--out",
    "-o",
    type=click.Path(),
    default="lock.json",
    help="Output lockfile path (default: lock.json)",
)
@click.option(
    "--data-root",
    type=click.Path(),
    help="Override data root directory",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON to stdout")
def packs_lock(out: str, data_root: str | None, as_json: bool):
    """Generate a lockfile from installed packs.

    Creates a reproducible environment specification with pack versions,
    content hashes, and install sources.

    Examples:
        redletters packs lock
        redletters packs lock --out myproject.lock.json
        redletters packs lock --json
    """
    from pathlib import Path as PathLib

    from redletters.sources.lockfile import LockfileGenerator

    data_root_path = PathLib(data_root) if data_root else None
    generator = LockfileGenerator(data_root=data_root_path)

    if as_json:
        lockfile = generator.generate()
        console.print(lockfile.to_json(pretty=True))
        return

    output_path = PathLib(out)
    lockfile = generator.save(output_path)

    console.print(f"[green]✓ Lockfile generated:[/green] {output_path}")
    console.print(f"  Tool version: {lockfile.tool_version}")
    console.print(f"  Schema version: {lockfile.schema_version}")
    console.print(f"  Packs: {len(lockfile.packs)}")
    console.print(f"  Hash: {lockfile.lockfile_hash[:16]}...")

    if lockfile.packs:
        console.print("\n[bold]Locked packs:[/bold]")
        for pack in lockfile.packs:
            console.print(
                f"  {pack.pack_id} ({pack.role}): {pack.version or 'unversioned'} [{pack.content_hash[:12]}...]"
            )


@packs.command("sync")
@click.option(
    "--lock",
    "-l",
    "lockfile_path",
    type=click.Path(exists=True),
    required=True,
    help="Path to lockfile",
)
@click.option(
    "--force",
    is_flag=True,
    help="Accept hash mismatches with audit record",
)
@click.option(
    "--data-root",
    type=click.Path(),
    help="Override data root directory",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def packs_sync(lockfile_path: str, force: bool, data_root: str | None, as_json: bool):
    """Verify and sync installed packs to match a lockfile.

    Checks that installed packs match the lockfile specification.
    If --force is used, hash mismatches are accepted with an audit record.

    Examples:
        redletters packs sync --lock lock.json
        redletters packs sync --lock lock.json --force
    """
    from pathlib import Path as PathLib

    from redletters.sources.lockfile import Lockfile, LockfileSyncer

    data_root_path = PathLib(data_root) if data_root else None
    syncer = LockfileSyncer(data_root=data_root_path)

    # Load lockfile
    lockfile = Lockfile.load(PathLib(lockfile_path))

    # Perform sync/verify
    result = syncer.sync(lockfile, force=force)

    if as_json:
        import json as json_lib

        console.print(json_lib.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        if not result.valid:
            sys.exit(1)
        return

    # Display results
    if result.valid:
        console.print("[green]✓ Environment matches lockfile[/green]")
    else:
        console.print("[red]✗ Environment does not match lockfile[/red]")

    console.print(f"\n  OK: {result.ok_count}")
    if result.missing:
        console.print(f"  [red]Missing: {len(result.missing)}[/red]")
    if result.mismatched:
        console.print(f"  [yellow]Hash mismatch: {len(result.mismatched)}[/yellow]")
    if result.extra:
        console.print(f"  [dim]Extra: {len(result.extra)}[/dim]")

    if result.forced:
        console.print(f"\n[yellow]⚠ Forced sync at {result.forced_at}[/yellow]")

    # Show details for non-OK packs
    non_ok = [p for p in result.packs if p.status != "ok"]
    if non_ok:
        console.print("\n[bold]Details:[/bold]")
        for pack_status in non_ok:
            status_color = {
                "missing": "red",
                "hash_mismatch": "yellow",
                "extra": "dim",
            }.get(pack_status.status, "white")
            console.print(
                f"  [{status_color}]{pack_status.pack_id}[/{status_color}]: {pack_status.status}"
            )
            if pack_status.message:
                console.print(f"    {pack_status.message}")
            if pack_status.expected_hash and pack_status.actual_hash:
                console.print(f"    Expected: {pack_status.expected_hash[:16]}...")
                console.print(f"    Actual:   {pack_status.actual_hash[:16]}...")

    if not result.valid:
        sys.exit(1)


# ============================================================================
# Gates commands (Sprint 11 - v0.3)
# ============================================================================


@cli.group()
def gates():
    """Manage variant acknowledgement gates."""
    pass


@gates.command("acknowledge")
@click.argument("reference")
@click.option(
    "--reason",
    "-r",
    required=True,
    help="Reason for acknowledgement (audit trail)",
)
@click.option(
    "--reading",
    "-i",
    default=0,
    type=int,
    help="Reading index to acknowledge (default: 0 = spine reading)",
)
@click.option(
    "--session-id",
    default="cli-default",
    help="Session ID for tracking (default: cli-default)",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def gates_acknowledge(
    reference: str,
    reason: str,
    reading: int,
    session_id: str,
    as_json: bool,
):
    """Acknowledge a variant gate without translating.

    Records acknowledgement for audit trail. Use this when you've reviewed
    a variant and want to record your decision before translation.

    Examples:
        redletters gates acknowledge "John 1:1" --reason "Reviewed, prefer SBLGNT"
        redletters gates acknowledge "John.1.18" -r "WH reading preferred" -i 1
        redletters gates acknowledge "John 1:1" --reason "Variant reviewed" --session-id my-session
    """
    from redletters.gates.state import AcknowledgementStore

    conn = get_connection(settings.db_path)

    # Normalize reference format (support both "John 1:1" and "John.1.1")
    ref_normalized = reference.replace(" ", ".").replace(":", ".")

    # Initialize acknowledgement store
    store = AcknowledgementStore(conn)
    store.init_schema()

    # Load or create session state
    state = store.load_session_state(session_id)

    # Record the acknowledgement
    ack = state.acknowledge_variant(
        ref=ref_normalized,
        reading_chosen=reading,
        context=f"gates acknowledge CLI: {reason}",
        notes=reason,
    )

    # Persist to database
    ack_id = store.persist_variant_ack(ack)

    conn.close()

    if as_json:
        import json as json_lib

        output = {
            "acknowledged": True,
            "id": ack_id,
            "reference": ref_normalized,
            "reading_index": reading,
            "reason": reason,
            "session_id": session_id,
            "timestamp": ack.timestamp.isoformat(),
        }
        console.print(json_lib.dumps(output, indent=2, ensure_ascii=False))
    else:
        console.print("[green]✓ Gate acknowledged[/green]")
        console.print(f"  Reference: {ref_normalized}")
        console.print(f"  Reading: {reading}")
        console.print(f"  Reason: {reason}")
        console.print(f"  Session: {session_id}")


@gates.command("list")
@click.option(
    "--session-id",
    default="cli-default",
    help="Session ID to query (default: cli-default)",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def gates_list(session_id: str, as_json: bool):
    """List acknowledged gates for a session.

    Examples:
        redletters gates list
        redletters gates list --session-id my-session --json
    """
    from redletters.gates.state import AcknowledgementStore

    conn = get_connection(settings.db_path)

    store = AcknowledgementStore(conn)
    store.init_schema()

    state = store.load_session_state(session_id)

    conn.close()

    if as_json:
        import json as json_lib

        acks = [ack.to_dict() for ack in state.acknowledged_variants.values()]
        console.print(json_lib.dumps(acks, indent=2, ensure_ascii=False))
    else:
        if not state.acknowledged_variants:
            console.print(f"[dim]No acknowledged gates for session: {session_id}[/dim]")
            return

        table = Table(title=f"Acknowledged Gates (session: {session_id})")
        table.add_column("Reference", style="cyan")
        table.add_column("Reading", justify="center")
        table.add_column("Timestamp")
        table.add_column("Notes")

        for ref, ack in sorted(state.acknowledged_variants.items()):
            table.add_row(
                ref,
                str(ack.reading_chosen),
                ack.timestamp.strftime("%Y-%m-%d %H:%M"),
                ack.notes or "",
            )

        console.print(table)


@gates.command("pending")
@click.argument("reference")
@click.option(
    "--session-id",
    default="cli-default",
    help="Session ID to check against",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def gates_pending(reference: str, session_id: str, as_json: bool):
    """Show pending (unacknowledged) gates for a reference.

    Lists variants that require acknowledgement before translation can proceed.

    Examples:
        redletters gates pending "John 1"
        redletters gates pending "John.1.18" --json
    """
    from redletters.variants.store import VariantStore
    from redletters.gates.state import AcknowledgementStore

    conn = get_connection(settings.db_path)

    # Load variant store
    var_store = VariantStore(conn)
    var_store.init_schema()

    # Load acknowledgement state
    ack_store = AcknowledgementStore(conn)
    ack_store.init_schema()
    state = ack_store.load_session_state(session_id)

    # Get all variants for reference
    ref_normalized = reference.replace(" ", ".").replace(":", ".")

    # Determine if this is a verse, chapter, or book reference
    parts = ref_normalized.split(".")
    if len(parts) >= 3:
        # Verse reference (e.g., "John.1.1")
        variants = var_store.get_variants_for_verse(ref_normalized)
    elif len(parts) == 2:
        # Chapter reference (e.g., "John.1")
        variants = var_store.get_significant_variants(
            book=parts[0], chapter=int(parts[1])
        )
    else:
        # Book reference (e.g., "John")
        variants = var_store.get_significant_variants(book=parts[0])

    # Filter to unacknowledged significant variants (significant or major)
    from redletters.variants.models import SignificanceLevel

    pending = []
    for v in variants:
        if v.significance in (SignificanceLevel.SIGNIFICANT, SignificanceLevel.MAJOR):
            if not state.has_acknowledged_variant(v.ref):
                pending.append(v)

    conn.close()

    if as_json:
        import json as json_lib

        output = {
            "reference": ref_normalized,
            "session_id": session_id,
            "pending_count": len(pending),
            "pending": [
                {
                    "variant_ref": p.ref,
                    "significance": p.significance.value,
                    "spine_reading": p.sblgnt_reading.surface_text
                    if p.sblgnt_reading
                    else "",
                    "readings_count": len(p.readings) if p.readings else 0,
                }
                for p in pending
            ],
        }
        console.print(json_lib.dumps(output, indent=2, ensure_ascii=False))
    else:
        if not pending:
            console.print(
                f"[green]✓ No pending gates for {ref_normalized}[/green] (session: {session_id})"
            )
            return

        console.print(f"[yellow]Pending gates for {ref_normalized}:[/yellow]")
        for p in pending:
            spine_text = p.sblgnt_reading.surface_text if p.sblgnt_reading else "?"
            console.print(
                f"  [yellow]?[/yellow] {p.ref} ({p.significance.value}): {spine_text}"
            )

        console.print("\n[dim]To acknowledge, use:[/dim]")
        for p in pending:
            console.print(
                f'  redletters gates acknowledge "{p.ref}" --reason "<your reason>"'
            )


# ============================================================================
# Quote command (v0.9.0 - Quote friction)
# ============================================================================


@cli.command()
@click.argument("reference")
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["readable", "traceable"]),
    default="readable",
    help="Output mode for quote",
)
@click.option(
    "--out",
    "-o",
    "output_path",
    type=click.Path(),
    help="Output JSON file path (optional; prints to stdout if not provided)",
)
@click.option(
    "--session-id",
    default="cli-default",
    help="Session ID for gate acknowledgement checking",
)
@click.option(
    "--force",
    is_flag=True,
    help="Generate quote even with pending gates (marks forced_responsibility)",
)
@click.option(
    "--data-root",
    type=click.Path(),
    help="Override data root for installed sources",
)
def quote(
    reference: str,
    mode: str,
    output_path: str | None,
    session_id: str,
    force: bool,
    data_root: str | None,
):
    """Generate a citeable quote for a reference (v0.9.0).

    Produces structured JSON intended for citation/quoting with:
    - Reference and mode
    - Spine text
    - Confidence bucket summary
    - Provenance (packs used)
    - Gate status

    GATE FRICTION: Fails with PendingGatesError unless gates are cleared
    or --force is used. If forced, marks forced_responsibility: true.

    Example:
        redletters quote "John 1:1" --out out/quote.json
        redletters quote "John 1:1" --force --out out/quote.json
    """
    from datetime import datetime, timezone
    from redletters.export.apparatus import check_pending_gates
    from redletters.export import PendingGatesError
    from redletters.export.schema_versions import QUOTE_SCHEMA_VERSION
    from redletters.sources.installer import SourceInstaller
    from redletters.variants.store import VariantStore

    # Set up data root
    if data_root:
        data_root_path = Path(data_root)
    else:
        data_root_path = Path.home() / ".redletters" / "data"

    # Get database connection
    db_path = data_root_path / "redletters.db"
    if not db_path.exists():
        console.print(
            "[red]Error: Database not found. Run 'redletters init' first.[/red]"
        )
        sys.exit(1)

    conn = get_connection(db_path)

    # Initialize stores
    variant_store = VariantStore(conn)

    # Normalize reference
    ref_normalized = reference.replace(" ", ".").replace(":", ".")
    parts = ref_normalized.split(".")
    if len(parts) < 3:
        console.print(
            "[red]Error: Reference must be in format Book.Chapter.Verse[/red]"
        )
        sys.exit(1)

    # Check for pending gates (gate friction)
    pending_gates = check_pending_gates(conn, reference, session_id, variant_store)

    if pending_gates and not force:
        # Fail with gate friction
        error = PendingGatesError(
            reference=reference,
            session_id=session_id,
            pending_gates=pending_gates,
        )
        console.print(f"[red]Error: {error}[/red]")
        console.print("\n[yellow]Pending gates:[/yellow]")
        for gate in pending_gates:
            console.print(
                f"  - {gate.variant_ref} ({gate.significance}): "
                f"{gate.spine_reading} ({gate.readings_count} readings)"
            )
        console.print(
            "\n[dim]Use --force to generate quote with forced_responsibility marked.[/dim]"
        )
        sys.exit(1)

    # Get spine text (SBLGNT)
    installer = SourceInstaller(data_root=data_root_path)
    spine_text = ""

    if installer.is_installed("morphgnt-sblgnt"):
        try:
            from redletters.sources.spine import SpineLoader

            spine_path = data_root_path / "sources" / "morphgnt-sblgnt"
            loader = SpineLoader(spine_path)
            tokens = loader.get_tokens_for_verse(ref_normalized)
            if tokens:
                spine_text = " ".join(t.get("surface", "") for t in tokens)
        except Exception:
            pass

    # Get provenance (installed packs)
    installed_packs = []
    try:
        from redletters.sources.catalog import list_sources

        for source in list_sources():
            if installer.is_installed(source.source_id):
                installed_packs.append(source.source_id)
    except Exception:
        pass

    # Determine gates_cleared (based on pending gates check above)
    gates_cleared = len(pending_gates) == 0
    forced_responsibility = force and len(pending_gates) > 0

    # Build quote output
    quote_output = {
        "reference": reference,
        "reference_normalized": ref_normalized,
        "mode": mode,
        "spine_text": spine_text,
        "provenance": {
            "packs_used": installed_packs,
            "session_id": session_id,
        },
        "gate_status": {
            "gates_cleared": gates_cleared,
            "forced_responsibility": forced_responsibility,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": QUOTE_SCHEMA_VERSION,  # v0.10.0: centralized
    }

    # If forced with pending gates, include them
    if forced_responsibility:
        quote_output["gate_status"]["pending_gates"] = [
            {
                "variant_ref": g.variant_ref,
                "significance": g.significance,
                "spine_reading": g.spine_reading,
                "readings_count": g.readings_count,
            }
            for g in pending_gates
        ]

    # Get confidence summary (aggregate across variants in scope)
    variants = variant_store.get_variants_for_verse(ref_normalized)
    if variants:
        # Count significance levels
        sig_counts = {"trivial": 0, "minor": 0, "significant": 0, "major": 0}
        for v in variants:
            sig_counts[v.significance.value] = (
                sig_counts.get(v.significance.value, 0) + 1
            )
        quote_output["confidence_summary"] = {
            "variants_in_scope": len(variants),
            "significance_breakdown": sig_counts,
        }
    else:
        quote_output["confidence_summary"] = {
            "variants_in_scope": 0,
            "significance_breakdown": {},
        }

    conn.close()

    # Output
    output_json = json.dumps(quote_output, indent=2, ensure_ascii=False)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(output_json, encoding="utf-8")
        if forced_responsibility:
            console.print(
                "[yellow]⚠ Quote generated with forced_responsibility=true[/yellow]"
            )
            console.print(
                f"[yellow]  {len(pending_gates)} pending gate(s) were bypassed[/yellow]"
            )
        else:
            console.print(f"[green]✓ Quote generated: {output_path}[/green]")
    else:
        console.print(output_json)


# ============================================================================
# Export commands (v0.5.0 - Reproducible Scholar Exports)
# ============================================================================


@cli.group()
def export():
    """Export datasets for scholarly reproducibility."""
    pass


@export.command("apparatus")
@click.argument("reference")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["jsonl"]),
    default="jsonl",
    help="Output format (default: jsonl)",
)
@click.option(
    "--out",
    "-o",
    "output_path",
    type=click.Path(),
    required=True,
    help="Output file path",
)
@click.option(
    "--session-id",
    default="cli-default",
    help="Session ID for gate checking (v0.8.0)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Export even with pending gates (records them in metadata)",
)
def export_apparatus(
    reference: str,
    output_format: str,
    output_path: str,
    session_id: str,
    force: bool,
):
    """Export variant apparatus dataset.

    Exports variant units with readings, support sets, and provenance
    in JSONL format for scholarly analysis.

    v0.8.0: Export now checks for pending gates. If unacknowledged significant
    variants exist, export is blocked unless --force is used.

    Each line contains one variant unit with:
    - Stable variant_unit_id and reading_id
    - All readings with normalized text
    - Support entries with witness details
    - Provenance (source packs)
    - Gate requirements

    Examples:
        redletters export apparatus "John 1:1-18" --out apparatus.jsonl
        redletters export apparatus "John.1" --out john1_apparatus.jsonl
        redletters export apparatus "John.1.18" --out test.jsonl --force
    """
    from redletters.variants.store import VariantStore
    from redletters.export.apparatus import ApparatusExporter, check_pending_gates

    conn = get_connection(settings.db_path)

    try:
        store = VariantStore(conn)
        store.init_schema()
    except Exception:
        pass

    # v0.8.0: Check for pending gates
    pending = check_pending_gates(conn, reference, session_id, store)
    forced_export = False
    pending_gates_at_export = []

    if pending and not force:
        # Block export
        conn.close()
        console.print("[yellow]Export blocked: pending gates[/yellow]")
        console.print(f"  Reference: {reference}")
        console.print(f"  Session: {session_id}")
        console.print(f"  Pending: {len(pending)}")
        for p in pending[:5]:
            console.print(f"    - {p.variant_ref} ({p.significance})")
        if len(pending) > 5:
            console.print(f"    ... and {len(pending) - 5} more")
        console.print("\n[dim]To acknowledge gates:[/dim]")
        console.print(f'  redletters gates acknowledge "<ref>" --session {session_id}')
        console.print("\n[dim]To force export anyway:[/dim]")
        console.print(
            f'  redletters export apparatus "{reference}" --out {output_path} --force'
        )
        sys.exit(2)
    elif pending and force:
        forced_export = True
        pending_gates_at_export = [
            {"variant_ref": p.variant_ref, "significance": p.significance}
            for p in pending
        ]
        console.print(
            f"[yellow]Warning: Exporting with {len(pending)} pending gate(s)[/yellow]"
        )

    exporter = ApparatusExporter(store)

    try:
        result = exporter.export_to_file(reference, output_path)

        # Add force metadata if applicable
        if forced_export:
            result["forced_export"] = True
            result["pending_gates_at_export"] = pending_gates_at_export

        conn.close()

        console.print("[green]✓ Apparatus exported[/green]")
        console.print(f"  Reference: {result['reference']}")
        console.print(f"  Rows: {result['row_count']}")
        console.print(f"  Output: {result['output_path']}")
        console.print(f"  Schema: {result['schema_version']}")
        if forced_export:
            console.print(
                f"  [yellow]Forced: {len(pending_gates_at_export)} pending gates[/yellow]"
            )
    except Exception as e:
        conn.close()
        console.print(f"[red]✗ Export failed: {e}[/red]")
        sys.exit(1)


@export.command("translation")
@click.argument("reference")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["jsonl"]),
    default="jsonl",
    help="Output format (default: jsonl)",
)
@click.option(
    "--out",
    "-o",
    "output_path",
    type=click.Path(),
    required=True,
    help="Output file path",
)
@click.option(
    "--data-root",
    type=click.Path(),
    help="Override data root for installed sources",
)
@click.option(
    "--session-id",
    default="export",
    help="Session ID for gate checking (v0.8.0)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Export even with pending gates (records them in metadata)",
)
def export_translation(
    reference: str,
    output_format: str,
    output_path: str,
    data_root: str | None,
    session_id: str,
    force: bool,
):
    """Export translation dataset with token ledger.

    Runs traceable translation and exports token-level data
    in JSONL format for scholarly analysis.

    v0.8.0: Export now checks for pending gates. If unacknowledged significant
    variants exist, export is blocked unless --force is used.

    Each line contains one verse with:
    - Token-level ledger (surface, lemma, morph, gloss)
    - Confidence scores (T/G/L/I layers)
    - Provenance (spine + comparative sources)

    Examples:
        redletters export translation "John 1:1-18" --out translation.jsonl
        redletters export translation "John.1.18" --out j118_translation.jsonl
        redletters export translation "John.1.18" --out test.jsonl --force
    """
    from redletters.pipeline import translate_passage, get_translator
    from redletters.sources import SourceInstaller, InstalledSpineProvider
    from redletters.export.translation import TranslationExporter
    from redletters.export.apparatus import check_pending_gates
    from redletters.variants.store import VariantStore

    conn = get_connection(settings.db_path)

    # Get spine provider
    installer = SourceInstaller(data_root=data_root)
    spine_provider = None
    source_id = ""
    source_license = ""

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
        console.print("[dim]Run: redletters sources install morphgnt-sblgnt[/dim]")
        conn.close()
        sys.exit(1)

    # v0.8.0: Check for pending gates
    var_store = VariantStore(conn)
    var_store.init_schema()
    pending = check_pending_gates(conn, reference, session_id, var_store)
    forced_export = False
    pending_gates_at_export = []

    if pending and not force:
        # Block export
        conn.close()
        console.print("[yellow]Export blocked: pending gates[/yellow]")
        console.print(f"  Reference: {reference}")
        console.print(f"  Session: {session_id}")
        console.print(f"  Pending: {len(pending)}")
        for p in pending[:5]:
            console.print(f"    - {p.variant_ref} ({p.significance})")
        if len(pending) > 5:
            console.print(f"    ... and {len(pending) - 5} more")
        console.print("\n[dim]To acknowledge gates:[/dim]")
        console.print(f'  redletters gates acknowledge "<ref>" --session {session_id}')
        console.print("\n[dim]To force export anyway:[/dim]")
        console.print(
            f'  redletters export translation "{reference}" --out {output_path} --force'
        )
        sys.exit(2)
    elif pending and force:
        forced_export = True
        pending_gates_at_export = [
            {"variant_ref": p.variant_ref, "significance": p.significance}
            for p in pending
        ]
        console.print(
            f"[yellow]Warning: Exporting with {len(pending)} pending gate(s)[/yellow]"
        )

    # Get traceable translator
    translator = get_translator(
        translator_type="traceable",
        source_id=source_id,
        source_license=source_license,
    )

    # Build options
    options = {"spine_provider": spine_provider}

    try:
        # Run translation
        result = translate_passage(
            conn=conn,
            reference=reference,
            mode="traceable",
            session_id=session_id,
            options=options,
            translator=translator,
        )

        conn.close()

        # Check if we got a gate response instead of translation
        from redletters.pipeline import GateResponsePayload

        if isinstance(result, GateResponsePayload):
            if not force:
                console.print("[yellow]Export blocked: gate required[/yellow]")
                console.print(f"  {result.message}")
                console.print("\n[dim]To force export anyway:[/dim]")
                console.print(
                    f'  redletters export translation "{reference}" --out {output_path} --force'
                )
                sys.exit(2)
            else:
                console.print(
                    "[yellow]Warning: Gate required - exporting empty ledger[/yellow]"
                )
                console.print(f"  {result.message}")

                # Export empty ledger with warning
                exporter = TranslationExporter()
                export_result = exporter.export_to_file([], output_path, reference)
                export_result["forced_export"] = True
                export_result["gate_message"] = result.message

                console.print("[yellow]Translation exported (no ledger data)[/yellow]")
                console.print(f"  Reference: {reference}")
                console.print(f"  Rows: {export_result['row_count']}")
                console.print(f"  Output: {export_result['output_path']}")
                return

        # Extract ledger data
        result_dict = result.to_dict()
        ledger_data = TranslationExporter.from_translate_response(result_dict)

        # Export
        exporter = TranslationExporter()
        export_result = exporter.export_to_file(ledger_data, output_path, reference)

        # Add force metadata if applicable
        if forced_export:
            export_result["forced_export"] = True
            export_result["pending_gates_at_export"] = pending_gates_at_export

        console.print("[green]✓ Translation exported[/green]")
        console.print(f"  Reference: {export_result['reference']}")
        console.print(f"  Rows: {export_result['row_count']}")
        console.print(f"  Output: {export_result['output_path']}")
        console.print(f"  Schema: {export_result['schema_version']}")
        if forced_export:
            console.print(
                f"  [yellow]Forced: {len(pending_gates_at_export)} pending gates[/yellow]"
            )

    except Exception as e:
        conn.close()
        console.print(f"[red]✗ Export failed: {e}[/red]")
        sys.exit(1)


@export.command("snapshot")
@click.option(
    "--out",
    "-o",
    "output_path",
    type=click.Path(),
    required=True,
    help="Output file path",
)
@click.option(
    "--inputs",
    "-i",
    "input_files",
    multiple=True,
    help="Export files to include in hash verification (can be repeated)",
)
@click.option(
    "--include-citations",
    is_flag=True,
    help="Auto-generate and include citations.json in snapshot",
)
@click.option(
    "--data-root",
    type=click.Path(),
    help="Override data root for installed sources",
)
def export_snapshot(
    output_path: str,
    input_files: tuple[str, ...],
    include_citations: bool,
    data_root: str | None,
):
    """Generate reproducibility snapshot.

    Creates a JSON file containing:
    - Tool version and schema version
    - Git commit (if available)
    - Installed pack metadata (IDs, versions, licenses, hashes)
    - Export file hashes for verification

    Examples:
        redletters export snapshot --out snapshot.json
        redletters export snapshot --out snapshot.json -i apparatus.jsonl -i translation.jsonl
        redletters export snapshot --out snapshot.json --include-citations
    """
    from pathlib import Path as PathLib

    from redletters.export.snapshot import SnapshotGenerator

    generator = SnapshotGenerator(data_root=data_root)

    # Flatten comma-separated inputs
    all_inputs = []
    for inp in input_files:
        all_inputs.extend([i.strip() for i in inp.split(",") if i.strip()])

    citations_path = None
    try:
        # Auto-generate citations if requested
        if include_citations:
            from redletters.export.citations import CitationsExporter

            # Generate citations file alongside snapshot
            output_dir = PathLib(output_path).parent
            citations_path = output_dir / "citations.json"

            # Get database connection for sense packs
            conn = get_connection(settings.db_path)
            exporter = CitationsExporter(conn=conn, data_root=data_root)
            citations_result = exporter.export_to_file(citations_path, format="csljson")
            conn.close()

            console.print("[green]✓ Citations exported[/green]")
            console.print(f"  Entries: {citations_result['entries_count']}")
            console.print(f"  Hash: {citations_result['content_hash'][:16]}...")

            # Add citations file to inputs
            all_inputs.append(str(citations_path))

        snapshot = generator.save(output_path, export_files=all_inputs or None)

        console.print("[green]✓ Snapshot created[/green]")
        console.print(f"  Tool version: {snapshot.tool_version}")
        console.print(f"  Schema version: {snapshot.schema_version}")
        console.print(f"  Git commit: {snapshot.git_commit or '(not in git repo)'}")
        console.print(f"  Packs: {len(snapshot.packs)}")
        for p in snapshot.packs:
            console.print(f"    - {p.pack_id} ({p.version}, {p.license})")
        if snapshot.export_hashes:
            console.print(f"  Export hashes: {len(snapshot.export_hashes)}")
            for fname, fhash in snapshot.export_hashes.items():
                console.print(f"    - {fname}: {fhash[:16]}...")
        console.print(f"  Output: {output_path}")

    except Exception as e:
        console.print(f"[red]✗ Snapshot failed: {e}[/red]")
        sys.exit(1)


@export.command("verify")
@click.option(
    "--snapshot",
    "-s",
    "snapshot_path",
    type=click.Path(exists=True),
    required=True,
    help="Snapshot file to verify against",
)
@click.option(
    "--inputs",
    "-i",
    "input_files",
    required=True,
    help="Export files to verify (comma-separated or repeated)",
)
def export_verify(snapshot_path: str, input_files: str):
    """Verify export files against snapshot.

    Recomputes hashes of input files and compares against
    hashes recorded in the snapshot. Returns non-zero exit
    code if verification fails.

    Examples:
        redletters export verify --snapshot snapshot.json --inputs apparatus.jsonl,translation.jsonl
        redletters export verify -s snapshot.json -i apparatus.jsonl -i translation.jsonl
    """
    from redletters.export.snapshot import SnapshotVerifier

    verifier = SnapshotVerifier()

    # Parse input files (comma-separated)
    all_inputs = [i.strip() for i in input_files.split(",") if i.strip()]

    try:
        result = verifier.verify(snapshot_path, all_inputs)

        if result.valid:
            console.print("[green]✓ Verification passed[/green]")
        else:
            console.print("[red]✗ Verification failed[/red]")

        # Show file hashes
        if result.file_hashes:
            console.print("\n[bold]File hashes:[/bold]")
            for fname, info in result.file_hashes.items():
                if info.get("match") is True:
                    status = "[green]✓[/green]"
                elif info.get("match") is False:
                    status = "[red]✗[/red]"
                else:
                    status = "[yellow]?[/yellow]"

                console.print(f"  {status} {fname}")
                if info.get("expected"):
                    console.print(f"      Expected: {info['expected'][:32]}...")
                console.print(f"      Actual:   {info['current'][:32]}...")

        # Show warnings
        if result.warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for w in result.warnings:
                console.print(f"  [yellow]⚠[/yellow] {w}")

        # Show errors
        if result.errors:
            console.print("\n[red]Errors:[/red]")
            for e in result.errors:
                console.print(f"  [red]✗[/red] {e}")

        if not result.valid:
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]✗ Verification failed: {e}[/red]")
        sys.exit(1)


@export.command("citations")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["csljson", "full"]),
    default="csljson",
    help="Output format: csljson (standard) or full (with metadata)",
)
@click.option(
    "--out",
    "-o",
    "output_path",
    type=click.Path(),
    required=True,
    help="Output file path",
)
@click.option(
    "--data-root",
    type=click.Path(),
    help="Override data root for installed sources",
)
def export_citations(output_format: str, output_path: str, data_root: str | None):
    """Export bibliography of all installed packs.

    Creates a CSL-JSON file containing bibliographic metadata for
    all installed packs (spine, comparative, sense packs).

    CSL-JSON is the standard format for citation managers (Zotero,
    Mendeley, etc.) and can be imported directly.

    Output includes:
    - source_id, title, edition, publisher, year
    - License information
    - Pack role and version

    Deterministic: same packs = identical output.

    Examples:
        redletters export citations --out citations.json
        redletters export citations --format full --out citations_full.json
    """
    from redletters.export.citations import CitationsExporter

    conn = get_connection(settings.db_path)

    try:
        exporter = CitationsExporter(conn=conn, data_root=data_root)
        result = exporter.export_to_file(output_path, format=output_format)
        conn.close()

        console.print("[green]✓ Citations exported[/green]")
        console.print(f"  Format: {result['format']}")
        console.print(f"  Entries: {result['entries_count']}")
        console.print(f"  Schema: {result['schema_version']}")
        console.print(f"  Hash: {result['content_hash'][:16]}...")
        console.print(f"  Output: {result['output_path']}")

    except Exception as e:
        conn.close()
        console.print(f"[red]✗ Export failed: {e}[/red]")
        sys.exit(1)


# ============================================================================
# Validate commands (v0.10.0 - Schema Contracts + Validation)
# ============================================================================


@cli.group()
def validate():
    """Validate generated outputs against schema contracts."""
    pass


@validate.command("output")
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--type",
    "-t",
    "artifact_type",
    type=click.Choice(
        [
            "apparatus",
            "translation",
            "snapshot",
            "citations",
            "quote",
            "dossier",
            "auto",
        ]
    ),
    default="auto",
    help="Artifact type (auto-detect if not specified)",
)
@click.option("--json", "as_json", is_flag=True, help="Output result as JSON")
def validate_output_cmd(file_path: str, artifact_type: str, as_json: bool):
    """Validate a generated output file against its schema.

    Performs deterministic validation with stable error messages.
    No network calls.

    Validates:
    - Required fields present
    - Schema version format
    - Artifact-specific structure (readings, tokens, etc.)

    Returns exit code 0 if valid, 1 if invalid.

    Examples:
        redletters validate output out/apparatus.jsonl
        redletters validate output out/snapshot.json --type snapshot
        redletters validate output out/quote.json --json
    """
    from redletters.export.validator import validate_output

    # Handle auto-detect
    type_arg = None if artifact_type == "auto" else artifact_type

    result = validate_output(file_path, artifact_type=type_arg)

    if as_json:
        import json

        console.print(json.dumps(result.to_dict(), indent=2))
    else:
        # Pretty output
        if result.valid:
            console.print(f"[green]✓ Valid {result.artifact_type}[/green]")
            console.print(f"  File: {result.file_path}")
            console.print(f"  Records: {result.records_checked}")
            if result.schema_version_found:
                console.print(f"  Schema: {result.schema_version_found}")
            if result.warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for w in result.warnings:
                    console.print(f"  - {w}")
        else:
            console.print(f"[red]✗ Invalid {result.artifact_type}[/red]")
            console.print(f"  File: {result.file_path}")
            console.print("\n[red]Errors:[/red]")
            for e in result.errors:
                console.print(f"  - {e}")
            if result.warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for w in result.warnings:
                    console.print(f"  - {w}")

    sys.exit(0 if result.valid else 1)


@validate.command("schemas")
def validate_schemas_cmd():
    """List all schema versions and their artifact types.

    Shows the current schema version for each artifact type.
    Useful for understanding compatibility and planning migrations.
    """
    from redletters.export.schema_versions import get_all_schema_versions

    versions = get_all_schema_versions()

    console.print("\n[bold]Schema Versions[/bold]\n")
    for artifact, version in sorted(versions.items()):
        console.print(f"  {artifact:<20} {version}")
    console.print()


# ============================================================================
# Senses commands (v0.7.0 - Pack Explainability)
# ============================================================================


@cli.group()
def senses():
    """Explain sense resolution and detect conflicts across packs."""
    pass


@senses.command("explain")
@click.argument("lemma")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def senses_explain(lemma: str, as_json: bool):
    """Explain why a specific sense was chosen for a lemma.

    Shows deterministic audit trail:
    - Normalized lemma key used for lookup
    - Packs consulted in precedence order
    - All matches found across packs
    - Chosen sense with full citation fields

    Examples:
        redletters senses explain μετανοέω
        redletters senses explain "λόγος" --json
    """
    from redletters.senses.explain import SenseExplainer

    conn = get_connection(settings.db_path)

    try:
        explainer = SenseExplainer(conn)
        result = explainer.explain(lemma)
        conn.close()

        if as_json:
            import json as json_lib

            console.print(
                json_lib.dumps(result.to_dict(), indent=2, ensure_ascii=False)
            )
            return

        # Pretty print
        console.print(
            Panel(
                f"[bold]Input:[/bold] {result.lemma_input}\n"
                f"[bold]Normalized:[/bold] {result.lemma_normalized}",
                title="Sense Resolution",
            )
        )

        console.print(f"\n[bold]Packs consulted:[/bold] {len(result.packs_consulted)}")
        for pack_id in result.packs_consulted:
            console.print(f"  • {pack_id}")

        console.print(f"\n[bold]Matches found:[/bold] {len(result.matches)}")
        for i, match in enumerate(result.matches):
            is_chosen = result.chosen and match == result.chosen
            marker = "[green]→[/green]" if is_chosen else " "
            console.print(
                f"  {marker} [{match.pack_id}] {match.gloss} "
                f"(weight={match.weight:.2f}, sense={match.sense_id})"
            )
            console.print(f"      Source: {match.source_id} - {match.source_title}")

        console.print(f"\n[bold]Reason:[/bold] {result.reason}")

        if result.chosen:
            console.print("\n[bold green]✓ Chosen sense:[/bold green]")
            console.print(f"  Gloss: {result.chosen.gloss}")
            console.print(
                f"  Pack: {result.chosen.pack_id}@{result.chosen.pack_version}"
            )
            console.print(f"  Citation: {result.chosen.citation_string()}")
        else:
            console.print("\n[yellow]⚠ No matching sense found[/yellow]")

    except Exception as e:
        conn.close()
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


@senses.command("conflicts")
@click.argument("lemma")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def senses_conflicts(lemma: str, as_json: bool):
    """Show all senses for a lemma across installed packs.

    Detects where packs agree or disagree on glosses:
    - Lists all sense entries from all packs
    - Shows pack_id@version for each entry
    - Highlights conflicts when primary glosses differ

    Examples:
        redletters senses conflicts λόγος
        redletters senses conflicts "πίστις" --json
    """
    from redletters.senses.conflicts import SenseConflictDetector

    conn = get_connection(settings.db_path)

    try:
        detector = SenseConflictDetector(conn)
        result = detector.detect(lemma)
        conn.close()

        if as_json:
            import json as json_lib

            console.print(
                json_lib.dumps(result.to_dict(), indent=2, ensure_ascii=False)
            )
            return

        # Pretty print
        console.print(
            Panel(
                f"[bold]Input:[/bold] {result.lemma_input}\n"
                f"[bold]Normalized:[/bold] {result.lemma_normalized}",
                title="Sense Conflicts",
            )
        )

        console.print(f"\n[bold]Packs checked:[/bold] {len(result.packs_checked)}")
        console.print(
            f"[bold]Packs with matches:[/bold] {len(result.packs_with_matches)}"
        )

        if result.has_conflict:
            console.print("\n[red bold]⚠ CONFLICT DETECTED[/red bold]")
        else:
            console.print("\n[green]✓ No conflict[/green]")

        console.print(f"[dim]{result.conflict_summary}[/dim]")

        if result.entries:
            console.print(f"\n[bold]All entries ({len(result.entries)}):[/bold]")

            table = Table()
            table.add_column("Pack", style="cyan")
            table.add_column("Version")
            table.add_column("Gloss", style="green")
            table.add_column("Weight")
            table.add_column("Source ID")

            for entry in result.entries:
                table.add_row(
                    entry.pack_id,
                    entry.pack_version,
                    entry.gloss,
                    f"{entry.weight:.2f}",
                    entry.source_id,
                )

            console.print(table)

            console.print(
                f"\n[bold]Unique glosses:[/bold] {', '.join(result.unique_glosses)}"
            )

    except Exception as e:
        conn.close()
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


@senses.command("list-packs")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def senses_list_packs(as_json: bool):
    """List installed sense packs in precedence order.

    Shows sense packs with their priority (lower = higher precedence),
    source citation info, and sense count.

    Examples:
        redletters senses list-packs
        redletters senses list-packs --json
    """
    from redletters.senses.conflicts import SenseConflictDetector

    conn = get_connection(settings.db_path)

    try:
        detector = SenseConflictDetector(conn)
        packs = detector.list_packs()
        conn.close()

        if as_json:
            import json as json_lib

            console.print(json_lib.dumps(packs, indent=2, ensure_ascii=False))
            return

        if not packs:
            console.print("[dim]No sense packs installed[/dim]")
            console.print(
                "[dim]Install a sense pack with: redletters sources install <pack>[/dim]"
            )
            return

        table = Table(title="Installed Sense Packs (Precedence Order)")
        table.add_column("Priority", justify="right")
        table.add_column("Pack ID", style="cyan")
        table.add_column("Version")
        table.add_column("Source ID", style="yellow")
        table.add_column("Senses", justify="right")
        table.add_column("License")

        for pack in packs:
            table.add_row(
                str(pack["priority"]),
                pack["pack_id"],
                pack["version"],
                pack["source_id"],
                str(pack["sense_count"]),
                pack["license"],
            )

        console.print(table)
        console.print(
            "\n[dim]Lower priority number = consulted first for sense resolution[/dim]"
        )

    except Exception as e:
        conn.close()
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


# v0.8.0: Claims analyzer CLI group
@cli.group()
def claims():
    """Analyze theological claims for textual uncertainty (v0.8.0)."""
    pass


@claims.command("analyze")
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--session-id", "-s", default="default", help="Session ID for gate checks"
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--out", "-o", type=click.Path(), help="Output file path")
def claims_analyze(input_file: str, session_id: str, as_json: bool, out: str | None):
    """Analyze claims file for textual uncertainty.

    Reads a JSON file containing theological claims with scripture dependencies
    and reports where textual uncertainty exists.

    Input format:
    {
        "claims": [
            {"label": "id", "text": "claim content", "dependencies": ["John.1.18"]}
        ]
    }

    Examples:
        redletters claims analyze claims.json
        redletters claims analyze claims.json --json
        redletters claims analyze claims.json --out results.json
    """
    from redletters.analysis import ClaimsAnalyzer
    from redletters.variants.store import VariantStore

    conn = get_connection(settings.db_path)
    variant_store = VariantStore(conn)
    variant_store.init_schema()

    try:
        # Load input file
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Analyze claims
        analyzer = ClaimsAnalyzer(conn, variant_store)
        results = analyzer.analyze_from_dict(data, session_id)

        # Build output
        output_data = {
            "input_file": str(input_file),
            "session_id": session_id,
            "claims_analyzed": len(results),
            "claims_with_uncertainty": sum(1 for r in results if r.has_uncertainty),
            "results": [r.to_dict() for r in results],
        }

        if out:
            Path(out).write_text(
                json.dumps(output_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            console.print(f"[green]✓ Output written to {out}[/green]")
        elif as_json:
            console.print(json.dumps(output_data, indent=2, ensure_ascii=False))
        else:
            # Pretty print
            console.print(
                Panel(
                    f"[bold]Claims analyzed:[/bold] {len(results)}\n"
                    f"[bold]With uncertainty:[/bold] {sum(1 for r in results if r.has_uncertainty)}",
                    title="Claims Analysis",
                )
            )

            for result in results:
                color = {
                    "high": "red",
                    "medium": "yellow",
                    "low": "blue",
                    "none": "green",
                }.get(result.uncertainty_score, "white")

                console.print(
                    f"\n[bold {color}]{result.label}[/bold {color}] "
                    f"(uncertainty: {result.uncertainty_score})"
                )
                console.print(f"  [dim]{result.text}[/dim]")

                if result.dependency_analyses:
                    console.print(f"  Dependencies ({result.dependencies_analyzed}):")
                    for dep in result.dependency_analyses:
                        status = "✓" if not dep.has_pending_gates else "!"
                        variant_info = ""
                        if dep.has_significant_variants:
                            variant_info = (
                                f" [{dep.significant_variant_count} variant(s)]"
                            )
                        console.print(f"    {status} {dep.reference}{variant_info}")

                if result.summary_notes:
                    console.print("  [dim]Notes:[/dim]")
                    for note in result.summary_notes:
                        console.print(f"    • {note}")

    except json.JSONDecodeError as e:
        console.print(f"[red]✗ Invalid JSON in input file: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)
    finally:
        conn.close()


# ============================================================================
# Bundle CLI Commands (v0.12.0)
# ============================================================================


@cli.group()
def bundle():
    """Research bundle operations for scholarly reproducibility."""
    pass


@bundle.command("create")
@click.option(
    "--out",
    "-o",
    required=True,
    type=click.Path(),
    help="Output directory for the bundle",
)
@click.option(
    "--lockfile",
    "-l",
    required=True,
    type=click.Path(exists=True),
    help="Path to lockfile.json",
)
@click.option(
    "--snapshot",
    "-s",
    required=True,
    type=click.Path(exists=True),
    help="Path to snapshot.json",
)
@click.option(
    "--inputs",
    "-i",
    multiple=True,
    required=True,
    type=click.Path(exists=True),
    help="Input artifact file(s) to include",
)
@click.option(
    "--include-schemas",
    is_flag=True,
    help="Include JSON schema files in bundle",
)
@click.option(
    "--zip",
    "create_zip",
    is_flag=True,
    help="Also create a zip archive of the bundle",
)
@click.option(
    "--notes",
    default="",
    help="Optional notes to include in manifest",
)
@click.option("--json", "as_json", is_flag=True, help="Output result as JSON")
def bundle_create(
    out: str,
    lockfile: str,
    snapshot: str,
    inputs: tuple[str, ...],
    include_schemas: bool,
    create_zip: bool,
    notes: str,
    as_json: bool,
):
    """Create a deterministic research bundle.

    Assembles a reproducible bundle containing lockfile, snapshot, and output
    artifacts with full integrity verification via SHA-256 hashes.

    Examples:
        redletters bundle create --out out/bundle -l lock.json -s snapshot.json -i apparatus.jsonl
        redletters bundle create -o out/bundle -l lock.json -s snap.json -i app.jsonl -i trans.jsonl --zip
        redletters bundle create -o out/bundle -l lock.json -s snap.json -i output.jsonl --include-schemas
    """
    from pathlib import Path as PathLib
    from redletters.export.bundle import BundleCreator

    output_dir = PathLib(out)
    lockfile_path = PathLib(lockfile)
    snapshot_path = PathLib(snapshot)
    input_paths = [PathLib(p) for p in inputs]

    creator = BundleCreator()
    result = creator.create(
        output_dir=output_dir,
        lockfile_path=lockfile_path,
        snapshot_path=snapshot_path,
        input_paths=input_paths,
        include_schemas=include_schemas,
        create_zip=create_zip,
        notes=notes,
    )

    if as_json:
        output_data = {
            "success": result.success,
            "bundle_path": str(result.bundle_path) if result.bundle_path else None,
            "manifest": result.manifest.to_dict() if result.manifest else None,
            "errors": result.errors,
            "warnings": result.warnings,
        }
        console.print(json.dumps(output_data, indent=2, ensure_ascii=False))
    else:
        if result.success:
            console.print(f"[green]✓ Bundle created: {result.bundle_path}[/green]")
            if result.manifest:
                console.print(f"  Artifacts: {len(result.manifest.artifacts)}")
                console.print(f"  Content hash: {result.manifest.content_hash[:16]}...")
            if create_zip:
                console.print(f"  Zip: {output_dir.with_suffix('.zip')}")
            for warning in result.warnings:
                console.print(f"  [yellow]⚠ {warning}[/yellow]")
        else:
            console.print("[red]✗ Bundle creation failed[/red]")
            for error in result.errors:
                console.print(f"  [red]{error}[/red]")
            sys.exit(1)


@bundle.command("verify")
@click.argument("bundle_path", type=click.Path(exists=True))
@click.option(
    "--check-snapshot/--no-check-snapshot",
    default=True,
    help="Verify snapshot file hashes",
)
@click.option(
    "--check-outputs/--no-check-outputs",
    default=True,
    help="Validate output files against schemas",
)
@click.option("--json", "as_json", is_flag=True, help="Output result as JSON")
def bundle_verify(
    bundle_path: str,
    check_snapshot: bool,
    check_outputs: bool,
    as_json: bool,
):
    """Verify a research bundle's integrity.

    Validates that all files in the bundle match their manifest hashes.
    Optionally verifies snapshot integrity and validates outputs against schemas.

    Exit code 0 if valid, 1 if invalid.

    Examples:
        redletters bundle verify out/bundle
        redletters bundle verify out/bundle.zip
        redletters bundle verify out/bundle --no-check-snapshot
        redletters bundle verify out/bundle --json
    """
    from pathlib import Path as PathLib
    from redletters.export.bundle import BundleVerifier

    verifier = BundleVerifier()
    result = verifier.verify(
        bundle_path=PathLib(bundle_path),
        check_snapshot=check_snapshot,
        check_outputs=check_outputs,
    )

    if as_json:
        console.print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        if result.valid:
            console.print("[green]✓ Bundle verified successfully[/green]")
            if result.manifest:
                console.print(f"  Artifacts checked: {len(result.manifest.artifacts)}")
                console.print(f"  Content hash: {result.manifest.content_hash[:16]}...")
            if result.snapshot_valid is not None:
                status = "✓" if result.snapshot_valid else "✗"
                console.print(f"  Snapshot integrity: {status}")
            if result.outputs_valid is not None:
                status = "✓" if result.outputs_valid else "✗"
                console.print(f"  Output validation: {status}")
            for warning in result.warnings:
                console.print(f"  [yellow]⚠ {warning}[/yellow]")
        else:
            console.print("[red]✗ Bundle verification failed[/red]")
            for error in result.errors:
                console.print(f"  [red]{error}[/red]")
            for warning in result.warnings:
                console.print(f"  [yellow]⚠ {warning}[/yellow]")
            sys.exit(1)


@bundle.command("inspect")
@click.argument("bundle_path", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def bundle_inspect(bundle_path: str, as_json: bool):
    """Inspect a research bundle's manifest.

    Shows the bundle manifest without performing full verification.

    Examples:
        redletters bundle inspect out/bundle
        redletters bundle inspect out/bundle --json
    """
    from pathlib import Path as PathLib
    from redletters.export.bundle import BundleManifest
    import zipfile

    bundle_dir = PathLib(bundle_path)

    # Handle zip
    if bundle_dir.suffix == ".zip":
        import tempfile

        temp_dir = PathLib(tempfile.mkdtemp())
        with zipfile.ZipFile(bundle_dir, "r") as zf:
            zf.extractall(temp_dir)
        bundle_dir = temp_dir

    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.exists():
        console.print("[red]✗ manifest.json not found in bundle[/red]")
        sys.exit(1)

    try:
        manifest = BundleManifest.load(manifest_path)
    except Exception as e:
        console.print(f"[red]✗ Failed to load manifest: {e}[/red]")
        sys.exit(1)

    if as_json:
        console.print(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False))
    else:
        console.print(Panel("[bold]Bundle Manifest[/bold]", title="Research Bundle"))
        console.print(f"  Tool version: {manifest.tool_version}")
        console.print(f"  Schema version: {manifest.schema_version}")
        console.print(f"  Created: {manifest.created_utc}")
        console.print(f"  Lockfile hash: {manifest.lockfile_hash[:16]}...")
        console.print(f"  Snapshot hash: {manifest.snapshot_hash[:16]}...")
        console.print(f"  Content hash: {manifest.content_hash[:16]}...")
        console.print(f"  Schemas included: {manifest.schemas_included}")
        if manifest.notes:
            console.print(f"  Notes: {manifest.notes}")

        console.print(f"\n  [bold]Artifacts ({len(manifest.artifacts)}):[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Path")
        table.add_column("Type")
        table.add_column("Schema Ver")
        table.add_column("SHA-256 (prefix)")

        for artifact in manifest.artifacts:
            table.add_row(
                artifact.path,
                artifact.artifact_type,
                artifact.schema_version or "-",
                artifact.sha256[:16] + "...",
            )

        console.print(table)


# ============================================================================
# Run CLI Commands (v0.13.0)
# ============================================================================


@cli.group()
def run():
    """End-to-end workflow execution commands."""
    pass


@run.command("scholarly")
@click.argument("reference")
@click.option(
    "--out",
    "-o",
    required=True,
    type=click.Path(),
    help="Output directory for all artifacts",
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["readable", "traceable"]),
    default="traceable",
    help="Translation mode (default: traceable)",
)
@click.option(
    "--include-schemas",
    is_flag=True,
    help="Include JSON schema files in bundle",
)
@click.option(
    "--zip",
    "create_zip",
    is_flag=True,
    help="Also create a zip archive of the bundle",
)
@click.option(
    "--force",
    is_flag=True,
    help="Proceed despite pending gates (records responsibility)",
)
@click.option(
    "--data-root",
    type=click.Path(),
    help="Override data root for installed sources",
)
@click.option(
    "--session",
    "-s",
    default="scholarly-run",
    help="Session ID for gate acknowledgements",
)
@click.option("--json", "as_json", is_flag=True, help="Output result as JSON")
def run_scholarly(
    reference: str,
    out: str,
    mode: str,
    include_schemas: bool,
    create_zip: bool,
    force: bool,
    data_root: str | None,
    session: str,
    as_json: bool,
):
    """Execute a complete scholarly workflow for a reference.

    Runs the entire scholarly pipeline in a single deterministic command:
    - Generates lockfile from installed packs
    - Checks for pending gates (refuses unless --force)
    - Runs translation for the reference
    - Exports all artifacts (apparatus, translation, citations, quote)
    - Creates snapshot with file hashes
    - Packages everything into a verified bundle
    - Writes deterministic run_log.json

    The output directory will contain:
    - lockfile.json: Pack state with integrity hashes
    - apparatus.jsonl: Variant apparatus data
    - translation.jsonl: Translation with provenance
    - citations.json: CSL-JSON bibliography
    - quote.json: Quotable output with gate status
    - snapshot.json: Reproducibility state
    - bundle/: Complete verified bundle (with manifest.json)
    - run_log.json: Detailed run log with all validations

    Examples:
        redletters run scholarly "John 1:1-18" -o out/run --mode traceable
        redletters run scholarly "John 1:1" -o out/run --include-schemas --zip
        redletters run scholarly "John 1:1" -o out/run --force  # bypass pending gates
        redletters run scholarly "John 1:1-5" -o out/run --json
    """
    from pathlib import Path as PathLib
    from redletters.run import ScholarlyRunner

    runner = ScholarlyRunner(
        data_root=data_root,
        session_id=session,
    )

    result = runner.run(
        reference=reference,
        output_dir=PathLib(out),
        mode=mode,  # type: ignore
        include_schemas=include_schemas,
        create_zip=create_zip,
        force=force,
    )

    if as_json:
        output_data = {
            "success": result.success,
            "output_dir": str(result.output_dir) if result.output_dir else None,
            "bundle_path": str(result.bundle_path) if result.bundle_path else None,
            "errors": result.errors,
            "gate_blocked": result.gate_blocked,
            "gate_refs": result.gate_refs,
        }
        if result.run_log:
            output_data["run_log"] = result.run_log.to_dict()
        console.print(json.dumps(output_data, indent=2, ensure_ascii=False))
    else:
        if result.success:
            console.print("[green]✓ Scholarly run completed successfully[/green]")
            console.print(f"  Output: {result.output_dir}")
            console.print(f"  Bundle: {result.bundle_path}")
            if result.run_log:
                console.print(f"  Files created: {len(result.run_log.files_created)}")
                console.print(
                    f"  Validations: {len(result.run_log.validations)} checks"
                )
                if result.run_log.gates and result.run_log.gates.forced:
                    console.print(
                        f"  [yellow]⚠ Gates bypassed with --force ({result.run_log.gates.pending_count} pending)[/yellow]"
                    )
        elif result.gate_blocked:
            console.print("[yellow]✗ Scholarly run blocked by pending gates[/yellow]")
            console.print(f"  Pending gates: {', '.join(result.gate_refs[:5])}")
            if len(result.gate_refs) > 5:
                console.print(f"  ... and {len(result.gate_refs) - 5} more")
            console.print("\n  [dim]To proceed anyway, use --force:[/dim]")
            console.print(
                f'    redletters run scholarly "{reference}" -o {out} --force'
            )
            console.print(
                "\n  [dim]Or acknowledge gates first (see redletters translate --ack)[/dim]"
            )
            sys.exit(2)
        else:
            console.print("[red]✗ Scholarly run failed[/red]")
            for error in result.errors:
                console.print(f"  [red]{error}[/red]")
            sys.exit(1)


# Register engine spine CLI commands
register_cli_commands(cli)


if __name__ == "__main__":
    cli()
