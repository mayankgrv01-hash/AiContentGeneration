import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta

from app.config import settings
from app.state import state
from app.services.editorial import run_discovery_cycle
from app.services.memory import memory_store
from app.logging_config import logger

# Initialize a global scheduler
scheduler = BackgroundScheduler()

def scheduled_discovery_job(agent_id: str = None):
    if state.status == "Running":
        logger.warning("Scheduled discovery skipped; cycle already running.")
        return
        
    logger.info(f"Autonomous discovery cycle starting for agent: {agent_id or 'default'}...")
    run_discovery_cycle(agent_id)
    
    # Update next discovery time
    job_id = f'discovery_job_{agent_id}' if agent_id else 'discovery_job'
    job = scheduler.get_job(job_id)
    if job and job.next_run_time:
        state.next_discovery_time = job.next_run_time

def start_agent_scheduler(agent_id: str):
    """Starts the discovery schedule for a specific agent id."""
    if not scheduler.running:
        scheduler.start()
        state.autonomy_status = "ACTIVE"
        
    interval_minutes = settings.discovery_interval_minutes
    job_id = f"discovery_job_{agent_id}"
    
    scheduler.add_job(
        scheduled_discovery_job,
        args=[agent_id],
        trigger=IntervalTrigger(minutes=interval_minutes),
        id=job_id,
        name=f'Autonomous Discovery Cycle for {agent_id}',
        replace_existing=True,
        next_run_time=datetime.now() + timedelta(seconds=2) # Run almost immediately after init
    )
    
    job = scheduler.get_job(job_id)
    if job and job.next_run_time:
        state.next_discovery_time = job.next_run_time
        
    logger.info(f"Agent scheduler started for {agent_id}. Discovery interval: {interval_minutes} minutes.")

def start_scheduler():
    """Initial startup of the global scheduler and restoring all active agents from database."""
    if not scheduler.running:
        scheduler.start()
        state.autonomy_status = "ACTIVE"
        logger.info("Global scheduler started.")
        
    # Restore jobs for all existing active agents in MongoDB
    try:
        agents = memory_store.get_active_agents()
        logger.info(f"Restoring scheduled discovery cycles for {len(agents)} persisted agents.")
        for agent in agents:
            agent_id = agent.get("agentId")
            if agent_id:
                start_agent_scheduler(agent_id)
    except Exception as e:
        logger.error(f"Error restoring persisted agents: {e}")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        state.autonomy_status = "STANDBY"
        logger.info("Scheduler stopped.")
