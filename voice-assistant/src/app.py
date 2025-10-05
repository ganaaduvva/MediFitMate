import os
import logging
from typing import Dict, List
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, PlainTextResponse
from google.cloud import texttospeech
from deepgram import Deepgram
from dotenv import load_dotenv

from src.models.twilio_models import TwilioMessage, UserPreference
from src.handlers.twilio_handler import TwilioHandler
from src.handlers.cerebras_handler import CerebrasHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Health Assistant Webhook",
    description="A WhatsApp-based health and wellness assistant",
    version="1.0.0"
)

# Initialize handlers
twilio_handler = TwilioHandler(app)
cerebras_handler = CerebrasHandler()
tts_client = texttospeech.TextToSpeechClient()

# Store user preferences and conversation history (in-memory, will reset on restart)
user_preferences: Dict[str, UserPreference] = {}
conversation_history: Dict[str, List[Dict[str, str]]] = {}

async def handle_format_choice(
    message: TwilioMessage,
    user_pref: UserPreference,
    background_tasks: BackgroundTasks
) -> str:
    """Handle format preference selection"""
    if message.body in ['1', '2']:
        user_pref.format = 'text' if message.body == '1' else 'voice'
        user_pref.state = 'ready'
        
        if user_pref.pending_query:
            query = user_pref.pending_query
            user_pref.pending_query = None
            return await process_query(query, message.from_number, background_tasks)
        else:
            return twilio_handler.create_response(
                f"Great! I'll send responses in {'text' if message.body == '1' else 'voice'} format. What would you like to know?"
            )
    else:
        user_pref.pending_query = message.body
        return twilio_handler.create_response(
            "How would you like to receive the response?\n\nReply with:\n1️⃣ for Text\n2️⃣ for Voice"
        )

async def generate_voice_response(text: str, sender: str) -> str:
    """Generate and send voice response using Google Cloud TTS"""
    try:
        logger.info("Generating voice response...")
        
        # Set the text input
        synthesis_input = texttospeech.SynthesisInput(
            text=twilio_handler.clean_markdown(text)
        )

        # Build the voice parameters
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-D",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )

        # Select the audio encoding
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0
        )

        logger.info("Calling Google TTS...")
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return await twilio_handler.send_voice_message(
            response.audio_content,
            sender
        )
        
    except Exception as e:
        logger.error(f"Error generating voice response: {str(e)}")
        return twilio_handler.create_response(
            "Sorry, I couldn't generate the voice response. Here's your response in text format:\n\n" + text
        )

async def handle_voice_message(
    message: TwilioMessage,
    background_tasks: BackgroundTasks
) -> str:
    """Handle incoming voice messages"""
    logger.info("Starting voice message processing")
    
    if not message.media_url0:
        return twilio_handler.create_response(
            "I couldn't find a voice message. Please try sending your message again."
        )
    
    try:
        # Download the voice message
        auth = (os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
        voice_content = await twilio_handler.download_media(message.media_url0, auth)
            
        # Save temporarily
        temp_path = "voice_message.ogg"
        with open(temp_path, "wb") as f:
            f.write(voice_content)
            
        try:
            # Transcribe with Deepgram
            deepgram = Deepgram(os.getenv('DEEPGRAM_API_KEY'))
            with open(temp_path, 'rb') as audio:
                source = {'buffer': audio, 'mimetype': 'audio/ogg'}
                transcription = deepgram.transcription.sync_prerecorded(source, {
                    'smart_format': True,
                    'model': 'general',
                    'language': 'en-US'
                })
                
            transcribed_text = transcription['results']['channels'][0]['alternatives'][0]['transcript']
            
            if not transcribed_text:
                raise Exception("Could not transcribe voice message")
                
            # Get or initialize conversation history
            if message.from_number not in conversation_history:
                conversation_history[message.from_number] = []

            # Process with Cerebras
            response, metadata = cerebras_handler.generate_response(
                query=transcribed_text,
                conversation_history=conversation_history[message.from_number],
                user_context={
                    "platform": "whatsapp",
                    "sender": message.from_number,
                    "type": "voice"
                }
            )

            # Update conversation history
            conversation_history[message.from_number].append({
                "user": transcribed_text,
                "assistant": response
            })
            
            # Create response with transcription
            full_response = f"I heard: '{transcribed_text}'\n\nHere's my response:\n\n{response}"
            return await twilio_handler.send_message_parts(
                full_response,
                message.from_number,
                background_tasks
            )
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        logger.error(f"Error processing voice message: {str(e)}")
        return twilio_handler.create_response(
            f"I apologize, but I'm having trouble processing your voice message right now. Error: {str(e)}"
        )

async def process_query(query: str, sender: str, background_tasks: BackgroundTasks) -> str:
    """Process a query and return response in user's preferred format"""
    user_pref = user_preferences.get(sender, UserPreference())
    logger.info(f"Processing query with format preference: {user_pref.format}")
    
    # Get or initialize conversation history
    if sender not in conversation_history:
        conversation_history[sender] = []

    # Generate response using Cerebras with conversation history
    response, metadata = cerebras_handler.generate_response(
        query=query,
        conversation_history=conversation_history[sender],
        user_context={
            "platform": "whatsapp",
            "sender": sender,
            "format": user_pref.format
        }
    )

    # Update conversation history
    conversation_history[sender].append({
        "user": query,
        "assistant": response
    })
    
    # Return response in preferred format
    if user_pref.format == 'voice':
        return await generate_voice_response(response, sender)
    else:
        return await twilio_handler.send_message_parts(
            response,
            sender,
            background_tasks
        )

@app.post("/webhook")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> str:
    logger.info("Starting webhook handler")
    """Handle incoming WhatsApp messages"""
    try:
        form_data = await request.form()
        logger.info(f"Received webhook request: {dict(form_data)}")
        
        # Parse Twilio message
        message = TwilioMessage(**dict(form_data))
        
        if not message.body and not message.media_url0:
            raise HTTPException(status_code=400, detail="No message content")
            
        # Get or create user preferences
        if message.from_number not in user_preferences:
            logger.info(f"Creating new user preferences for {message.from_number}")
            user_preferences[message.from_number] = UserPreference()
        user_pref = user_preferences[message.from_number]
        logger.info(f"Current user state: {user_pref.state}, format: {user_pref.format}")
        
        # Handle format preference
        if user_pref.state == "asking":
            logger.info(f"User {message.from_number} is in asking state, handling format choice")
            response = await handle_format_choice(message, user_pref, background_tasks)
            logger.info(f"Format choice response: {response}")
            return response
        
        # Handle voice message
        if message.is_voice_message:
            return await handle_voice_message(message, background_tasks)
            
        # Handle format change command
        if message.body.lower() in ['change format', 'switch format', 'format']:
            user_pref.state = "asking"
            return twilio_handler.create_response(
                "How would you like to receive the response?\n\n" +
                "Reply with:\n1️⃣ for Text\n2️⃣ for Voice"
            )
            
        # Process text query
        return await process_query(message.body, message.from_number, background_tasks)
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 5001))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )