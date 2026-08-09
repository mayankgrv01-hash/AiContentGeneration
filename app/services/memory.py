import json
import os
import fcntl
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
from pymongo import MongoClient
import certifi

class MemoryStore(ABC):
    @abstractmethod
    def save_agent(self, agent: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_active_agents(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_post(self, post: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def save_rejected_topic(self, topic: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_recent_posts(self, limit: int = 10, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_recent_rejected_topics(self, limit: int = 10, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_recent_topic(self, topic: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def get_all_data(self) -> Dict[str, Any]:
        pass

class LocalJsonMemoryStore(MemoryStore):
    def __init__(self, filepath: str = "data/codeblooded_memory.json"):
        self.filepath = filepath
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            self.reset()

    def _read_data(self) -> Dict[str, Any]:
        try:
            with open(self.filepath, "r") as f:
                fcntl.flock(f, fcntl.LOCK_SH)
                try:
                    return json.load(f)
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except json.JSONDecodeError:
            return self._default_state()
        except Exception:
            return self._default_state()

    def _write_data(self, data: Dict[str, Any]) -> None:
        with open(self.filepath, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                json.dump(data, f, indent=4)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def _default_state(self) -> Dict[str, Any]:
        return {
            "agents": [],
            "published_posts": [],
            "rejected_topics": [],
            "recent_topics": []
        }

    def save_agent(self, agent: Dict[str, Any]) -> None:
        data = self._read_data()
        if "agents" not in data:
            data["agents"] = []
        # Update if exists, otherwise insert
        existing = next((a for a in data["agents"] if a.get("agentId") == agent.get("agentId")), None)
        if existing:
            existing.update(agent)
        else:
            data["agents"].append(agent)
        self._write_data(data)

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        data = self._read_data()
        return next((a for a in data.get("agents", []) if a.get("agentId") == agent_id), None)

    def get_active_agents(self) -> List[Dict[str, Any]]:
        data = self._read_data()
        return data.get("agents", [])

    def save_post(self, post: Dict[str, Any]) -> None:
        data = self._read_data()
        data["published_posts"].insert(0, post)
        self._write_data(data)

    def save_rejected_topic(self, topic: Dict[str, Any]) -> None:
        data = self._read_data()
        data["rejected_topics"].insert(0, topic)
        self._write_data(data)

    def get_recent_posts(self, limit: int = 10, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        data = self._read_data()
        posts = data.get("published_posts", [])
        if agent_id:
            posts = [p for p in posts if p.get("agent_id") == agent_id or p.get("agentId") == agent_id]
        return posts[:limit]

    def get_recent_rejected_topics(self, limit: int = 10, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        data = self._read_data()
        rejections = data.get("rejected_topics", [])
        if agent_id:
            rejections = [r for r in rejections if r.get("agent_id") == agent_id]
        return rejections[:limit]
        
    def save_recent_topic(self, topic: Dict[str, Any]) -> None:
        data = self._read_data()
        data["recent_topics"].insert(0, topic)
        if len(data["recent_topics"]) > 50:
            data["recent_topics"] = data["recent_topics"][:50]
        self._write_data(data)

    def reset(self) -> None:
        self._write_data(self._default_state())

    def get_all_data(self) -> Dict[str, Any]:
        return self._read_data()


class MongoDbMemoryStore(MemoryStore):
    def __init__(self, uri: str, db_name: str = "codeblooded_db"):
        self.client = MongoClient(uri, tlsCAFile=certifi.where())
        self.db = self.client[db_name]
        self.agents_col = self.db["agents"]
        self.posts_col = self.db["published_posts"]
        self.rejected_col = self.db["rejected_topics"]
        self.recent_col = self.db["recent_topics"]

    def save_agent(self, agent: Dict[str, Any]) -> None:
        self.agents_col.update_one(
            {"agentId": agent.get("agentId")},
            {"$set": agent},
            upsert=True
        )

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self.agents_col.find_one({"agentId": agent_id}, {"_id": 0})

    def get_active_agents(self) -> List[Dict[str, Any]]:
        return list(self.agents_col.find({}, {"_id": 0}))

    def save_post(self, post: Dict[str, Any]) -> None:
        self.posts_col.insert_one(post)

    def save_rejected_topic(self, topic: Dict[str, Any]) -> None:
        self.rejected_col.insert_one(topic)

    def get_recent_posts(self, limit: int = 10, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = {}
        if agent_id:
            query = {"$or": [{"agent_id": agent_id}, {"agentId": agent_id}]}
        cursor = self.posts_col.find(query, {"_id": 0}).sort("publication_timestamp", -1).limit(limit)
        return list(cursor)

    def get_recent_rejected_topics(self, limit: int = 10, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = {}
        if agent_id:
            query = {"agent_id": agent_id}
        cursor = self.rejected_col.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
        return list(cursor)

    def save_recent_topic(self, topic: Dict[str, Any]) -> None:
        self.recent_col.insert_one(topic)
        count = self.recent_col.count_documents({})
        if count > 50:
            to_delete = self.recent_col.find({}, {"_id": 1}).sort("timestamp", 1).limit(count - 50)
            ids = [doc["_id"] for doc in to_delete]
            self.recent_col.delete_many({"_id": {"$in": ids}})

    def reset(self) -> None:
        self.agents_col.delete_many({})
        self.posts_col.delete_many({})
        self.rejected_col.delete_many({})
        self.recent_col.delete_many({})

    def get_all_data(self) -> Dict[str, Any]:
        return {
            "agents": list(self.agents_col.find({}, {"_id": 0})),
            "published_posts": list(self.posts_col.find({}, {"_id": 0}).sort("publication_timestamp", -1)),
            "rejected_topics": list(self.rejected_col.find({}, {"_id": 0}).sort("timestamp", -1)),
            "recent_topics": list(self.recent_col.find({}, {"_id": 0}).sort("timestamp", -1)),
        }


# Instantiate based on settings
from app.config import settings

if settings.mongodb_uri:
    memory_store: MemoryStore = MongoDbMemoryStore(settings.mongodb_uri)
else:
    memory_store: MemoryStore = LocalJsonMemoryStore()
