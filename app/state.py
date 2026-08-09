from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class DiscoveredTopic(BaseModel):
    title: str
    category: str
    source_name: str
    source_url: str
    summary: str
    approved: bool
    rejection_reason: Optional[str] = None

class AppState(BaseModel):
    status: str = "Idle"
    current_operation: str = "None"
    last_discovery_time: Optional[datetime] = None
    next_discovery_time: Optional[datetime] = None
    autonomy_status: str = "STANDBY"
    topics_discovered: int = 0
    topics_rejected: int = 0
    topics_approved: int = 0
    posts_published: int = 0
    duplicate_topics_prevented: int = 0
    ai_requests_used: int = 0
    tavily_requests_used: int = 0
    tavily_status: str = "Connected"
    nemotron_status: str = "Connected"
    discovered_topics: List[DiscoveredTopic] = []
    logs: List[str] = []
    cycle_history: List[Dict[str, Any]] = []

    def log(self, message: str):
        self.logs.append(f"{datetime.now().isoformat()} - {message}")
        # Keep last 50 logs
        if len(self.logs) > 50:
            self.logs.pop(0)

# Global in-memory state
state = AppState()
