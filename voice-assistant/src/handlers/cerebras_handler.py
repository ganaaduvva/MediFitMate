"""
Cerebras LLM Handler
Manages conversation history and generates responses using Cerebras AI
"""
import os
import logging
import re
from typing import List, Dict
from cerebras.cloud.sdk import Cerebras

logger = logging.getLogger(__name__)


def clean_markdown_for_display(text: str) -> str:
    """Convert markdown to readable plain text with proper formatting"""
    # Remove bold markers but keep the text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Remove italic markers
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    
    # Convert numbered lists to bullet points with line breaks
    text = re.sub(r'^\d+\.\s+', '\n• ', text, flags=re.MULTILINE)
    
    # Convert markdown bullet points to proper bullets with spacing
    text = re.sub(r'^\*\s+', '\n• ', text, flags=re.MULTILINE)
    text = re.sub(r'^-\s+', '\n• ', text, flags=re.MULTILINE)
    
    # Preserve paragraph breaks (important!)
    # Don't collapse double line breaks
    
    # Clean up excessive whitespace but preserve structure
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 line breaks
    
    return text.strip()


class CerebrasHandler:
    """Handle Cerebras LLM interactions with conversation management"""
    
    def __init__(self, api_key: str, model: str = "llama-3.1-8b"):
        """
        Initialize Cerebras handler
        
        Args:
            api_key: Cerebras API key
            model: Model name to use (default: llama-3.1-8b)
        """
        self.client = Cerebras(api_key=api_key)
        self.model = model
        self.conversations: Dict[str, List[Dict]] = {}  # room_id -> history
        
    def get_conversation_history(self, room_id: str) -> List[Dict]:
        """Get conversation history for a room"""
        if room_id not in self.conversations:
            self.conversations[room_id] = []
        return self.conversations[room_id]
    
    def add_message(self, room_id: str, role: str, content: str):
        """Add a message to conversation history"""
        history = self.get_conversation_history(room_id)
        history.append({"role": role, "content": content})
        
        # Keep only last 20 messages to avoid context overflow
        if len(history) > 20:
            self.conversations[room_id] = history[-20:]
    
    def clear_history(self, room_id: str):
        """Clear conversation history for a room"""
        self.conversations[room_id] = []
    
    def generate_response(
        self, 
        room_id: str, 
        user_message: str,
        system_prompt: str = """You are a helpful health and wellness assistant. When formatting your responses:
1. Use clear paragraphs with proper spacing
2. Use bullet points (•) for lists
3. Include all details without truncation
4. For meal plans and schedules:
   - List each item on a new line
   - Include all nutritional information
   - Complete all sections fully
5. Never leave responses incomplete
6. Use proper line breaks between sections""",
        max_tokens: int = 2000,  # Increased for longer responses
        temperature: float = 0.7
    ) -> str:
        """
        Generate a response using Cerebras Chat API
        
        Args:
            room_id: Unique room identifier
            user_message: User's input message
            system_prompt: System instruction for the AI
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            Generated response text
        """
        try:
            # Add user message to history
            self.add_message(room_id, "user", user_message)
            
            # Get conversation history
            history = self.get_conversation_history(room_id)
            
            logger.info(f"Generating response for room {room_id}")
            
            # Try Chat API (modern, scalable approach)
            try:
                messages = [{"role": "system", "content": system_prompt}]
                for msg in history[-10:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                reply = response.choices[0].message.content.strip()
                logger.info("✅ Used Chat API")
                
            except Exception as chat_error:
                # Fallback to completions API if chat not available
                logger.warning(f"Chat API failed, using completions fallback")
                
                prompt = f"{system_prompt}\n\n"
                for msg in history[-10:]:
                    role_label = "User" if msg["role"] == "user" else "Assistant"
                    prompt += f"{role_label}: {msg['content']}\n"
                prompt += "Assistant:"
                
                response = self.client.completions.create(
                    model=self.model,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=["\nUser:"],  # Stop at next user turn
                )
                reply = response.choices[0].text.strip()
                
                # Clean up any echoed conversation format
                if "User:" in reply:
                    reply = reply.split("User:")[0].strip()
            
            # Clean up markdown formatting for better display
            reply = clean_markdown_for_display(reply)
            
            # Add assistant response to history
            self.add_message(room_id, "assistant", reply)
            
            logger.info(f"Generated response: {reply[:50]}...")
            return reply
            
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return "I apologize, but I encountered an error processing your request." 