import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from src.app import app
import json

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_webhook_no_content():
    """Test webhook with no content"""
    response = client.post("/webhook", data={})
    assert response.status_code == 400
    assert "No message content" in response.text

@patch('src.handlers.cerebras_handler.CerebrasHandler')
def test_webhook_text_message(mock_cerebras):
    """Test webhook with text message"""
    # Mock Cerebras response
    mock_cerebras.return_value.generate_response.return_value = (
        "Test response",
        {"type": "text"}
    )

    # Simulate a text message
    data = {
        'MessageType': 'text',
        'Body': 'Test message',
        'From': 'whatsapp:+1234567890',
        'To': 'whatsapp:+14155238886',
        'MessageSid': 'test_sid'
    }
    
    response = client.post("/webhook", data=data)
    assert response.status_code == 200
    assert 'Test response' in response.text

@patch('src.handlers.cerebras_handler.CerebrasHandler')
def test_webhook_format_selection(mock_cerebras):
    """Test format selection flow"""
    # First message should trigger format selection
    data = {
        'MessageType': 'text',
        'Body': 'Test message',
        'From': 'whatsapp:+1234567890',
        'To': 'whatsapp:+14155238886',
        'MessageSid': 'test_sid'
    }
    
    response = client.post("/webhook", data=data)
    assert response.status_code == 200
    assert 'How would you like to receive' in response.text

    # Select format (1 for text)
    data['Body'] = '1'
    response = client.post("/webhook", data=data)
    assert response.status_code == 200
    assert 'text format' in response.text

@patch('deepgram.Deepgram')
@patch('src.handlers.cerebras_handler.CerebrasHandler')
async def test_webhook_voice_message(mock_cerebras, mock_deepgram):
    """Test webhook with voice message"""
    # Mock Deepgram transcription
    mock_transcription = {
        'results': {
            'channels': [{
                'alternatives': [{
                    'transcript': 'Test voice message'
                }]
            }]
        }
    }
    mock_deepgram.return_value.transcription.sync_prerecorded.return_value = mock_transcription

    # Mock Cerebras response
    mock_cerebras.return_value.generate_response.return_value = (
        "Test response",
        {"type": "text"}
    )

    # Simulate a voice message
    data = {
        'MessageType': 'audio',
        'MediaUrl0': 'https://example.com/audio.ogg',
        'From': 'whatsapp:+1234567890',
        'To': 'whatsapp:+14155238886',
        'MediaContentType0': 'audio/ogg',
        'MessageSid': 'test_sid'
    }
    
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"test audio content"
        
        response = client.post("/webhook", data=data)
        assert response.status_code == 200
        assert 'I heard: ' in response.text
        assert 'Test voice message' in response.text

def test_webhook_format_change():
    """Test format change command"""
    data = {
        'MessageType': 'text',
        'Body': 'change format',
        'From': 'whatsapp:+1234567890',
        'To': 'whatsapp:+14155238886',
        'MessageSid': 'test_sid'
    }
    
    response = client.post("/webhook", data=data)
    assert response.status_code == 200
    assert 'How would you like to receive' in response.text

@pytest.mark.asyncio
async def test_long_message_splitting():
    """Test long message splitting functionality"""
    long_message = "x" * 2000  # Message longer than 1500 chars
    data = {
        'MessageType': 'text',
        'Body': long_message,
        'From': 'whatsapp:+1234567890',
        'To': 'whatsapp:+14155238886',
        'MessageSid': 'test_sid'
    }
    
    response = client.post("/webhook", data=data)
    assert response.status_code == 200
    assert 'Part 1/' in response.text