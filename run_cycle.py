"""
run_cycle.py — Standalone one-shot cron script for Render Cron Jobs.

Runs exactly ONE autonomous discovery cycle then exits.
Exit code 0 = success, 1 = error.

Usage:
    python run_cycle.py                      # uses the most recently initialized agent
    python run_cycle.py <agentId>            # uses a specific agent
"""
import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("nexus.cron")


def main():
    agent_id_arg = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        from app.services.memory import memory_store
        from app.services.editorial import run_discovery_cycle
        from app.config import settings
    except Exception as e:
        logger.error(f"Failed to import NEXUS modules: {e}")
        sys.exit(1)

    # Resolve agent_id
    agent_id = agent_id_arg
    if not agent_id:
        try:
            agents = memory_store.get_active_agents()
            if not agents:
                logger.error("No initialized agents found in MongoDB. Run POST /api/agent/init first.")
                sys.exit(1)
            # Use the most recently created agent
            agents_sorted = sorted(
                agents,
                key=lambda a: a.get("created_at", ""),
                reverse=True
            )
            agent_id = agents_sorted[0].get("agentId")
            agent_name = agents_sorted[0].get("persona", {}).get("name", "NEXUS")
            agent_domain = agents_sorted[0].get("persona", {}).get("domain", "AI")
            logger.info(f"Using agent: {agent_id} | Name: {agent_name} | Domain: {agent_domain}")
        except Exception as e:
            logger.error(f"Failed to load agents from MongoDB: {e}")
            sys.exit(1)

    logger.info(f"Starting one-shot discovery cycle for agent {agent_id} at {datetime.utcnow().isoformat()}Z")

    try:
        run_discovery_cycle(agent_id=agent_id)
        logger.info("Discovery cycle completed successfully.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Discovery cycle failed with unhandled exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
