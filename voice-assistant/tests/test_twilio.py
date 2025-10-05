import os
import json
from dotenv import load_dotenv
from src.app import app

def test_message_webhook():
    """Test the WhatsApp message webhook"""
    # Load environment variables
    load_dotenv()
    
    # Create a test client
    client = app.test_client()
    
    # Test data
    test_data = {
        'Body': 'What are common causes of headaches?',
        'From': 'whatsapp:+1234567890'
    }
    
    # Send a POST request to the webhook
    response = client.post(
        '/webhook/message',
        data=test_data
    )
    
    print("\nTest Results:")
    print("-" * 50)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.data.decode()}")
    
    # Assert response is valid
    assert response.status_code == 200
    assert b'<?xml version="1.0" encoding="UTF-8"?><Response>' in response.data

if __name__ == "__main__":
    test_message_webhook()
