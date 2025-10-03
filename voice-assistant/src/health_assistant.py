"""
Health Assistant Module
Provides intelligent health topic classification and response generation
"""
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from cachetools import TTLCache
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Load configuration files
CONFIG_DIR = Path("config")

def load_config(filename: str) -> dict:
    """Load configuration from JSON file"""
    with open(CONFIG_DIR / filename, 'r') as f:
        return json.load(f)

class TopicScore(BaseModel):
    """Pydantic model for topic classification scores"""
    confidence: float = Field(..., ge=0.0, le=1.0)
    requires_disclaimer: bool
    referrals: List[str]

class HealthAssistant:
    def __init__(self):
        """Initialize the health assistant with embeddings model and configurations"""
        # Load configurations
        self.categories = load_config("health_categories.json")
        self.prompts = load_config("prompt_templates.json")
        self.disclaimers = load_config("disclaimer_templates.json")
        
        # Initialize embeddings model
        logger.info("Loading sentence transformer model...")
        self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Prepare category embeddings
        self.category_embeddings = self._prepare_category_embeddings()
        
        # Initialize response cache (24 hour TTL)
        self.response_cache = TTLCache(maxsize=1000, ttl=24*60*60)
        
        logger.info("Health Assistant initialized successfully")
    
    def _prepare_category_embeddings(self) -> Dict[str, np.ndarray]:
        """Pre-compute embeddings for each category's keywords"""
        embeddings = {}
        for category, config in self.categories.items():
            # Get embeddings for all keywords and move to CPU
            keyword_embeddings = self.embeddings_model.encode(
                config['keywords'],
                convert_to_tensor=True
            ).cpu()
            # Store mean embedding for category
            embeddings[category] = keyword_embeddings.mean(axis=0).cpu()
        return embeddings
    
    async def classify_health_topic(self, text: str) -> Dict[str, TopicScore]:
        """
        Classify input text into health categories using embeddings
        Returns dict of categories with confidence scores
        """
        # Get text embedding and move to CPU
        text_embedding = self.embeddings_model.encode(
            text,
            convert_to_tensor=True
        ).cpu()
        
        # Calculate similarity with each category
        scores = {}
        for category, category_embedding in self.category_embeddings.items():
            # Move category embedding to CPU before comparison
            category_embedding = category_embedding.cpu()
            similarity = float(cosine_similarity(
                text_embedding.reshape(1, -1).numpy(),
                category_embedding.reshape(1, -1).numpy()
            )[0][0])
            
            # Check if similarity exceeds category threshold
            if similarity > self.categories[category]['threshold']:
                scores[category] = TopicScore(
                    confidence=similarity,
                    requires_disclaimer=self.categories[category]['requires_disclaimer'],
                    referrals=self.categories[category]['professional_referral']
                )
        
        return scores
    
    def _get_relevant_disclaimers(self, topics: Dict[str, TopicScore]) -> List[str]:
        """Get relevant disclaimers based on detected topics"""
        disclaimers = [self.disclaimers['general']['educational']]
        
        for topic in topics:
            if topic in self.disclaimers['category_specific']:
                disclaimers.append(
                    self.disclaimers['category_specific'][topic]['general']
                )
        
        return disclaimers
    
    async def get_dynamic_prompt(self, topics: Dict[str, TopicScore]) -> str:
        """Generate context-aware system prompt based on detected topics"""
        prompt_parts = [self.prompts['base_prompt']]
        
        # Add topic-specific prompts
        for topic in topics:
            if topic in self.prompts['category_prompts']:
                prompt_parts.append(self.prompts['category_prompts'][topic])
        
        # Add relevant disclaimers
        disclaimers = self._get_relevant_disclaimers(topics)
        prompt_parts.extend(disclaimers)
        
        # Add safety guidelines if needed
        if any(topic.requires_disclaimer for topic in topics.values()):
            prompt_parts.append(self.prompts['safety_guidelines']['medical_emergency'])
        
        return "\n\n".join(prompt_parts)
    
    async def validate_response(
        self,
        response: str,
        topics: Dict[str, TopicScore]
    ) -> Tuple[bool, str]:
        """
        Validate response for medical safety and required elements
        Returns (valid, feedback)
        """
        issues = []
        
        # Check for required disclaimers
        if any(topic.requires_disclaimer for topic in topics.values()):
            if "consult" not in response.lower():
                issues.append("Missing healthcare consultation recommendation")
            if "not medical advice" not in response.lower():
                issues.append("Missing medical advice disclaimer")
        
        # Check for professional referrals
        referrals = [ref for topic in topics.values() for ref in topic.referrals]
        if referrals and not any(ref.lower() in response.lower() for ref in referrals):
            issues.append("Missing professional referral suggestion")
        
        # Check response length and structure
        if len(response.split()) < 20:
            issues.append("Response too short - may lack sufficient detail")
        if len(response.split('\n')) < 2:
            issues.append("Response lacks proper formatting/structure")
        
        valid = len(issues) == 0
        feedback = "\n".join(issues) if issues else ""
        
        return valid, feedback
    
    async def process_query(self, text: str) -> str:
        """
        Main entry point for processing health queries
        Returns appropriate response with disclaimers
        """
        try:
            # Check cache first
            cache_key = hash(text)
            if cache_key in self.response_cache:
                logger.info("Cache hit - returning cached response")
                return self.response_cache[cache_key]
            
            # Classify health topics
            topics = await self.classify_health_topic(text)
            
            # If no health topics detected, return redirect message
            if not topics:
                logger.info("No health topics detected - redirecting")
                return (
                    "I'm a specialized health and wellness assistant. "
                    "I notice your question isn't directly related to health or wellness. "
                    "Would you like to discuss how this topic might relate to your health, "
                    "or would you prefer to ask a different health-related question?"
                )
            
            # Get dynamic prompt based on detected topics
            prompt = await self.get_dynamic_prompt(topics)
            
            # TODO: Generate response using Cerebras
            # For now, return a placeholder
            response = "This is a placeholder response. Implementation pending."
            
            # Validate response
            valid, feedback = await self.validate_response(response, topics)
            if not valid:
                logger.warning(f"Response validation failed: {feedback}")
                # TODO: Regenerate response with feedback
            
            # Cache valid response
            self.response_cache[cache_key] = response
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return (
                "I apologize, but I encountered an error processing your request. "
                "Please try again or rephrase your question."
            )
