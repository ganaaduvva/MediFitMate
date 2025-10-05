import pytest
from unittest.mock import Mock, patch
from fastapi import FastAPI, BackgroundTasks
from src.handlers.twilio_handler import TwilioHandler
from src.models.twilio_models import TwilioMessage

@pytest.fixture
def app():
    return FastAPI()

@pytest.fixture
def handler(app):
    handler = TwilioHandler(app)
    handler.client = Mock()
    handler.phone_number = "+14155238886"
    return handler

def test_create_twiml_response(handler):
    """Test creating TwiML response"""
    response = handler.create_twiml_response("Test message")
    assert "Test message" in response
    assert "<?xml" in response
    assert "<Message>" in response

def test_clean_markdown(handler):
    """Test markdown cleaning"""
    text = "# Header\n**Bold** *Italic*\n\n\nMultiple lines"
    cleaned = handler.clean_markdown(text)
    assert cleaned == "Header\nBold Italic\n\nMultiple lines"

@pytest.mark.asyncio
async def test_send_message(handler):
    """Test sending a single message"""
    # Mock the Twilio response
    mock_message = Mock()
    mock_message.sid = "test_sid"
    handler.client.messages.create.return_value = mock_message

    sid = await handler.send_message("Test message", "whatsapp:+1234567890")
    assert sid == "test_sid"
    
    # Verify Twilio client was called correctly
    handler.client.messages.create.assert_called_once_with(
        body="Test message",
        from_=f"whatsapp:{handler.phone_number}",
        to="whatsapp:+1234567890"
    )

@pytest.mark.asyncio
async def test_send_voice_message(handler):
    """Test sending voice message"""
    mock_message = Mock()
    mock_message.sid = "test_sid"
    handler.client.messages.create.return_value = mock_message

    response = await handler.send_voice_message(
        b"audio content",
        "whatsapp:+1234567890"
    )
    
    # Verify empty TwiML response
    assert response == '<?xml version=\'1.0\' encoding=\'UTF-8\'?><Response />'
    
    # Verify Twilio client was called with media
    call_args = handler.client.messages.create.call_args[1]
    assert call_args['body'] == "Here's your voice response:"
    assert call_args['to'] == "whatsapp:+1234567890"
    assert len(call_args['media_streams']) == 1

@pytest.mark.asyncio
async def test_send_message_parts(handler):
    """Test sending message parts"""
    background_tasks = BackgroundTasks()
    
    # Test short message
    response = await handler.send_message_parts(
        "Short message",
        "whatsapp:+1234567890",
        background_tasks
    )
    assert "Short message" in response
    assert "Part 1/" not in response

    # Test long message
    long_message = "x" * 2000
    response = await handler.send_message_parts(
        long_message,
        "whatsapp:+1234567890",
        background_tasks
    )
    assert "Part 1/2" in response

@pytest.mark.asyncio
async def test_download_media(handler):
    """Test downloading media"""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"test content"
        
        content = await handler.download_media(
            "https://example.com/media",
            ("test_sid", "test_token")
        )
        
        assert content == b"test content"
        mock_get.assert_called_once_with(
            "https://example.com/media",
            auth=("test_sid", "test_token")
        )

@pytest.mark.asyncio
async def test_message_limit_handling(handler):
    """Test handling of message limit errors"""
    background_tasks = BackgroundTasks()
    
    # Mock message limit error
    handler.client.messages.create.side_effect = Exception("63038")
    
    # Test long message that triggers limit
    long_message = "x" * 2000
    response = await handler.send_message_parts(
        long_message,
        "whatsapp:+1234567890",
        background_tasks
    )
    
    assert "Part 1/" in response
    # Background task will handle the error and send limit message