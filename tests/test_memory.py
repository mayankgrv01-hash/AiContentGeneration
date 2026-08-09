import os
import json
import pytest
from app.services.memory import LocalJsonMemoryStore

@pytest.fixture
def memory():
    # Use a test file
    filepath = "data/test_memory.json"
    if os.path.exists(filepath):
        os.remove(filepath)
    
    store = LocalJsonMemoryStore(filepath=filepath)
    yield store
    
    # Cleanup
    if os.path.exists(filepath):
        os.remove(filepath)

def test_memory_creation_and_reset(memory):
    data = memory.get_all_data()
    assert "published_posts" in data
    assert "rejected_topics" in data
    
    # modify and reset
    memory.save_post({"id": "123", "topic_title": "Test Post"})
    assert len(memory.get_recent_posts()) == 1
    
    memory.reset()
    assert len(memory.get_recent_posts()) == 0

def test_save_post(memory):
    post1 = {"id": "1", "topic_title": "First"}
    post2 = {"id": "2", "topic_title": "Second"}
    
    memory.save_post(post1)
    memory.save_post(post2)
    
    recent = memory.get_recent_posts()
    assert len(recent) == 2
    # Should be reverse chronological
    assert recent[0]["topic_title"] == "Second"
    assert recent[1]["topic_title"] == "First"

def test_save_rejected_topic(memory):
    topic = {"topic": "Bad Idea", "score": 40}
    memory.save_rejected_topic(topic)
    
    rejected = memory.get_recent_rejected_topics()
    assert len(rejected) == 1
    assert rejected[0]["topic"] == "Bad Idea"

def test_missing_or_corrupt_memory(tmp_path):
    filepath = tmp_path / "bad_memory.json"
    
    # Create invalid JSON
    with open(filepath, "w") as f:
        f.write("{ invalid json")
        
    store = LocalJsonMemoryStore(filepath=str(filepath))
    # Should safely fallback to default state instead of crashing
    data = store.get_all_data()
    assert "published_posts" in data
