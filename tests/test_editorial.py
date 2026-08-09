import pytest
from unittest.mock import MagicMock
from app.services.editorial import evaluate_topic, generate_codeblooded_post, is_duplicate, EditorialEvaluation, CodebloodedPostContent
from app.services.tavily import RawTopic
from app.services.memory import LocalJsonMemoryStore
import app.services.editorial

@pytest.fixture
def mock_memory_store(monkeypatch):
    mock_store = MagicMock()
    mock_store.get_recent_posts.return_value = []
    mock_store.get_recent_rejected_topics.return_value = []
    monkeypatch.setattr(app.services.editorial, "memory_store", mock_store)
    return mock_store

def test_duplicate_detection(mock_memory_store):
    raw_topic = RawTopic(
        title="OpenAI releases new ChatGPT model",
        category="AI Models",
        source_name="TechCrunch",
        source_url="http://example.com",
        summary="A new model was released."
    )
    
    # Empty memory -> not a duplicate
    assert not is_duplicate(raw_topic)
    
    # Memory has similar post
    mock_memory_store.get_recent_posts.return_value = [
        {"topic_title": "OpenAI releases new ChatGPT model for developers"}
    ]
    assert is_duplicate(raw_topic)
    
    # Memory has unrelated post
    mock_memory_store.get_recent_posts.return_value = [
        {"topic_title": "Anthropic updates Claude limits"}
    ]
    assert not is_duplicate(raw_topic)

def test_evaluate_topic():
    mock_provider = MagicMock()
    mock_provider.generate_structured.return_value = EditorialEvaluation(
        relevance=80, novelty=75, technical_significance=90, 
        timeliness=85, source_quality=80, redundancy_risk=10, 
        overall_score=85, reasoning="Good technical topic."
    )
    
    topic = RawTopic(title="Test", category="Test", source_name="Test", source_url="", summary="Test")
    result = evaluate_topic(topic, mock_provider)
    
    assert result.overall_score == 85
    assert result.reasoning == "Good technical topic."
    mock_provider.generate_structured.assert_called_once()

def test_generate_codeblooded_post():
    mock_provider = MagicMock()
    mock_provider.generate_structured.return_value = CodebloodedPostContent(
        post_text="This is a post.",
        why_selected="Because it's cool.",
        why_now="Because it's new."
    )
    
    topic = RawTopic(title="Test", category="Test", source_name="Test", source_url="", summary="Test")
    result = generate_codeblooded_post(topic, mock_provider)
    
    assert result.post_text == "This is a post."
    assert "Because" in result.why_selected
