import sys
import os

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.tavily import discover_topics

def test_tavily():
    print("Testing Tavily Web Search...\n")
    try:
        topics = discover_topics()
        print(f"Discovered {len(topics)} topics.\n")
        
        for idx, t in enumerate(topics, 1):
            print(f"{idx}. {t.title}")
            print(f"   Source: {t.source_name}")
            print(f"   URL: {t.source_url}")
            print(f"   Summary: {t.summary}\n")
            
    except Exception as e:
        print(f"Tavily Test Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_tavily()
