from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi import BackgroundTasks
import os

from app.state import state
from app.services.editorial import run_discovery_cycle

router = APIRouter(prefix="/dev", tags=["dev"])

@router.get("", response_class=HTMLResponse)
def get_dev_console():
    # Read the HTML template
    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "dev.html")
    with open(template_path, "r") as f:
        html = f.read()
    return HTMLResponse(content=html)

@router.get("/status")
def get_status():
    data = state.model_dump()
    from app.config import settings
    data["config"] = {
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model
    }
    return data

@router.post("/discover")
def trigger_discovery(background_tasks: BackgroundTasks):
    if state.status == "Running":
        return {"status": "error", "message": "Discovery cycle is already running."}
    
    background_tasks.add_task(run_discovery_cycle)
    return {"status": "ok", "message": "Discovery cycle started."}

@router.get("/feed")
def get_feed():
    from app.services.memory import memory_store
    return {"posts": memory_store.get_recent_posts(limit=20)}

@router.get("/memory")
def get_memory():
    from app.services.memory import memory_store
    return {
        "recent_posts": memory_store.get_recent_posts(limit=10),
        "recent_rejected_topics": memory_store.get_recent_rejected_topics(limit=10),
        "stats": {
            "posts_published": state.posts_published,
            "topics_rejected": state.topics_rejected,
            "topics_approved": state.topics_approved,
            "duplicate_topics_prevented": state.duplicate_topics_prevented
        }
    }

@router.post("/memory/reset")
def reset_memory():
    from app.services.memory import memory_store
    memory_store.reset()
    state.posts_published = 0
    state.topics_rejected = 0
    state.topics_approved = 0
    state.duplicate_topics_prevented = 0
    return {"status": "ok", "message": "Memory reset successfully."}
