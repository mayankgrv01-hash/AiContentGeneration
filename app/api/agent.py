import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional

from app.services.memory import memory_store
from app.scheduler import start_agent_scheduler
from app.logging_config import logger
from app.state import state

router = APIRouter(prefix="/api/agent")


class PersonaConfig(BaseModel):
    name: str
    domain: str


class InitRequest(BaseModel):
    persona: PersonaConfig


@router.post("/init")
def init_agent(req: InitRequest):
    """Initialize an autonomous agent with a persona and start its discovery loop."""
    agent_id = str(uuid.uuid4())

    agent_record = {
        "agentId": agent_id,
        "persona": {
            "name": req.persona.name,
            "domain": req.persona.domain,
        },
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "active",
    }

    memory_store.save_agent(agent_record)
    logger.info(
        f"Agent initialized: {agent_id} | Name: {req.persona.name} | Domain: {req.persona.domain}"
    )

    # Start the autonomous discovery loop for this agent
    start_agent_scheduler(agent_id)

    return {"agentId": agent_id}


@router.get("/feed")
def get_agent_feed(agentId: str):
    """Return the published feed for a specific agent in the evaluator-required schema."""
    agent = memory_store.get_agent(agentId)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agentId}' not found.")

    raw_posts = memory_store.get_recent_posts(limit=200, agent_id=agentId)

    posts = []
    for p in raw_posts:
        # Normalize timestamp to ISO 8601 UTC with 'Z' suffix
        ts = p.get("publication_timestamp", "")
        try:
            if ts.endswith("Z"):
                created_at = ts
            elif "+" in ts:
                dt = datetime.fromisoformat(ts)
                created_at = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                dt = datetime.fromisoformat(ts)
                created_at = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            created_at = ts

        posts.append(
            {
                "id": p.get("id", str(uuid.uuid4())),
                "createdAt": created_at,
                "text": p.get("post_text", ""),
                "rationale": p.get("rationale", p.get("why_selected", "")),
                "sources": p.get("source_urls", []),
            }
        )

    return {"posts": posts}


@router.get("/status")
def get_agent_status(agentId: Optional[str] = None):
    """Return autonomous agent status suitable for the evaluator."""
    initialized = False
    active = False
    agent_info = {}

    if agentId:
        agent = memory_store.get_agent(agentId)
        if agent:
            initialized = True
            active = agent.get("status") == "active"
            agent_info = {
                "agentId": agentId,
                "name": agent.get("persona", {}).get("name"),
                "domain": agent.get("persona", {}).get("domain"),
                "initialized_at": agent.get("created_at"),
            }
    else:
        # Return global NEXUS status
        agents = memory_store.get_active_agents()
        initialized = len(agents) > 0
        active = initialized

    last_cycle = None
    next_cycle = None
    if state.last_discovery_time:
        last_cycle = state.last_discovery_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    if state.next_discovery_time:
        try:
            next_cycle = state.next_discovery_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            next_cycle = str(state.next_discovery_time)

    # Count stats scoped to this agent if specified
    if agentId:
        posts_published = len(memory_store.get_recent_posts(limit=500, agent_id=agentId))
        topics_rejected = len(
            memory_store.get_recent_rejected_topics(limit=500, agent_id=agentId)
        )
    else:
        posts_published = state.posts_published
        topics_rejected = state.topics_rejected

    return {
        **agent_info,
        "initialized": initialized,
        "active": active,
        "scheduler_status": state.autonomy_status,
        "current_operation": state.current_operation,
        "last_cycle": last_cycle,
        "next_cycle": next_cycle,
        "posts_published": posts_published,
        "topics_analyzed": state.topics_discovered,
        "topics_rejected": topics_rejected,
        "duplicate_topics_prevented": state.duplicate_topics_prevented,
    }
