import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.ai.openrouter import OpenRouterProvider

def test_nemotron():
    print(f"Testing OpenRouter Provider with model: {settings.ai_model}...\n")
    
    if not settings.openrouter_api_key:
        print("OPENROUTER_API_KEY is not set.")
        sys.exit(1)
        
    try:
        provider = OpenRouterProvider(
            api_key=settings.openrouter_api_key,
            model_name=settings.ai_model
        )
        
        prompt = "Explain in two sentences what an autonomous AI agent is."
        print(f"Sending prompt: '{prompt}'\n")
        
        response = provider.generate_text(prompt)
        
        print("--- OpenRouter Response ---")
        print(response)
        print("---------------------------")
        print("\nRequest SUCCESS.")
        
    except Exception as e:
        print(f"Request FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_nemotron()
