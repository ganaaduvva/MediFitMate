import os
import time
import requests
import re
import base64
from threading import Thread
from collections import defaultdict
from google.cloud import texttospeech
from dotenv import load_dotenv
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from deepgram import Deepgram
from src.handlers.cerebras_handler import CerebrasHandler

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Initialize Twilio client
twilio_client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)

# Initialize Cerebras handler
cerebras_handler = CerebrasHandler()

# Initialize Google Cloud TTS client
tts_client = texttospeech.TextToSpeechClient()

# Store user preferences (in-memory, will reset on server restart)
user_preferences = defaultdict(lambda: {'state': 'asking', 'format': None, 'pending_query': None})

def ask_format_preference():
    """Create response asking for format preference"""
    twilio_response = MessagingResponse()
    twilio_response.message("How would you like to receive the response?\n\nReply with:\n1️⃣ for Text\n2️⃣ for Voice")
    return str(twilio_response)

def generate_voice_response(text, sender):
    """Generate and send voice response using Google Cloud TTS"""
    try:
        app.logger.info("Generating voice response...")
        # Clean the text
        clean_text = clean_markdown(text)
        
        # Set the text input
        synthesis_input = texttospeech.SynthesisInput(text=clean_text)

        # Build the voice parameters
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-D",  # A natural-sounding female voice
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )

        # Select the audio encoding
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0
        )

        app.logger.info("Calling Google TTS...")
        # Perform the text-to-speech request
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        app.logger.info("Got TTS response")

        # Create a temporary file in memory
        from io import BytesIO
        audio_buffer = BytesIO(response.audio_content)
        audio_buffer.name = 'response.mp3'  # Required for Twilio to detect MIME type

        # Send message with audio using Twilio's client
        twilio_response = twilio_client.messages.create(
            body="Here's your voice response:",
            from_=f"whatsapp:{os.getenv('TWILIO_PHONE_NUMBER')}",
            to=sender,
            media_streams=[audio_buffer]
        )
        
        app.logger.info(f"Twilio API response: {twilio_response.status_code}")
        
        app.logger.info("Sending voice response...")
        # Return empty TwiML response since we sent via API
        return str(MessagingResponse())
        
    except Exception as e:
        app.logger.error(f"Error generating voice response: {str(e)}")
        # Fall back to text response
        twilio_response = MessagingResponse()
        twilio_response.message("Sorry, I couldn't generate the voice response. Here's your response in text format:\n\n" + clean_text)
        return str(twilio_response)

def clean_markdown(text):
    """Remove markdown formatting"""
    # Replace markdown headers with plain text
    text = re.sub(r'#+\s*', '', text)
    # Replace markdown bold/italic with plain text
    text = re.sub(r'\*+', '', text)
    # Replace multiple newlines with just two
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def send_remaining_parts(chunks, sender):
    """Send remaining parts in background after delay"""
    try:
        # Wait for webhook response to be sent
        time.sleep(3)
        
        # Send remaining chunks
        for i, chunk in enumerate(chunks[1:], 2):
            try:
                twilio_client.messages.create(
                    body=chunk + f"\n(Part {i}/{len(chunks)})",
                    from_=f"whatsapp:{os.getenv('TWILIO_PHONE_NUMBER')}",
                    to=sender
                )
                time.sleep(1)
            except Exception as e:
                if "63038" in str(e):
                    app.logger.error("Message limit reached for trial account")
                    # Send a final message about the limit
                    twilio_client.messages.create(
                        body="I apologize, but I've reached the message limit for today. Please try again tomorrow.",
                        from_=f"whatsapp:{os.getenv('TWILIO_PHONE_NUMBER')}",
                        to=sender
                    )
                    break
                else:
                    raise e
    except Exception as e:
        app.logger.error(f"Error sending remaining parts: {str(e)}")

def send_message_parts(response, sender):
    """Send message in parts if needed"""
    try:
        # Clean markdown from response
        response = clean_markdown(response)
        
        # Create TwiML response for first message
        twilio_response = MessagingResponse()
        
        # If response is too long, split it
        if len(response) > 1500:
            chunks = [response[i:i+1500] for i in range(0, len(response), 1500)]
            try:
                # Send first chunk via TwiML
                twilio_response.message(chunks[0] + "\n(Part 1/" + str(len(chunks)) + ")")
                
                # Start background thread for remaining parts
                from threading import Thread
                thread = Thread(target=send_remaining_parts, args=(chunks, sender))
                thread.daemon = True
                thread.start()
            except Exception as e:
                if "63038" in str(e):
                    app.logger.error("Message limit reached for trial account")
                    error_response = MessagingResponse()
                    error_response.message("I apologize, but I've reached the message limit for today. Please try again tomorrow.")
                    return str(error_response)
                else:
                    raise e
        else:
            # Response is within limit
            try:
                twilio_response.message(response)
            except Exception as e:
                if "63038" in str(e):
                    app.logger.error("Message limit reached for trial account")
                    error_response = MessagingResponse()
                    error_response.message("I apologize, but I've reached the message limit for today. Please try again tomorrow.")
                    return str(error_response)
                else:
                    raise e
        
        return str(twilio_response)
    except Exception as e:
        app.logger.error(f"Error in send_message_parts: {str(e)}")
        error_response = MessagingResponse()
        error_response.message("An error occurred while sending the message. Please try again.")
        return str(error_response)

def process_query(query, sender):
    """Process a query and return response in user's preferred format"""
    user_pref = user_preferences[sender]
    app.logger.info(f"Processing query with format preference: {user_pref['format']}")
    
    # Generate response using Cerebras
    response, metadata = cerebras_handler.generate_response(
        query=query,
        user_context={
            "platform": "whatsapp",
            "sender": sender,
            "format": user_pref['format']
        }
    )
    
    # Return response in preferred format
    if user_pref['format'] == 'voice':
        return generate_voice_response(response, sender)
    else:
        return send_message_parts(response, sender)

@app.route("/webhook", methods=['POST'])
def handle_message():
    """Handle incoming WhatsApp messages"""
    app.logger.info("Received webhook request")
    app.logger.info(f"Request values: {request.values}")
    app.logger.info(f"Request headers: {request.headers}")
    # Validate the request
    if not request.values.get('Body') and not request.values.get('MediaUrl0'):
        return 'No message content (text or voice)', 400
        
    # Get sender info
    sender = request.values.get('From', '')
    user_pref = user_preferences[sender]
    
    # If we're waiting for format preference
    if user_pref['state'] == 'asking':
        incoming_msg = request.values.get('Body', '').strip()
        
        # Check if this is a format choice
        if incoming_msg in ['1', '2']:
            user_pref['format'] = 'text' if incoming_msg == '1' else 'voice'
            user_pref['state'] = 'ready'
            
            # If we have a pending query, process it now
            if user_pref['pending_query']:
                query = user_pref['pending_query']
                user_pref['pending_query'] = None
                return process_query(query, sender)
            else:
                twilio_response = MessagingResponse()
                twilio_response.message(f"Great! I'll send responses in {'text' if incoming_msg == '1' else 'voice'} format. What would you like to know?")
                return str(twilio_response)
        else:
            # Store this as the pending query and ask for format preference
            user_pref['pending_query'] = incoming_msg
            return ask_format_preference()
    
    # Handle incoming message
    if request.values.get('MediaUrl0'):
        return handle_voice()  # Voice message always returns text response for now
        
    # Process text query
    incoming_msg = request.values.get('Body', '').strip()
    
    # Check for format change command
    if incoming_msg.lower() in ['change format', 'switch format', 'format']:
        user_pref['state'] = 'asking'
        return ask_format_preference()
        
    return process_query(incoming_msg, sender)

def handle_voice():
    """Handle incoming voice messages"""
    app.logger.info("Starting voice message processing")
    sender = request.values.get('From', '')
    app.logger.info(f"Current user preferences: {user_preferences[sender]}")
    
    # Get the message details
    media_url = request.values.get('MediaUrl0', '')
    sender = request.values.get('From', '')
    
    # Log incoming request details
    app.logger.info(f"Voice message from {sender}")
    app.logger.info(f"Media URL: {media_url}")
    app.logger.info(f"All request values: {request.values}")
    
    # Validate media URL
    if not media_url:
        twilio_response = MessagingResponse()
        twilio_response.message("I couldn't find a voice message. Please try sending your message again.")
        return str(twilio_response)
        
    # Send immediate acknowledgment
    twilio_response = MessagingResponse()
    twilio_response.message("I received your voice message. Processing it now...")
    
    try:
        # Download the voice message
        auth = (os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
        app.logger.info("Attempting to download voice message...")
        
        response = requests.get(media_url, auth=auth)
        app.logger.info(f"Download response status: {response.status_code}")
        
        if response.status_code != 200:
            raise Exception(f"Failed to download voice message: {response.status_code}")
            
        # Save temporarily
        temp_path = "voice_message.ogg"  # Save in current directory instead of /tmp
        with open(temp_path, "wb") as f:
            f.write(response.content)
        app.logger.info(f"Saved voice message to {temp_path}")
            
        # Convert OGG to WAV (if needed)
        # For now, we'll assume the file is in a compatible format
        
        try:
            # Initialize DeepgramClient
            deepgram = Deepgram(os.getenv('DEEPGRAM_API_KEY'))
            
            # Transcribe the audio file
            with open(temp_path, 'rb') as audio:
                source = {'buffer': audio, 'mimetype': 'audio/ogg'}
                transcription = deepgram.transcription.sync_prerecorded(source, {
                    'smart_format': True,
                    'model': 'general',
                    'language': 'en-US'
                })
                
            # Extract transcribed text
            transcribed_text = transcription['results']['channels'][0]['alternatives'][0]['transcript']
            
            if not transcribed_text:
                raise Exception("Could not transcribe voice message")
                
            # Process with Cerebras
            response, metadata = cerebras_handler.generate_response(
                query=transcribed_text,
                user_context={
                    "platform": "whatsapp",
                    "sender": sender,
                    "type": "voice"
                }
            )
            
            # Create response with transcription and response
            full_response = f"I heard: '{transcribed_text}'\n\nHere's my response:\n\n{response}"
            return send_message_parts(full_response, sender)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        app.logger.error(f"Error processing voice message: {str(e)}")
        app.logger.error(f"Full request data: {request.values}")
        error_msg = f"I apologize, but I'm having trouble processing your voice message right now. Error: {str(e)}"
        twilio_response = MessagingResponse()
        twilio_response.message(error_msg)
        return str(twilio_response)

if __name__ == "__main__":
    # Get port from environment variable or default to 5000
    port = int(os.getenv('PORT', 5000))
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=port, debug=True)