from datetime import datetime, timezone
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from flask import current_app
import pytz
from app.services.tournament_service import start_tournament
from app.services.user_service import remove_expired_tokens
from app.models import ScheduledTournament

scheduler = BackgroundScheduler()
scheduler_initialized = False


def register_scheduler(app):
    global scheduler_initialized
    if scheduler_initialized:
        print("Scheduler already initialized, skipping...")
        return

    # Проверяем, что мы в главном процессе
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        with app.app_context():
            print("Scheduler starting...")
            # Восстанавливаем запланированные турниры
            scheduled_tournaments = ScheduledTournament.query.all()
            for scheduled in scheduled_tournaments:
                now_utc = datetime.now(pytz.UTC)
                start_time_utc = scheduled.start_time.replace(
                    tzinfo=timezone.utc)
                if start_time_utc > now_utc:
                    schedule_tournament_start(
                        scheduled.tournament_id, scheduled.start_time, scheduled.job_id)
                    print(
                        f"Restored job for tournament {scheduled.tournament_id} at {scheduled.start_time} (UTC)")
                else:
                    print(
                        f"Skipped past job for tournament {scheduled.tournament_id} at {scheduled.start_time}")

            scheduler.add_job(func=remove_expired_tokens,
                              trigger="interval", hours=1)
            scheduler.start()
            scheduler_initialized = True
            print("Scheduler started successfully")


def schedule_tournament_start(tournament_id, start_time: datetime, job_id: str):
    with current_app.app_context():
        print(
            f"Scheduling tournament {tournament_id} to start at {start_time} (UTC) with job_id {job_id}")
        scheduler.add_job(
            func=start_tournament,
            trigger=DateTrigger(run_date=start_time),
            args=[tournament_id],
            id=job_id,
            replace_existing=True
        )
