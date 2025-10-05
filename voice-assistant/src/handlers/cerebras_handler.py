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
                model=self.model
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
        prompt = """You are a knowledgeable health assistant powered by Cerebras AI.
        
        Your core responsibilities:
        1. Provide accurate, evidence-based health information
        2. Use appropriate medical terminology while explaining concepts clearly
        3. Include relevant health disclaimers and warnings
        4. Recommend professional medical consultation when appropriate
        5. Stay within your scope of knowledge
        
        Response Guidelines:
        - Structure responses clearly with sections and bullet points
        - Include relevant medical terms with explanations
        - Add context-appropriate disclaimers
        - Cite reliable health sources when possible
        - Clearly indicate when professional medical advice is needed
        
        Important Disclaimers:
        - You are not a substitute for professional medical advice
        - Emergency situations require immediate medical attention
        - Individual health conditions require personalized medical care
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
        """Validate response for medical accuracy and completeness"""
        validation = {
            "is_valid": True,
            "confidence": 0.9,  # Default high confidence
            "warnings": [],
            "requires_disclaimer": False
        }
        
        # Check for medical terms consistency
        for term in medical_terms:
            if term["term"] not in response:
                validation["warnings"].append(
                    f"Response should address medical term: {term['term']}"
                )
                validation["confidence"] *= 0.9

        # Check for appropriate disclaimers
        if any(keyword in query.lower() for keyword in ["emergency", "urgent", "severe"]):
            validation["requires_disclaimer"] = True
            if "emergency" not in response.lower():
                validation["warnings"].append("Missing emergency disclaimer")
                validation["confidence"] *= 0.8

        # Validate response length
        if len(response.split()) < 20:
            validation["warnings"].append("Response may be too short")
            validation["confidence"] *= 0.7

        # Update final validity
        validation["is_valid"] = validation["confidence"] > 0.6
        
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