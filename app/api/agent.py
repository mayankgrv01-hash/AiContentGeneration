import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional

from app.services.memory import memory_store
from app.scheduler import start_agent_scheduler
from app.logging_config import logger

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
            "domain": req.persona.domain
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active"
    }
    
    memory_store.save_agent(agent_record)
    logger.info(f"Agent initialized: {agent_id} | Name: {req.persona.name} | Domain: {req.persona.domain}")
    
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
            elif "+" in ts or ts.endswith("UTC"):
                dt = datetime.fromisoformat(ts)
                created_at = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                # Assume local time stored without tz, convert to UTC representation
                dt = datetime.fromisoformat(ts)
                created_at = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            created_at = ts
            
        posts.append({
            "id": p.get("id", str(uuid.uuid4())),
            "createdAt": created_at,
            "text": p.get("post_text", ""),
            "rationale": p.get("rationale", p.get("why_selected", "")),
            "sources": p.get("source_urls", [])
        })
    
    return {"posts": posts}
