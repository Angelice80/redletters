"""FastAPI application for Engine Spine.

This is the desktop application backend per ADR-003/004/005/006.
Binds to 127.0.0.1 only (never 0.0.0.0).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from redletters import __version__
from redletters.engine_spine.broadcaster import EventBroadcaster
from redletters.engine_spine.database import EngineDatabase
from redletters.engine_spine.jobs import JobManager
from redletters.engine_spine.middleware import AuthMiddleware, setup_secure_logging
from redletters.engine_spine.routes import router
from redletters.engine_spine.status import EngineState

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_DB_PATH = Path("~/.greek2english/engine.db").expanduser()
DEFAULT_WORKSPACE_BASE = Path("~/.greek2english/workspaces").expanduser()
DEFAULT_PORT = 47200


def create_engine_app(
    db_path: Path | None = None,
    workspace_base: Path | None = None,
    safe_mode: bool = False,
) -> FastAPI:
    """Create the Engine Spine FastAPI application.

    Args:
        db_path: Path to engine database (default: ~/.greek2english/engine.db)
        workspace_base: Path to job workspaces (default: ~/.greek2english/workspaces)
        safe_mode: If True, disable job execution (diagnostics only)

    Returns:
        Configured FastAPI application
    """
    db_path = db_path or DEFAULT_DB_PATH
    workspace_base = workspace_base or DEFAULT_WORKSPACE_BASE

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan manager."""
        # Setup secure logging
        setup_secure_logging()

        # Initialize database
        db = EngineDatabase(db_path)
        db.init_schema()

        # Initialize broadcaster
        broadcaster = EventBroadcaster(db)

        # Initialize engine state
        state = EngineState.get_instance()
        state.initialize(db, broadcaster, safe_mode=safe_mode)

        # Recover orphaned jobs from crash
        job_manager = JobManager(db, broadcaster, workspace_base, safe_mode)
        recovered = await job_manager.recover_orphaned_jobs()
        if recovered:
            logger.warning(f"Recovered {len(recovered)} orphaned jobs: {recovered}")

        # Start job executor (unless safe mode)
        from redletters.engine_spine.executor import JobExecutor

        executor = JobExecutor(
            db=db,
            broadcaster=broadcaster,
            workspace_base=workspace_base,
            safe_mode=safe_mode,
        )
        executor.start()
        state.executor = executor  # Store for status/diagnostics

        # Start heartbeat
        await state.status_manager.start_heartbeat()

        logger.info(
            f"Engine started (mode={'safe' if safe_mode else 'normal'}, "
            f"port={DEFAULT_PORT})"
        )

        yield

        # Shutdown
        await executor.stop()
        await state.status_manager.stop_heartbeat()
        db.close()
        state.reset()
        logger.info("Engine stopped")

    app = FastAPI(
        title="Red Letters Engine",
        description="Desktop application backend for Greek NT translation tool",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Add CORS middleware for Tauri WebView access
    # Order matters: CORS must be added AFTER auth (middleware runs in reverse order)
    # so preflight OPTIONS requests are handled before auth rejects them
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:1420",
            "http://127.0.0.1:1420",
            "tauri://localhost",
            "https://tauri.localhost",
        ],
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["*"],
        allow_headers=["*"],  # includes Authorization + Last-Event-ID for SSE
    )

    # Add auth middleware (all endpoints except docs require token)
    app.add_middleware(AuthMiddleware)

    # Include routes
    app.include_router(router)

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "Red Letters Engine",
            "version": __version__,
            "api": "/v1",
            "docs": "/docs",
        }

    return app


# Create default app instance for uvicorn
app = create_engine_app()


def run_engine(
    host: str = "127.0.0.1",
    port: int = DEFAULT_PORT,
    safe_mode: bool = False,
    db_path: Path | None = None,
    workspace_base: Path | None = None,
    log_level: str = "info",
) -> None:
    """Run the engine server.

    CRITICAL: Always binds to 127.0.0.1 per ADR-005 security model.
    Never pass 0.0.0.0 to this function.

    Args:
        host: Bind host (must be 127.0.0.1 for security)
        port: Bind port (default: 47200)
        safe_mode: If True, disable job execution
        db_path: Path to engine database
        workspace_base: Path to job workspaces
        log_level: Logging level
    """
    import uvicorn

    # Security enforcement
    if host != "127.0.0.1":
        logger.error(f"Security violation: refusing to bind to {host}")
        logger.error("Engine must bind to 127.0.0.1 only per ADR-005")
        raise ValueError("Engine must bind to 127.0.0.1 only")

    # Create app with configuration
    engine_app = create_engine_app(
        db_path=db_path,
        workspace_base=workspace_base,
        safe_mode=safe_mode,
    )

    # Run server
    uvicorn.run(
        engine_app,
        host=host,
        port=port,
        log_level=log_level,
    )
