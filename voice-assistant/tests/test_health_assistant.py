"""
Tests for the health assistant module
"""
import unittest
from src.health_assistant import HealthAssistant

class TestHealthAssistant(unittest.TestCase):
    def setUp(self):
        """Set up test cases"""
        self.assistant = HealthAssistant()

    def test_health_topic_classification(self):
        """Test health topic classification"""
        # Test health-related query
        health_query = "What's a good diet for weight loss?"
        topics = self.assistant.classify_health_topic(health_query)
        self.assertTrue(len(topics) > 0, "Should detect health topics")
        
        # Test non-health query
        non_health_query = "What's the weather like today?"
        topics = self.assistant.classify_health_topic(non_health_query)
        self.assertEqual(len(topics), 0, "Should not detect health topics")

    def test_response_validation(self):
        """Test response validation"""
        # Test response with proper disclaimers
        good_response = """
        Here's a healthy diet plan.
        
        Important: This information is for educational purposes only.
        Please consult with a healthcare provider or registered dietitian.
        """
        topics = {"nutrition": {"requires_disclaimer": True}}
        valid, _ = self.assistant.validate_response(good_response, topics)
        self.assertTrue(valid, "Should accept response with proper disclaimers")
        
        # Test response without required disclaimers
        bad_response = "Here's a diet plan without any disclaimers."
        valid, feedback = self.assistant.validate_response(bad_response, topics)
        self.assertFalse(valid, "Should reject response without disclaimers")
        self.assertIn("disclaimer", feedback.lower())

if __name__ == '__main__':
    unittest.main()
