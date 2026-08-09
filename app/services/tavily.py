from tavily import TavilyClient
from typing import List, Optional
from app.config import settings
from app.logging_config import logger
from app.state import state
# Import RawTopic from discovery to avoid circular if discovery imports tavily
from pydantic import BaseModel

class RawTopic(BaseModel):
    title: str
    category: str
    source_name: str
    source_url: str
    summary: str

def discover_topics(domain: Optional[str] = None) -> List[RawTopic]:
    logger.info("Starting live topic discovery via Tavily...")
    
    if not settings.tavily_api_key:
        state.tavily_status = "Error"
        raise ValueError("TAVILY_API_KEY is not configured.")
        
    client = TavilyClient(api_key=settings.tavily_api_key)
    
    import random
    
    if domain:
        query = f"latest major developments in {domain}"
        clean_category = domain
    else:
        categories = [
            "AI models and LLMs state-of-the-art releases",
            "autonomous AI agents and workflow frameworks",
            "AI infrastructure compute and model serving",
            "AI security vulnerabilities and alignment defense",
            "open-source AI models and developer libraries",
            "AI developer tools and automated coding assistants",
            "AI research breakthroughs and academic papers",
            "AI hardware accelerators and GPU chips",
            "robotics physical AI and humanoid control systems"
        ]
        
        selected_category = random.choice(categories)
        query = f"latest major developments in {selected_category}"
        
        category_map = {
            "AI models and LLMs state-of-the-art releases": "AI Models",
            "autonomous AI agents and workflow frameworks": "AI Agents",
            "AI infrastructure compute and model serving": "AI Infrastructure",
            "AI security vulnerabilities and alignment defense": "AI Security",
            "open-source AI models and developer libraries": "Open Source AI",
            "AI developer tools and automated coding assistants": "Developer Tools",
            "AI research breakthroughs and academic papers": "AI Research",
            "AI hardware accelerators and GPU chips": "AI Hardware",
            "robotics physical AI and humanoid control systems": "Robotics"
        }
        clean_category = category_map.get(selected_category, "AI Development")
    
    logger.info(f"Using search query: '{query}'")
    try:
        state.tavily_requests_used += 1
        response = client.search(
            query=query,
            search_depth="advanced",
            topic="general",
            days=2,
            max_results=10
        )
        
        state.tavily_status = "Connected"
        
        raw_topics = []
        for result in response.get("results", []):
            raw_topics.append(RawTopic(
                title=result.get("title", "Unknown Title"),
                category=clean_category,
                source_name=result.get("url", "").split("/")[2] if "url" in result else "Unknown Source",
                source_url=result.get("url", ""),
                summary=result.get("content", "No summary available.")
            ))
            
        logger.info(f"Tavily discovered {len(raw_topics)} topics under category '{clean_category}'.")
        return raw_topics
    except Exception as e:
        state.tavily_status = "Error"
        logger.error(f"Error communicating with Tavily: {e}")
        raise
