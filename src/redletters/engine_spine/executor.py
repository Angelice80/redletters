"""Background job executor for Engine Spine.

Implements the worker loop that claims queued jobs and executes them.
Single-threaded async executor for MVP - can scale later.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redletters.engine_spine.broadcaster import EventBroadcaster
    from redletters.engine_spine.database import EngineDatabase
    from redletters.engine_spine.jobs import JobManager

logger = logging.getLogger(__name__)

# Executor configuration
POLL_INTERVAL_SECONDS = 0.5  # How often to check for new jobs
MAX_BACKOFF_SECONDS = 5.0  # Max backoff when idle


class JobExecutor:
    """Background executor that processes queued jobs.

    Runs as an asyncio task started from FastAPI lifespan.
    Disabled in safe mode.
    """

    def __init__(
        self,
        *,
        db: "EngineDatabase",
        broadcaster: "EventBroadcaster",
        workspace_base: Path,
        safe_mode: bool = False,
    ):
        self._db = db
        self._broadcaster = broadcaster
        self._workspace_base = workspace_base
        self._safe_mode = safe_mode
        self._shutdown = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._current_job_id: str | None = None

    @property
    def is_running(self) -> bool:
        """Check if executor loop is running."""
        return self._task is not None and not self._task.done()

    @property
    def current_job_id(self) -> str | None:
        """Get currently executing job ID."""
        return self._current_job_id

    def start(self) -> None:
        """Start the executor background task."""
        if self._safe_mode:
            logger.info("Executor disabled (safe mode)")
            return

        if self._task is not None:
            logger.warning("Executor already started")
            return

        self._task = asyncio.create_task(
            self._run_loop(),
            name="job-executor",
        )
        logger.info("Job executor started")

    async def stop(self, timeout: float = 30.0) -> None:
        """Stop the executor gracefully.

        Args:
            timeout: Max seconds to wait for current job to finish
        """
        if self._task is None:
            return

        logger.info("Stopping job executor...")
        self._shutdown.set()

        try:
            await asyncio.wait_for(self._task, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Executor stop timed out after {timeout}s, cancelling")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._task = None
        logger.info("Job executor stopped")

    async def _run_loop(self) -> None:
        """Main executor loop - polls for jobs and processes them."""
        logger.debug("Executor run loop starting")
        backoff = POLL_INTERVAL_SECONDS

        while not self._shutdown.is_set():
            try:
                # Fetch next queued job
                job_id = self._db.fetch_next_queued_job_id()

                if job_id is None:
                    # No jobs available - back off
                    backoff = min(backoff * 1.5, MAX_BACKOFF_SECONDS)
                    try:
                        await asyncio.wait_for(
                            self._shutdown.wait(),
                            timeout=backoff,
                        )
                        # Shutdown signaled
                        break
                    except asyncio.TimeoutError:
                        # Normal timeout, continue polling
                        continue

                # Reset backoff when job found
                backoff = POLL_INTERVAL_SECONDS

                # Try to claim the job atomically
                claimed = self._db.claim_job(job_id)
                if not claimed:
                    # Another executor claimed it (future multi-executor support)
                    logger.debug(f"Job {job_id} already claimed by another worker")
                    continue

                # Process the job
                self._current_job_id = job_id
                try:
                    await self._process_job(job_id)
                finally:
                    self._current_job_id = None

            except Exception as e:
                logger.exception(f"Executor loop error: {e}")
                # Brief pause on error to avoid tight error loops
                await asyncio.sleep(1.0)

    async def _process_job(self, job_id: str) -> None:
        """Process a single job from start to completion.

        Args:
            job_id: The job to process
        """
        from redletters.engine_spine.jobs import JobManager
        from redletters.engine_spine.models import LogLevel

        job_manager = JobManager(
            db=self._db,
            broadcaster=self._broadcaster,
            workspace_base=self._workspace_base,
            safe_mode=self._safe_mode,
        )

        logger.info(f"Processing job: {job_id}")

        try:
            # Emit running state (claim already happened, this sets started_at)
            await job_manager.start_job(job_id)

            # Get job details
            job = await job_manager.get_job(job_id)
            if not job:
                raise RuntimeError(f"Job disappeared after claim: {job_id}")

            # Log job start
            await job_manager.log(
                job_id,
                LogLevel.INFO,
                "executor",
                f"Starting job with config: {job.config.model_dump_json()}",
            )

            # Update progress: initializing
            await job_manager.update_progress(
                job_id,
                phase="initializing",
                percent=0,
                message="Loading translation engine",
            )

            # Execute translation work in thread pool (sync code)
            # Use run_in_executor for Python 3.8 compatibility (to_thread is 3.9+)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,  # Default executor
                self._execute_translation,
                job_id,
                job.config.model_dump(),
                job_manager,
            )

            # Update progress: finalizing
            await job_manager.update_progress(
                job_id,
                phase="finalizing",
                percent=95,
                message="Generating receipt",
            )

            # Complete the job with outputs
            await job_manager.complete_job(job_id, outputs=result.get("outputs", []))

            await job_manager.log(
                job_id,
                LogLevel.INFO,
                "executor",
                "Job completed successfully",
            )

            logger.info(f"Job completed: {job_id}")

        except asyncio.CancelledError:
            # Shutdown requested during job execution
            logger.warning(f"Job {job_id} cancelled due to shutdown")
            await job_manager.fail_job(
                job_id,
                error_code="E_CANCELLED",
                error_message="Job cancelled due to engine shutdown",
            )
            raise

        except Exception as e:
            logger.exception(f"Job {job_id} failed: {e}")
            await job_manager.fail_job(
                job_id,
                error_code="E_EXECUTION_ERROR",
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
            )

    def _execute_translation(
        self,
        job_id: str,
        config: dict[str, Any],
        job_manager: "JobManager",
    ) -> dict[str, Any]:
        """Execute the actual translation work (sync, runs in thread pool).

        Args:
            job_id: Job identifier
            config: Job configuration dict
            job_manager: For progress updates (will be called via run_coroutine_threadsafe)

        Returns:
            Dict with 'outputs' list of ArtifactInfo
        """
        from redletters.config import Settings
        from redletters.db.connection import get_connection
        from redletters.engine.generator import CandidateGenerator, RenderingStyle
        from redletters.engine.ranker import RenderingRanker
        from redletters.engine.query import parse_reference, get_tokens_for_reference
        from redletters.engine_spine.models import ArtifactInfo

        outputs: list[ArtifactInfo] = []
        input_paths = config.get("input_paths", [])
        style = config.get("style", "natural")
        workspace_path = self._workspace_base / job_id / "output"

        # Get database connection to translation database
        settings = Settings()
        conn = get_connection(settings.db_path)

        try:
            generator = CandidateGenerator(conn)
            ranker = RenderingRanker(conn)

            total_items = len(input_paths)
            results = []

            for idx, input_path in enumerate(input_paths):
                # Update progress
                percent = int((idx / max(total_items, 1)) * 80) + 10
                self._sync_update_progress(
                    job_manager,
                    job_id,
                    phase="translating",
                    percent=percent,
                    items_completed=idx,
                    items_total=total_items,
                    message=f"Processing {input_path}",
                )

                # Parse input path (e.g., "demo:matthew" or "Matthew 3:1-5")
                if input_path.startswith("demo:"):
                    # Demo mode - generate sample output
                    book_name = input_path.split(":")[1].title()
                    result = self._generate_demo_output(book_name, style)
                else:
                    # Real reference parsing
                    ref = parse_reference(input_path)
                    tokens = get_tokens_for_reference(conn, ref)

                    if not tokens:
                        result = {
                            "reference": input_path,
                            "error": "No tokens found for reference",
                        }
                    else:
                        # Generate candidates
                        candidates = generator.generate_all(tokens)

                        # Rank and select best for requested style
                        ranked = ranker.rank(candidates)

                        # Find the requested style
                        style_enum = (
                            RenderingStyle(style)
                            if style in [s.value for s in RenderingStyle]
                            else RenderingStyle.NATURAL
                        )
                        selected = next(
                            (c for c in ranked if c.style == style_enum),
                            ranked[0] if ranked else None,
                        )

                        if selected:
                            result = {
                                "reference": str(ref),
                                "style": selected.style.value,
                                "text": selected.text,
                                "score": selected.raw_score,
                                "token_count": len(selected.token_renderings),
                            }
                        else:
                            result = {
                                "reference": input_path,
                                "error": "No renderings generated",
                            }

                results.append(result)

            # Write results to output file
            output_file = workspace_path / "renderings.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_content = json.dumps(results, indent=2, ensure_ascii=False)
            output_file.write_text(output_content, encoding="utf-8")

            # Create artifact info
            import hashlib

            content_bytes = output_content.encode("utf-8")
            sha256 = hashlib.sha256(content_bytes).hexdigest()

            outputs.append(
                ArtifactInfo(
                    name="renderings.json",
                    path=str(output_file),
                    artifact_type="rendering",
                    size_bytes=len(content_bytes),
                    sha256=sha256,
                )
            )

            return {"outputs": outputs, "results": results}

        finally:
            conn.close()

    def _generate_demo_output(self, book_name: str, style: str) -> dict[str, Any]:
        """Generate demo output for testing without full translation.

        Args:
            book_name: Book name (e.g., "Matthew")
            style: Rendering style

        Returns:
            Demo result dict
        """
        # Demo translations for testing
        demo_texts = {
            "Matthew": {
                "natural": "In those days John the Baptist came preaching in the wilderness of Judea, 'Repent, for the kingdom of heaven is at hand.'",
                "ultra-literal": "In the days those came-forth John the Baptist proclaiming in the wilderness of-the Judea, saying: Repent-ye, has-drawn-near for the kingdom of-the heavens.",
            },
            "Mark": {
                "natural": "The beginning of the gospel of Jesus Christ, the Son of God.",
                "ultra-literal": "Beginning of-the good-news of-Jesus Christ Son of-God.",
            },
            "John": {
                "natural": "In the beginning was the Word, and the Word was with God, and the Word was God.",
                "ultra-literal": "In beginning was the Word, and the Word was toward the God, and God was the Word.",
            },
        }

        book_demos = demo_texts.get(book_name, demo_texts["Matthew"])
        text = book_demos.get(style, book_demos.get("natural", "Demo translation text"))

        return {
            "reference": f"{book_name} 1:1-2",
            "style": style,
            "text": text,
            "score": 0.85,
            "token_count": len(text.split()),
            "demo": True,
        }

    def _sync_update_progress(
        self,
        job_manager: "JobManager",
        job_id: str,
        phase: str,
        percent: int | None = None,
        items_completed: int | None = None,
        items_total: int | None = None,
        message: str | None = None,
    ) -> None:
        """Update progress from sync code (runs coroutine in event loop).

        This is called from the thread pool, so we need to schedule
        the async update in the main event loop.
        """
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - we're in a thread
            # Skip progress update rather than blocking
            logger.debug(f"Skipping progress update (no event loop): {phase}")
            return

        # Schedule the coroutine
        asyncio.run_coroutine_threadsafe(
            job_manager.update_progress(
                job_id,
                phase=phase,
                percent=percent,
                items_completed=items_completed,
                items_total=items_total,
                message=message,
            ),
            loop,
        )
