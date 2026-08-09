from openai import OpenAI
from typing import Any, Type, Optional
from app.ai.base import AIProvider
from app.logging_config import logger
from app.state import state
import json

class OpenRouterProvider(AIProvider):
    """AI Provider implementation for OpenRouter (e.g. Nemotron)."""
    
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        logger.info(f"Initializing OpenRouter provider with model {model_name}...")
        try:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
            )
            logger.info("OpenRouter provider initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter provider: {e}")
            raise
            
        # Fallback NVIDIA client setup
        self.nvidia_client = None
        from app.config import settings
        if settings.nvidia_api_key:
            try:
                self.nvidia_client = OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=settings.nvidia_api_key,
                )
                logger.info("NVIDIA native API fallback client initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize NVIDIA native fallback: {e}")
            
    def generate_text(self, prompt: str, use_search: bool = False) -> str:
        """Generates text using the OpenRouter API with NVIDIA fallback."""
        if use_search:
            logger.warning("Search grounded generation is not directly supported via OpenRouter in this implementation.")
            
        try:
            logger.info(f"Generating text with model {self.model_name}...")
            state.ai_requests_used += 1
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenRouter generate_text failed: {e}. Checking fallback...")
            if self.nvidia_client:
                try:
                    logger.info("Attempting fallback generation with native NVIDIA API...")
                    response = self.nvidia_client.chat.completions.create(
                        model="nvidia/nemotron-3-ultra-550b-a55b",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=1,
                        top_p=0.95,
                        max_tokens=16384,
                        extra_body={"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 16384}
                    )
                    return response.choices[0].message.content or ""
                except Exception as ex:
                    logger.error(f"NVIDIA Fallback failed: {ex}")
                    raise ex
            raise e

    def generate_structured(self, prompt: str, response_schema: Type, use_search: bool = False) -> Any:
        """Generates structured output based on a pydantic schema using OpenRouter with NVIDIA fallback."""
        if use_search:
            logger.warning("Search grounded generation is not directly supported via OpenRouter in this implementation.")
            
        schema_json = response_schema.model_json_schema()
        full_prompt = f"{prompt}\n\nYou MUST return valid JSON matching this schema:\n{json.dumps(schema_json)}\nDo not include markdown blocks like ```json."

        try:
            logger.info(f"Generating structured output with model {self.model_name}...")
            state.ai_requests_used += 1
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": full_prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content or "{}"
        except Exception as e:
            logger.error(f"OpenRouter generate_structured failed: {e}. Checking fallback...")
            if self.nvidia_client:
                try:
                    logger.info("Attempting fallback structured generation with native NVIDIA API...")
                    response = self.nvidia_client.chat.completions.create(
                        model="nvidia/nemotron-3-ultra-550b-a55b",
                        messages=[{"role": "user", "content": full_prompt}],
                        temperature=1,
                        top_p=0.95,
                        max_tokens=16384,
                        extra_body={"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 16384}
                    )
                    content = response.choices[0].message.content or "{}"
                except Exception as ex:
                    logger.error(f"NVIDIA Fallback failed: {ex}")
                    raise ex
            else:
                raise e
            
        # Clean up potential markdown formatting if the model disobeys
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        data = json.loads(content)
        return response_schema(**data)
