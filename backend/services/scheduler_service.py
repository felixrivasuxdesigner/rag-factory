"""
Scheduler Service - APScheduler integration for automatic sync jobs
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging
import os
from redis import Redis
from rq import Queue

from core.database import get_db_connection

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

def get_scheduler():
    """Get or create the scheduler instance."""
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler()
        scheduler.start()
        logger.info("Scheduler started")
    return scheduler

def parse_schedule_config(sync_frequency: str) -> dict:
    """
    Parse sync_frequency string into scheduler config.

    Supported formats:
    - "manual" - No scheduling
    - "hourly" - Every hour
    - "daily" - Every day at midnight
    - "weekly" - Every Monday at midnight
    - "interval:30m" - Every 30 minutes
    - "interval:2h" - Every 2 hours
    - "interval:1d" - Every day
    - "cron:0 0 * * *" - Cron expression
    """
    if not sync_frequency or sync_frequency == "manual":
        return None

    # Preset frequencies
    if sync_frequency == "hourly":
        return {"type": "interval", "hours": 1}
    elif sync_frequency == "daily":
        return {"type": "cron", "hour": 0, "minute": 0}
    elif sync_frequency == "weekly":
        return {"type": "cron", "day_of_week": 0, "hour": 0, "minute": 0}

    # Interval format: "interval:30m", "interval:2h", "interval:1d"
    if sync_frequency.startswith("interval:"):
        interval_str = sync_frequency.split(":")[1]
        if interval_str.endswith("m"):
            minutes = int(interval_str[:-1])
            return {"type": "interval", "minutes": minutes}
        elif interval_str.endswith("h"):
            hours = int(interval_str[:-1])
            return {"type": "interval", "hours": hours}
        elif interval_str.endswith("d"):
            days = int(interval_str[:-1])
            return {"type": "interval", "days": days}

    # Cron format: "cron:0 0 * * *"
    if sync_frequency.startswith("cron:"):
        cron_expr = sync_frequency.split(":", 1)[1]
        parts = cron_expr.split()
        if len(parts) == 5:
            return {
                "type": "cron",
                "minute": parts[0],
                "hour": parts[1],
                "day": parts[2],
                "month": parts[3],
                "day_of_week": parts[4]
            }

    logger.warning(f"Unknown sync_frequency format: {sync_frequency}")
    return None

def trigger_sync_job(source_id: int, source_name: str):
    """Trigger a sync job for a data source."""
    try:
        logger.info(f"Scheduler triggered sync for source {source_id}: {source_name}")

        # Get Redis queue
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_conn = Redis.from_url(redis_url)
        queue = Queue('rag-tasks', connection=redis_conn)

        # Get source and project info
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to connect to database")
            return

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ds.*, rp.id as project_id
                    FROM data_sources ds
                    JOIN rag_projects rp ON ds.project_id = rp.id
                    WHERE ds.id = %s AND ds.is_active = TRUE
                """, (source_id,))

                result = cur.fetchone()
                if not result:
                    logger.warning(f"Source {source_id} not found or inactive")
                    return

                columns = [desc[0] for desc in cur.description]
                source_data = dict(zip(columns, result))

                # Create ingestion job
                cur.execute("""
                    INSERT INTO ingestion_jobs (
                        project_id, source_id, job_type, status,
                        total_documents, processed_documents,
                        successful_documents, failed_documents
                    )
                    VALUES (%s, %s, 'scheduled', 'pending', 0, 0, 0, 0)
                    RETURNING id;
                """, (source_data['project_id'], source_id))

                job_id = cur.fetchone()[0]
                conn.commit()

                logger.info(f"Created scheduled job {job_id} for source {source_id}")

                # Enqueue to RQ
                from workers.ingestion_tasks import run_ingestion_job
                queue.enqueue(
                    run_ingestion_job,
                    job_id=job_id,
                    job_timeout='10m'
                )

                logger.info(f"Enqueued job {job_id} to RQ worker")

        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Error triggering sync for source {source_id}: {e}", exc_info=True)

def add_source_schedule(source_id: int, source_name: str, sync_frequency: str):
    """Add or update a schedule for a data source."""
    config = parse_schedule_config(sync_frequency)
    if not config:
        logger.info(f"No schedule for source {source_id} (manual mode)")
        return False

    scheduler = get_scheduler()
    job_id = f"source_{source_id}"

    # Remove existing job if any
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # Create appropriate trigger
    if config["type"] == "interval":
        trigger_kwargs = {k: v for k, v in config.items() if k != "type"}
        trigger = IntervalTrigger(**trigger_kwargs)
    elif config["type"] == "cron":
        trigger_kwargs = {k: v for k, v in config.items() if k != "type"}
        trigger = CronTrigger(**trigger_kwargs)
    else:
        logger.error(f"Unknown trigger type: {config['type']}")
        return False

    # Add job to scheduler
    scheduler.add_job(
        trigger_sync_job,
        trigger=trigger,
        id=job_id,
        args=[source_id, source_name],
        name=f"Sync: {source_name}",
        replace_existing=True
    )

    logger.info(f"Scheduled source {source_id} ({source_name}) with {sync_frequency}")
    return True

def remove_source_schedule(source_id: int):
    """Remove a schedule for a data source."""
    scheduler = get_scheduler()
    job_id = f"source_{source_id}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Removed schedule for source {source_id}")
        return True

    return False

def load_all_schedules():
    """Load all active schedules from database."""
    conn = get_db_connection()
    if not conn:
        logger.error("Failed to connect to database")
        return

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, sync_frequency
                FROM data_sources
                WHERE is_active = TRUE
                AND sync_frequency IS NOT NULL
                AND sync_frequency != 'manual'
            """)

            sources = cur.fetchall()
            logger.info(f"Loading {len(sources)} scheduled sources")

            for source_id, source_name, sync_frequency in sources:
                add_source_schedule(source_id, source_name, sync_frequency)

    finally:
        conn.close()

def get_scheduled_jobs():
    """Get all scheduled jobs with next run times."""
    scheduler = get_scheduler()
    jobs = []

    for job in scheduler.get_jobs():
        jobs.append({
            "job_id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })

    return jobs

def pause_schedule(source_id: int):
    """Pause a schedule without removing it."""
    scheduler = get_scheduler()
    job_id = f"source_{source_id}"

    job = scheduler.get_job(job_id)
    if job:
        scheduler.pause_job(job_id)
        logger.info(f"Paused schedule for source {source_id}")
        return True

    return False

def resume_schedule(source_id: int):
    """Resume a paused schedule."""
    scheduler = get_scheduler()
    job_id = f"source_{source_id}"

    job = scheduler.get_job(job_id)
    if job:
        scheduler.resume_job(job_id)
        logger.info(f"Resumed schedule for source {source_id}")
        return True

    return False

def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler shutdown")

# Initialize on import if running as part of API
if __name__ != "__main__":
    # Auto-load schedules when module is imported
    try:
        load_all_schedules()
        logger.info("Scheduler service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {e}")
