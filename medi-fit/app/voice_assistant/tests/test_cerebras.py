import os
import asyncio
from dotenv import load_dotenv
from src.handlers.cerebras_handler import CerebrasHandler

async def test_cerebras_chat():
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize the handler
        handler = CerebrasHandler()
        
        # Test a health-related query
        query = "What are the symptoms of dehydration?"
        response, metadata = await handler.generate_response(
            query=query,
            conversation_history=None,
            user_context={"type": "health_query", "topic": "general_health"}
        )
        
        print("\nTest Results:")
        print("-" * 50)
        print(f"Query: {query}")
        print("-" * 50)
        print(f"Response: {response}")
        print("-" * 50)
        print(f"Metadata: {metadata}")
        
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_cerebras_chat())
