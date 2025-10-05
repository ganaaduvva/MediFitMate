import os
import json
import logging
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from cachetools import TTLCache
from cerebras.cloud.sdk import Cerebras

class CerebrasHandler:
    def __init__(self):
        self.api_key = os.getenv('CEREBRAS_API_KEY')
        if not self.api_key:
            raise ValueError("CEREBRAS_API_KEY environment variable is required")
            
        self.client = Cerebras(api_key=self.api_key)
        self.model = "llama-4-scout-17b-16e-instruct"  # Using the latest instruct model
        self.context_window = 4096
        
        # Cache for frequently asked questions (30 minute TTL)
        self.response_cache = TTLCache(maxsize=100, ttl=1800)
        
        # Load medical terminology and conditions
        self.load_medical_knowledge()
        
    def load_medical_knowledge(self):
        """Load medical terminology and conditions for enhanced responses"""
        try:
            with open('config/medical_terms.json', 'r') as f:
                self.medical_terms = json.load(f)
            with open('config/health_conditions.json', 'r') as f:
                self.health_conditions = json.load(f)
        except FileNotFoundError:
            logging.warning("Medical knowledge files not found, using defaults")
            self.medical_terms = {}
            self.health_conditions = {}
    
    def generate_response(
        self, 
        query: str, 
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict] = None
    ) -> Tuple[str, Dict]:
        # Initialize conversation history if None
        if conversation_history is None:
            conversation_history = []
            
        # Keep last 3 exchanges for context
        if len(conversation_history) > 3:
            conversation_history = conversation_history[-3:]
        """
        Generate a health-focused response using Cerebras LLM
        
        Args:
            query: User's question
            conversation_history: List of previous exchanges
            user_context: Additional context about the user
            
        Returns:
            Tuple of (response_text, metadata)
        """
        # Check cache first
        cache_key = f"{query}_{len(conversation_history or [])}"
        if cache_key in self.response_cache:
            return self.response_cache[cache_key]

        # Build enhanced system prompt
        system_prompt = self._build_system_prompt(user_context)
        
        # Prepare conversation context
        context = self._prepare_conversation_context(conversation_history)
        
        # Identify medical terms in query
        medical_terms = self._extract_medical_terms(query)
        
        try:
            # Generate response using chat completions
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    messages.append({"role": "user", "content": msg["user"]})
                    messages.append({"role": "assistant", "content": msg["assistant"]})
            
            # Add current query
            messages.append({"role": "user", "content": query})
            
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                max_tokens=500  # Limit response length
            )
            
            response = chat_completion.choices[0].message.content
            
            # Process and validate response
            processed_response, metadata = self._process_response(
                response, query, medical_terms
            )
            
            # Cache the response if it's valid
            if metadata.get("is_valid", False):
                self.response_cache[cache_key] = (processed_response, metadata)
            
            return processed_response, metadata
            
        except Exception as e:
            logging.error(f"Cerebras API error: {e}")
            return (
                "I apologize, but I encountered an error. Please try again.",
                {"error": str(e), "is_valid": False}
            )

    def _build_system_prompt(self, user_context: Optional[Dict] = None) -> str:
        """Build a comprehensive system prompt with health focus"""
        prompt = """You are a health and wellness assistant. Your primary goal is to provide clear, helpful information about health-related topics.

        STRICT RULES:
        1. ONLY answer health and wellness related questions
        2. For non-health questions, politely explain that you can only assist with health topics
        3. If a question involves emergency medical situations, ALWAYS direct to immediate medical care
        4. Never provide specific medical treatment advice or diagnoses
        5. For one-word responses like "yes", "no", or "okay", check previous conversation for context
        6. If a response seems to be answering a previous question, continue that discussion

        RESPONSE STRUCTURE:
        1. First, give a clear, simple answer that anyone can understand
        2. If using medical terms, immediately explain them in simple words
        3. Add 1-2 practical tips or recommendations when relevant
        4. Include a brief disclaimer when:
           - Discussing serious health conditions
           - Mentioning medications or treatments
           - Addressing emergency situations
           - Suggesting lifestyle changes

        TONE AND STYLE:
        - Use conversational, friendly language
        - Avoid technical jargon unless necessary
        - Be empathetic but professional
        - Keep responses concise and focused
        - Make complex topics easy to understand
        - Maintain context from previous messages
        - Reference previous answers when relevant

        ALWAYS REMEMBER:
        - You are an information resource, not a medical professional
        - Encourage professional medical consultation when appropriate
        - Stay within the scope of general health information
        - Prioritize user safety and well-being
        """
        
        if user_context:
            prompt += f"\n\nUser Context:\n{json.dumps(user_context, indent=2)}"
            
        return prompt

    def _prepare_conversation_context(
        self, 
        history: Optional[List[Dict[str, str]]]
    ) -> str:
        """Prepare conversation history for context"""
        if not history:
            return ""
            
        # Take last 5 exchanges to stay within context window
        recent_history = history[-5:]
        context = []
        
        for exchange in recent_history:
            context.extend([
                f"User: {exchange['user']}",
                f"Assistant: {exchange['assistant']}"
            ])
            
        return "\n".join(context)

    def _extract_medical_terms(self, text: str) -> List[str]:
        """Extract medical terminology from text"""
        found_terms = []
        
        # Check against loaded medical terms
        for term, info in self.medical_terms.items():
            if term.lower() in text.lower():
                found_terms.append({
                    "term": term,
                    "category": info.get("category"),
                    "definition": info.get("definition")
                })
                
        return found_terms

    def _format_prompt(
        self, 
        system_prompt: str,
        context: str,
        query: str,
        medical_terms: List[Dict]
    ) -> str:
        """Format the complete prompt with all context"""
        prompt_parts = [
            system_prompt,
            "\nConversation History:",
            context,
            "\nIdentified Medical Terms:",
            json.dumps(medical_terms, indent=2) if medical_terms else "None",
            "\nCurrent Query:",
            query,
            "\nAssistant:"
        ]
        
        return "\n".join(prompt_parts)

    def _process_response(
        self, 
        response: str,
        original_query: str,
        medical_terms: List[Dict]
    ) -> Tuple[str, Dict]:
        """Process and validate the LLM response"""
        # Clean up response text
        cleaned_response = self._clean_response_text(response)
        
        # Validate response
        validation_results = self._validate_response(
            cleaned_response, 
            original_query,
            medical_terms
        )
        
        # Add disclaimers if needed
        final_response = self._add_disclaimers(cleaned_response, validation_results)
        
        # Prepare metadata
        metadata = {
            "timestamp": datetime.utcnow().isoformat(),
            "model": self.model,
            "medical_terms": medical_terms,
            "validation_results": validation_results,
            "is_valid": validation_results.get("is_valid", False),
            "confidence_score": validation_results.get("confidence", 0.0)
        }
        
        return final_response, metadata

    def _clean_response_text(self, text: str) -> str:
        """Clean up response text for better formatting"""
        # Remove any echoed conversation format
        text = text.replace("User:", "").replace("Assistant:", "")
        
        # Clean up whitespace
        text = "\n".join(line.strip() for line in text.split("\n"))
        
        # Ensure proper spacing around sections
        text = text.replace("\n\n\n", "\n\n")
        
        return text.strip()

    def _validate_response(
        self, 
        response: str,
        query: str,
        medical_terms: List[Dict]
    ) -> Dict:
        """Validate response for health focus and structure"""
        validation = {
            "is_valid": True,
            "confidence": 0.9,
            "warnings": [],
            "requires_disclaimer": False
        }
        
        # Check if response is health-related
        non_health_indicators = ["I can only assist with health", "I cannot provide information about"]
        if any(indicator in response for indicator in non_health_indicators):
            validation["is_valid"] = True  # Valid response for non-health query
            return validation

        # Check for clear explanation of medical terms
        for term in medical_terms:
            term_loc = response.lower().find(term["term"].lower())
            if term_loc != -1:
                next_50_chars = response[term_loc:term_loc+50].lower()
                if "means" not in next_50_chars and "is" not in next_50_chars:
                    validation["warnings"].append(f"Medical term '{term['term']}' may need explanation")
                    validation["confidence"] *= 0.9


        # Check for appropriate disclaimers
        emergency_keywords = ["emergency", "urgent", "severe", "critical", "life-threatening"]
        treatment_keywords = ["medication", "treatment", "therapy", "surgery"]
        
        if any(keyword in query.lower() for keyword in emergency_keywords):
            validation["requires_disclaimer"] = True
            if "seek immediate medical attention" not in response.lower():
                validation["warnings"].append("Missing emergency disclaimer")
                validation["confidence"] *= 0.8

        if any(keyword in response.lower() for keyword in treatment_keywords):
            validation["requires_disclaimer"] = True
            if "consult" not in response.lower() and "healthcare provider" not in response.lower():
                validation["warnings"].append("Missing medical consultation disclaimer")
                validation["confidence"] *= 0.8

        # Validate response structure
        if len(response.split()) < 50:  # Too short
            validation["warnings"].append("Response may be too brief")
            validation["confidence"] *= 0.8
        elif len(response.split()) > 200:  # Too long
            validation["warnings"].append("Response may be too detailed")
            validation["confidence"] *= 0.9

        # Update final validity
        validation["is_valid"] = validation["confidence"] > 0.7
        
        return validation

    def _add_disclaimers(self, response: str, validation: Dict) -> str:
        """Add appropriate disclaimers to response"""
        if not validation.get("requires_disclaimer"):
            return response
            
        disclaimers = []
        
        if "emergency" in validation.get("warnings", []):
            disclaimers.append(
                "\n\nIMPORTANT: If this is a medical emergency, "
                "please call emergency services or visit the nearest emergency room immediately."
            )
            
        if validation["confidence"] < 0.8:
            disclaimers.append(
                "\n\nNote: This information is for educational purposes only. "
                "Please consult with a healthcare professional for medical advice."
            )
            
        return response + "".join(disclaimers)