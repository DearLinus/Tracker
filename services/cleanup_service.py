import asyncio
import functools
import logging
from datetime import datetime, timezone

from telegram.ext import Application

from services.tracker_service import get_tracker_from_context

logger = logging.getLogger(__name__)


async def _cleanup_due_deletions(app: Application) -> None:
    tracker = get_tracker_from_context(app.bot_data)
    now = datetime.now(timezone.utc)
    try:
        due_users = await asyncio.to_thread(functools.partial(tracker.cleanup_expired_deletions, now=now))
    except Exception:
        logger.exception("Failed to process pending deletions")
        return

    if due_users:
        logger.info("Processed permanent deletions for users: %s", due_users)


def schedule_cleanup_jobs(app: Application) -> None:
    """Register a periodic cleanup routine for expired pending deletions.

    The bot already uses application-scoped tracking, so the job is attached to the
    application itself and runs on the existing loop without needing global state.
    """
    app.job_queue.run_repeating(_cleanup_due_deletions, interval=3600, first=60)
