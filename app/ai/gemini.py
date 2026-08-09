from google import genai
from google.genai import types
from app.ai.base import AIProvider
from app.logging_config import logger
from app.state import state
from typing import Any, Optional, Type
import json

class GeminiProvider(AIProvider):
    """AI Provider implementation for Google's Gemini."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-3.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        logger.info("Initializing Gemini provider...")
        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info("Gemini provider initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini provider: {e}")
            raise
            
    def _get_config(self, use_search: bool, response_schema: Optional[Type] = None) -> Optional[types.GenerateContentConfig]:
        """Helper to build Gemini config."""
        kwargs = {}
        if use_search:
            kwargs["tools"] = [{"google_search": {}}]
        if response_schema:
            kwargs["response_mime_type"] = "application/json"
            kwargs["response_schema"] = response_schema
            
        return types.GenerateContentConfig(**kwargs) if kwargs else None
        
    def generate_text(self, prompt: str, use_search: bool = False) -> str:
        """Generates text using the Gemini API."""
        try:
            logger.info(f"Generating text with model {self.model_name} (search: {use_search})...")
            state.ai_requests_used += 1
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self._get_config(use_search)
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Error generating text with Gemini: {e}")
            raise

    def generate_structured(self, prompt: str, response_schema: Type, use_search: bool = False) -> Any:
        """Generates structured output based on a pydantic schema using Gemini."""
        try:
            logger.info(f"Generating structured output with model {self.model_name} (search: {use_search})...")
            state.ai_requests_used += 1
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self._get_config(use_search, response_schema)
            )
            # The google-genai library returns the parsed object in response.parsed
            if hasattr(response, "parsed") and response.parsed is not None:
                return response.parsed
                
            # Fallback if parsed isn't populated for some reason (e.g. SDK version differences)
            data = json.loads(response.text or "{}")
            return response_schema(**data)
            
        except Exception as e:
            logger.error(f"Error generating structured text with Gemini: {e}")
            raise
