import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.websocket_manager import manager as websocket_manager
from app.tasks import jobs

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


def start_scheduler():
    """
    Initializes the scheduler, adds jobs, and starts it.

    This function is designed to be called once at application startup.
    It schedules periodic tasks for updating stock data and checking alerts.
    """
    global scheduler

    if scheduler is not None and scheduler.running:
        logger.warning("Scheduler is already running.")
        return

    if scheduler is None:
        scheduler = AsyncIOScheduler(timezone="UTC")

    # Schedule the job to update the most active stock data periodically.
    # Running it hourly is a sensible default to avoid excessive API calls.
    scheduler.add_job(
        jobs.update_stock_data_job,
        'interval',
        minutes=60,
        id='update_stock_data_job',
        replace_existing=True
    )

    # Schedule the job to check for user-defined stock alerts.
    # This runs more frequently to provide timely notifications.
    scheduler.add_job(
        jobs.check_alerts_job,
        'interval',
        seconds=30,
        args=[websocket_manager],
        id='check_alerts_job',
        replace_existing=True
    )

    try:
        scheduler.start()
        logger.info("Scheduler started successfully. Jobs are now running.")
        logger.info(f"Scheduled jobs: {[job.id for job in scheduler.get_jobs()]}")
    except Exception as e:
        logger.error(f"Error starting the scheduler: {e}", exc_info=True)


def shutdown_scheduler():
    """
    Shuts down the scheduler gracefully if it is running.

    This function is intended to be called during application shutdown.
    """
    global scheduler
    if scheduler and scheduler.running:
        try:
            scheduler.shutdown()
            logger.info("Scheduler has been shut down gracefully.")
        except Exception as e:
            logger.error(f"Error shutting down the scheduler: {e}", exc_info=True)
    else:
        logger.info("Scheduler is not running or not initialized, no shutdown needed.")
