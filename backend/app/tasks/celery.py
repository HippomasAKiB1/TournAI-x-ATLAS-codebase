import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "atlas_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

@celery_app.task(name="tasks.run_adaptive_pipeline")
def run_adaptive_pipeline_task(
    home_team: str,
    away_team: str,
    home_score: int,
    away_score: int,
    stage: str
):
    """Celery background task wrapper for the ATLAS adaptive retraining loop."""
    # Local import to avoid circular imports during startup
    from src.adaptive.pipeline_trigger import trigger_adaptive_update
    
    print(f"[Celery Worker] Starting background retraining for {home_team} vs {away_team}")
    trigger_adaptive_update(
        home_team=home_team,
        away_team=away_team,
        home_score=home_score,
        away_score=away_score,
        stage=stage
    )
    return {"status": "completed"}
