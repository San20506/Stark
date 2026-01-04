"""
DEBUG SEARCH & LLM
"""
import sys

def test_ddg():
    print("\n1. Testing DuckDuckGo...")
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text("test", max_results=1))
        print(f"✅ DDG Success: {len(results)} results")
    except Exception as e:
        print(f"❌ DDG Failed: {e}")

def test_ollama():
    print("\n2. Testing Ollama...")
    try:
        import ollama
        res = ollama.chat(model='deepseek-r1:1.5b', messages=[{'role': 'user', 'content': 'hi'}])
        print(f"✅ Ollama Success: {res['message']['content'][:20]}")
    except Exception as e:
        print(f"❌ Ollama Failed: {e}")

if __name__ == "__main__":
    test_ddg()
    test_ollama()
