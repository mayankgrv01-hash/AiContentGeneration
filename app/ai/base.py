from abc import ABC, abstractmethod

from typing import Any

class AIProvider(ABC):
    """Base class for all AI providers to ensure a consistent interface."""
    
    @abstractmethod
    def generate_text(self, prompt: str, use_search: bool = False) -> str:
        """Generates text from the provider based on a prompt."""
        pass
        
    @abstractmethod
    def generate_structured(self, prompt: str, response_schema: type, use_search: bool = False) -> Any:
        """Generates structured output based on a pydantic schema."""
        pass

