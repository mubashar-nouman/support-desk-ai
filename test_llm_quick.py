"""Quick LLM client test."""
import asyncio
from src.llm import get_llm_client, LLMMessage

async def test():
    # This will test client initialization
    # (Won't make real API calls without valid keys)
    try:
        client = get_llm_client()
        print(f"✅ Client initialized: {client}")
        print(f"   Primary: {client.primary_provider_name}")
        print(f"   Fallback: {client.fallback_provider is not None}")
        
        # Test token counting
        tokens = client.count_tokens("Hello world")
        print(f"✅ Token counting works: {tokens} tokens")
        
        print("\n✅ LLM Client validation passed!")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test())
