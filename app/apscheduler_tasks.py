from datetime import datetime, timezone
from flask_apscheduler import APScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
import pytz
from flask import current_app
from app.services.tournament_service import start_tournament
from app.services.user_service import remove_expired_tokens
from app.models import ScheduledTournament

scheduler = APScheduler()

def init_scheduler(app):
    if scheduler.running:
        print("Scheduler already running, skipping...")
        return
    # Настройка отдельной SQLite базы для задач
    app.config['SCHEDULER_JOBSTORES'] = {
        'default': SQLAlchemyJobStore(url='sqlite:///scheduler_jobs.sqlite')
    }
    app.config['SCHEDULER_API_ENABLED'] = False
    scheduler.init_app(app)
    try:
        with app.app_context():
            print("Scheduler starting...")
            scheduler.start()
            print("Scheduler started successfully")

            # Восстановить запланированные турниры
            scheduled_tournaments = ScheduledTournament.query.all()
            for scheduled in scheduled_tournaments:
                now_utc = datetime.now(pytz.UTC)
                start_time_utc = scheduled.start_time.replace(tzinfo=timezone.utc)
                if start_time_utc > now_utc:
                    schedule_tournament_start(
                        scheduled.tournament_id, scheduled.start_time, scheduled.job_id)
                    print(
                        f"Restored job for tournament {scheduled.tournament_id} at {scheduled.start_time} (UTC)")
                else:
                    print(
                        f"Skipped past job for tournament {scheduled.tournament_id} at {scheduled.start_time}")

            scheduler.add_job(
                id='remove_expired_tokens',
                func=remove_expired_tokens,
                trigger='interval',
                hours=1
            )
    except Exception as e:
        print(f"Failed to start scheduler: {str(e)}")

def schedule_tournament_start(tournament_id, start_time: datetime, job_id: str):
    try:
        print(
            f"Scheduling tournament {tournament_id} to start at {start_time} (UTC) with job_id {job_id}")
        if not scheduler.running:
            print("Scheduler is not running, cannot add job")
            return
        job = scheduler.add_job(
            func=start_tournament,
            trigger=DateTrigger(run_date=start_time),
            args=[tournament_id],
            id=job_id,
            replace_existing=True,
            jobstore='default'
        )
        print(job)
        scheduler.print_jobs()
        print(f"Job {job_id} added successfully")
    except Exception as e:
        print(f"Failed to add job {job_id}: {str(e)}")