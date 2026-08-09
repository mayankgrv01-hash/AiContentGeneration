import json
import re
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel
from typing import Optional, List

from app.services.tavily import RawTopic, discover_topics
from app.state import DiscoveredTopic, state
from app.ai.openrouter import OpenRouterProvider
from app.config import settings
from app.logging_config import logger
from app.services.memory import memory_store
from app.persona.codeblooded_persona import get_system_prompt

# Models for AI Responses
class EditorialEvaluation(BaseModel):
    relevance: int
    novelty: int
    technical_significance: int
    timeliness: int
    source_quality: int
    redundancy_risk: int
    overall_score: int
    reasoning: str

class CodebloodedPostContent(BaseModel):
    post_text: str
    rationale: str

def is_duplicate(raw_topic: RawTopic, agent_id: Optional[str] = None) -> bool:
    """Check for semantic similarity based on title overlap, filtered by agent."""
    title_words = set(raw_topic.title.lower().split())
    
    def check_overlap(existing_title: str) -> bool:
        existing_words = set(existing_title.lower().split())
        overlap = title_words.intersection(existing_words)
        if len(title_words) > 0 and len(overlap) / len(title_words) > 0.6:
            return True
        return False
        
    recent_posts = memory_store.get_recent_posts(limit=20, agent_id=agent_id)
    for post in recent_posts:
        if check_overlap(post.get("topic_title", "")):
            return True
            
    recent_rejected = memory_store.get_recent_rejected_topics(limit=20, agent_id=agent_id)
    for rej in recent_rejected:
        if check_overlap(rej.get("topic", "")):
            return True
            
    return False

def count_words(text: str) -> int:
    """Deterministic word count calculation."""
    if not text:
        return 0
    return len(text.split())

def evaluate_topic(topic: RawTopic, provider: OpenRouterProvider, domain: str) -> EditorialEvaluation:
    prompt = f"""
You are an editorial director for a highly technical AI persona focusing on the {domain} domain.
Evaluate the following discovered topic based on its relevance and significance to the {domain} ecosystem.
Provide an integer score (0-100) for each category, an overall_score (0-100), and a brief reasoning.

Title: {topic.title}
Source: {topic.source_name}
Content: {topic.summary}
"""
    try:
        return provider.generate_structured(prompt, response_schema=EditorialEvaluation)
    except Exception as e:
        logger.error(f"Editorial evaluation failed: {e}")
        err_msg = str(e)
        err_msg = re.sub(r'sk-[a-zA-Z0-9]+', 'sk-...', err_msg)
        err_msg = re.sub(r'tvly-[a-zA-Z0-9]+', 'tvly-...', err_msg)
        return EditorialEvaluation(
            relevance=50, novelty=50, technical_significance=50, 
            timeliness=50, source_quality=50, redundancy_risk=50, 
            overall_score=50, reasoning=f"Failed to evaluate: {err_msg}"
        )

def generate_codeblooded_post(topic: RawTopic, provider: OpenRouterProvider, name: str, domain: str, retry_count: int = 0) -> CodebloodedPostContent:
    extra_instruction = ""
    if retry_count > 0:
        extra_instruction = "CRITICAL: YOUR PREVIOUS POST WAS TOO LONG. You MUST write a conversational post under 100 WORDS MAXIMUM."
    else:
        extra_instruction = "Write a conversational post (35-80 words ideal, 100 words MAXIMUM)."
        
    system_prompt = get_system_prompt(name, domain)
    prompt = f"""
{system_prompt}

{extra_instruction}

Based on the following topic, write a simulated social media post. Remember: DO NOT summarize the whole article. Find ONE interesting thing and give your opinion on it.
You MUST also generate a concise editorial rationale explaining:
1. Why the topic was selected.
2. Why it is relevant NOW.
3. Why it was chosen over other candidates.
Write a single concise sentence for the rationale. Do not include hidden chain-of-thought.

Topic: {topic.title}
Source: {topic.source_name}
URL: {topic.source_url}
Content: {topic.summary}
"""
    try:
        content = provider.generate_structured(prompt, response_schema=CodebloodedPostContent)
        
        # Backend Sanitizer for em dashes and word count leakage
        sanitized_text = content.post_text
        sanitized_text = re.sub(r'[—–‒―]', '-', sanitized_text)
        sanitized_text = re.sub(r'(?i)word count:?\s*\d+', '', sanitized_text)
        sanitized_text = re.sub(r'(?i)\d+\s*words?', '', sanitized_text)
        sanitized_text = re.sub(r'\d+/\d+', '', sanitized_text)
        content.post_text = sanitized_text.strip()
        
        return content
    except Exception as e:
        logger.error(f"Post generation failed: {e}")
        return CodebloodedPostContent(
            post_text="Error generating post.",
            rationale="Error."
        )

