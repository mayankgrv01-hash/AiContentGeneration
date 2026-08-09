import sys
import os

# Add the root directory to sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.ai.gemini import GeminiProvider
from app.logging_config import logger
from pydantic import ValidationError

def run_test():
    logger.info("Starting Gemini test...")
    try:
        # Check if API key is provided
        if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
            logger.error("GEMINI_API_KEY is not set or is still the default placeholder.")
            sys.exit(1)
            
        provider = GeminiProvider(api_key=settings.gemini_api_key)
        
        prompt = "What is one important recent development in AI? Be concise."
        logger.info(f"Sending prompt to Gemini: '{prompt}'")
        
        response = provider.generate_text(prompt)
        logger.info("Gemini test succeeded.")
        print(f"\n--- Gemini Response ---\n{response}\n-----------------------\n")
        
    except ValidationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Gemini test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_test()
