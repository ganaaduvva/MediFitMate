"""
Simple Direct Agent - Connects to room as a participant
Handles both text and voice with Cerebras AI
"""
import os
import asyncio
import logging
import numpy as np
from dotenv import load_dotenv
from livekit import rtc, api
from cerebras_handler import CerebrasHandler
from voice_handler import VoiceHandler
from health_assistant import HealthAssistant

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://voice-agent-g5af7mn0.livekit.cloud")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
ROOM_NAME = "cerebras-voice-room"

# Initialize handlers
cerebras = CerebrasHandler(
    api_key=os.getenv("CEREBRAS_API_KEY"),
    model="llama-3.1-8b"
)

voice = VoiceHandler(
    deepgram_key=os.getenv("DEEPGRAM_API_KEY"),
    cartesia_key=os.getenv("CARTESIA_API_KEY")
)

# Initialize health assistant
health = HealthAssistant()


def generate_agent_token():
    """Generate a token for the agent to join the room"""
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity("cerebras-agent")
    token.with_name("Cerebras Assistant")
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=ROOM_NAME,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    ))
    return token.to_jwt()


async def main():
    """Main agent - handles text and voice chat"""
    
    logging.info("🤖 Starting Cerebras AI Agent...")
    room = rtc.Room()
    
    # Voice processing state
    audio_buffers = {}  # participant_id -> audio buffer
    is_processing_voice = {}  # participant_id -> bool
    voice_enabled = {}  # participant_id -> bool (whether voice is enabled for this user)
    
    async def handle_text_message(packet: rtc.DataPacket):
        """Handle text messages and control commands via data channel"""
        try:
            message = packet.data.decode('utf-8')
            
            # Get participant - for control messages, find by audio track
            if packet.participant:
                participant_id = packet.participant.identity
            else:
                # Fallback: use any participant with an audio track
                for pid in audio_buffers.keys():
                    participant_id = pid
                    break
                else:
                    participant_id = "unknown"
            
            # Handle control messages (from Voice button)
            if message == "__VOICE_ENABLE__":
                # Enable for all participants with audio buffers
                for pid in audio_buffers.keys():
                    voice_enabled[pid] = True
                    logging.info(f"🎤 Voice ENABLED for {pid} (via Voice button)")
                return  # Don't send a response for control messages
            
            if message == "__VOICE_DISABLE__":
                # Disable for all participants with audio buffers
                for pid in audio_buffers.keys():
                    voice_enabled[pid] = False
                    logging.info(f"🔇 Voice DISABLED for {pid} (via Voice button)")
                return  # Don't send a response for control messages
            
            logging.info(f"📝 Text message from {participant_id}: {message}")
            
            # Handle text commands
            if message.lower() in ["/clear", "/reset", "/new"]:
                cerebras.clear_history(ROOM_NAME)
                response = "Conversation history cleared! Starting fresh. 🔄"
                logging.info("🔄 History cleared")
            else:
                # Process through health assistant first
                health_response = await health.process_query(message)
                
                if "not directly related to health" in health_response:
                    # Non-health topic detected
                    response = health_response
                    logging.info("🚫 Non-health topic redirected")
                else:
                    # Health topic - get Cerebras response with health context
                    response = cerebras.generate_response(ROOM_NAME, message)
                    
                    # Validate the response
                    valid, feedback = await health.validate_response(
                        response,
                        await health.classify_health_topic(message)
                    )
                    
                    if not valid:
                        logging.warning(f"⚠️ Response validation issues: {feedback}")
                        # Add missing elements (disclaimers, referrals)
                        response = f"{response}\n\nIMPORTANT: {health.disclaimers['general']['educational']}"
                
                logging.info(f"🤖 Response: {response[:100]}...")
            
            # Send response back via data channel
            await room.local_participant.publish_data(
                response.encode('utf-8'),
                reliable=True
            )
            logging.info("✉️ Text response sent!")
            
        except Exception as e:
            logging.error(f"❌ Error handling text message: {e}", exc_info=True)
    
    async def process_voice_buffer(participant_id: str):
        """Process accumulated audio buffer for a participant"""
        if is_processing_voice.get(participant_id, False):
            return  # Already processing
        
        try:
            is_processing_voice[participant_id] = True
            
            if participant_id not in audio_buffers or len(audio_buffers[participant_id]) == 0:
                return
            
            # Get audio buffer
            audio_data = bytes(audio_buffers[participant_id])
            audio_buffers[participant_id] = bytearray()  # Clear buffer
            
            logging.info(f"🎤 Processing voice from {participant_id}")
            
            # Step 1: Transcribe audio with Deepgram
            transcript = await voice.transcribe_audio(audio_data, sample_rate=48000)
            
            if not transcript:
                logging.warning("⚠️ No transcript, skipping")
                return
            
            logging.info(f"📝 Transcript: {transcript}")
            
            # Step 2: Process through health assistant
            health_response = await health.process_query(transcript)
            
            if "not directly related to health" in health_response:
                # Non-health topic detected
                response_text = health_response
                logging.info("🚫 Non-health topic redirected")
            else:
                # Health topic - get Cerebras response with health context
                response_text = cerebras.generate_response(ROOM_NAME, transcript)
                
                # Validate the response
                valid, feedback = await health.validate_response(
                    response_text,
                    await health.classify_health_topic(transcript)
                )
                
                if not valid:
                    logging.warning(f"⚠️ Response validation issues: {feedback}")
                    # Add missing elements (disclaimers, referrals)
                    response_text = f"{response_text}\n\nIMPORTANT: {health.disclaimers['general']['educational']}"
            
            logging.info(f"🤖 Response: {response_text[:100]}...")
            
            # Step 3: Convert to speech with Cartesia
            audio_response = await voice.text_to_speech(response_text)
            
            if not audio_response:
                logging.error("❌ Failed to generate speech")
                return
            
            # Step 4: Publish audio back to room
            audio_source = rtc.AudioSource(48000, 1)  # 48kHz, mono
            audio_track = rtc.LocalAudioTrack.create_audio_track("agent-voice", audio_source)
            
            options = rtc.TrackPublishOptions()
            options.source = rtc.TrackSource.SOURCE_MICROPHONE
            
            await room.local_participant.publish_track(audio_track, options)
            
            # Convert bytes to audio frames and publish
            await play_audio_to_source(audio_source, audio_response)
            
            logging.info("🔊 Voice response played!")
            
            # Unpublish track after playing
            await room.local_participant.unpublish_track(audio_track.sid)
            
        except Exception as e:
            logging.error(f"❌ Voice processing error: {e}", exc_info=True)
        finally:
            is_processing_voice[participant_id] = False
    
    async def play_audio_to_source(audio_source: rtc.AudioSource, audio_data: bytes):
        """Play PCM audio data to an audio source"""
        # Convert bytes to 16-bit PCM samples
        samples = np.frombuffer(audio_data, dtype=np.int16)
        
        # Split into frames (480 samples = 10ms at 48kHz)
        frame_size = 480
        for i in range(0, len(samples), frame_size):
            frame_samples = samples[i:i + frame_size]
            
            # Pad last frame if needed
            if len(frame_samples) < frame_size:
                frame_samples = np.pad(frame_samples, (0, frame_size - len(frame_samples)))
            
            # Create audio frame
            frame = rtc.AudioFrame(
                data=frame_samples.tobytes(),
                sample_rate=48000,
                num_channels=1,
                samples_per_channel=len(frame_samples)
            )
            
            await audio_source.capture_frame(frame)
            await asyncio.sleep(0.01)  # 10ms between frames
    
    # Event handlers
    @room.on("data_received")
    def on_data_received(packet: rtc.DataPacket):
        """Handle incoming text messages"""
        asyncio.create_task(handle_text_message(packet))
    
    @room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        logging.info(f"👤 Participant joined: {participant.identity}")
    
    @room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        logging.info(f"👋 Participant left: {participant.identity}")
    
    @room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        """Handle audio tracks for voice input"""
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logging.info(f"🎤 Audio track detected from {participant.identity}")
            logging.info(f"💡 Voice is disabled by default. User must click Voice button to enable.")
            audio_track = track
            asyncio.create_task(handle_audio_track(audio_track, participant))
    
    async def handle_audio_track(track: rtc.RemoteAudioTrack, participant: rtc.RemoteParticipant):
        """Stream audio frames and buffer them for processing"""
        participant_id = participant.identity
        audio_buffers[participant_id] = bytearray()
        voice_enabled[participant_id] = False  # Voice disabled by default
        
        # Create audio stream
        audio_stream = rtc.AudioStream(track)
        
        buffer_duration = 0  # Track duration in seconds
        BUFFER_LIMIT = 3.0  # Process every 3 seconds of audio
        
        try:
            async for audio_frame_event in audio_stream:
                frame = audio_frame_event.frame
                
                # Only process if voice is enabled for this participant
                if not voice_enabled.get(participant_id, False):
                    # Clear buffer if voice is disabled
                    if len(audio_buffers[participant_id]) > 0:
                        audio_buffers[participant_id] = bytearray()
                        buffer_duration = 0
                    continue
                
                # Append audio data to buffer
                audio_buffers[participant_id].extend(frame.data)
                
                # Calculate duration
                duration = frame.samples_per_channel / frame.sample_rate
                buffer_duration += duration
                
                # Process when we have enough audio
                if buffer_duration >= BUFFER_LIMIT:
                    logging.info(f"🎤 Buffer full ({buffer_duration:.1f}s), processing...")
                    asyncio.create_task(process_voice_buffer(participant_id))
                    buffer_duration = 0
                    
        except Exception as e:
            logging.error(f"❌ Audio streaming error: {e}", exc_info=True)
    
    # Generate token and connect
    token = generate_agent_token()
    logging.info(f"🔗 Connecting to room: {ROOM_NAME}")
    
    try:
        await room.connect(LIVEKIT_URL, token)
        logging.info(f"✅ Connected! Agent is ready.")
        logging.info(f"📊 Room: {ROOM_NAME}")
        logging.info(f"📝 Text chat: Always enabled")
        logging.info(f"🎤 Voice chat: Click the Voice button in the UI to activate")
        logging.info(f"💡 Command: /clear (clear conversation history)")
        logging.info(f"🚀 Both text and voice use the same conversation history!")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logging.error(f"❌ Connection failed: {e}", exc_info=True)
    finally:
        await room.disconnect()
        logging.info("👋 Agent disconnected")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\n👋 Agent stopped by user") 