def run_discovery_cycle(agent_id: Optional[str] = None):
    cycle_start = datetime.now()
    cycle_id = str(uuid.uuid4())
    
    state.status = "Running"
    state.current_operation = "Discovering raw topics via Tavily..."
    state.log(f"Starting new autonomous discovery cycle (ID: {cycle_id[:8]}).")
    
    cycle_record = {
        "cycle_id": cycle_id,
        "agent_id": agent_id,
        "started_at": cycle_start.isoformat(),
        "topics_discovered": 0,
        "topics_selected": 0,
        "topics_rejected": 0,
        "duplicates": 0,
        "posts_created": 0,
        "status": "Running"
    }
    
    # Dynamic Agent Settings
    name = "CODEBLOODED"
    domain = "AI and technology"
    if agent_id:
        agent = memory_store.get_agent(agent_id)
        if agent:
            name = agent.get("persona", {}).get("name", "CODEBLOODED")
            domain = agent.get("persona", {}).get("domain", "AI and technology")
            
    try:
        raw_topics = discover_topics(domain=domain)
        provider = OpenRouterProvider(api_key=settings.openrouter_api_key or "", model_name=settings.ai_model)
        
        state.current_operation = "Evaluating topics..."
        state.log(f"Discovered {len(raw_topics)} raw topics.")
        cycle_record["topics_discovered"] = len(raw_topics)
        
        evaluated_topics = []
        approved_topics = []
        
        for rt in raw_topics[:5]:
            memory_store.save_recent_topic({
                "agent_id": agent_id,
                "title": rt.title,
                "timestamp": datetime.now().isoformat()
            })
            
            if is_duplicate(rt, agent_id=agent_id):
                state.duplicate_topics_prevented += 1
                cycle_record["duplicates"] += 1
                state.log(f"Duplicate detected: {rt.title}")
                continue
                
            state.log(f"Evaluating with Nemotron: {rt.title}")
            eval_result = evaluate_topic(rt, provider, domain=domain)
            state.ai_requests_used += 1
            
            dt = DiscoveredTopic(
                title=rt.title,
                category=rt.category,
                source_name=rt.source_name,
                source_url=rt.source_url,
                summary=rt.summary,
                approved=False
            )
            
            if eval_result.overall_score >= settings.publish_threshold:
                dt.approved = True
                state.topics_approved += 1
                cycle_record["topics_selected"] += 1
                state.log(f"APPROVED (Score {eval_result.overall_score}): {rt.title}")
                approved_topics.append((rt, eval_result, dt))
            else:
                dt.approved = False
                dt.rejection_reason = eval_result.reasoning
                state.topics_rejected += 1
                cycle_record["topics_rejected"] += 1
                state.log(f"REJECTED (Score {eval_result.overall_score}): {rt.title}")
                memory_store.save_rejected_topic({
                    "agent_id": agent_id,
                    "topic": rt.title,
                    "timestamp": datetime.now().isoformat(),
                    "score": eval_result.overall_score,
                    "rejection_reason": eval_result.reasoning,
                    "source": rt.source_name
                })
            
            evaluated_topics.append(dt)

        if approved_topics:
            state.current_operation = "Generating post..."
            approved_topics.sort(key=lambda x: x[1].overall_score, reverse=True)
            best_raw, best_eval, best_dt = approved_topics[0]
            
            state.log(f"Generating post for: {best_raw.title}")
            
            # Word limit logic
            max_retries = 1
            post_content = None
            valid_post = False
            final_word_count = 0
            
            for attempt in range(max_retries + 1):
                post_content = generate_codeblooded_post(best_raw, provider, name=name, domain=domain, retry_count=attempt)
                state.ai_requests_used += 1
                final_word_count = count_words(post_content.post_text)
                
                if final_word_count <= 100:
                    valid_post = True
                    break
                else:
                    state.log(f"Post generation failed length check ({final_word_count} words). Attempting rewrite.")
            
            if valid_post and post_content:
                post_record = {
                    "id": str(uuid.uuid4()),
                    "agentId": agent_id,
                    "agent_id": agent_id,
                    "topic_title": best_raw.title,
                    "normalized_title": best_raw.title.lower(),
                    "post_text": post_content.post_text,
                    "word_count": final_word_count,
                    "source_urls": [best_raw.source_url],
                    "source_names": [best_raw.source_name],
                    "publication_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "why_selected": post_content.rationale,  # Backwards compatibility for UI
                    "why_now": post_content.rationale,       # Backwards compatibility for UI
                    "rationale": post_content.rationale,
                    "editorial_score": best_eval.overall_score,
                    "relevant_topic": best_raw.category
                }
                memory_store.save_post(post_record)
                state.posts_published += 1
                cycle_record["posts_created"] += 1
                state.log(f"Post published ({final_word_count} words).")
            else:
                state.log(f"Aborted publishing. Model failed to generate a post under 100 words.")
        else:
            state.log("No topics met the editorial threshold. Nothing published.")

        state.discovered_topics = evaluated_topics
        state.topics_discovered = len(evaluated_topics)
        state.last_discovery_time = datetime.now()
        
        cycle_record["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cycle_record["status"] = "Completed"
        state.log("Discovery cycle completed successfully.")
        
    except Exception as e:
        cycle_record["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cycle_record["status"] = "Error"
        cycle_record["error"] = str(e)
        state.log(f"Error during discovery cycle: {e}")
        logger.error(f"Discovery cycle failed: {e}")

    finally:
        # Always reset state so future cycles are not blocked
        state.status = "Idle"
        state.current_operation = "None"
        state.last_discovery_time = datetime.now()
        state.cycle_history.insert(0, cycle_record)
        if len(state.cycle_history) > 20:
            state.cycle_history.pop()
