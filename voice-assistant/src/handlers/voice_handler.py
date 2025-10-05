import os
import httpx
import logging
import tempfile
from typing import Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

class VoiceHandler:
    def __init__(self):
        self.deepgram_api_key = os.getenv('DEEPGRAM_API_KEY')
        self.cartesia_api_key = os.getenv('CARTESIA_API_KEY')
        
    async def download_voice_message(self, media_url: str) -> Optional[bytes]:
        """Download voice message from Twilio's media URL"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(media_url)
                if response.status_code == 200:
                    return response.content
                logger.error(f"Failed to download voice message: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error downloading voice message: {e}")
            return None
    
    async def upload_to_twilio(self, audio_data: bytes, twilio_client) -> Optional[str]:
        """Upload audio response to Twilio for media message"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Upload to Twilio
            try:
                media = twilio_client.media.v1.media_list.create(
                    content=open(temp_file_path, 'rb'),
                    content_type='audio/mp3'
                )
                return media.uri
            finally:
                # Clean up temp file
                os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"Error uploading audio to Twilio: {e}")
            return None
    
    async def transcribe_audio(self, audio_data: bytes, sample_rate: int = 48000) -> Optional[str]:
        """Transcribe audio using Deepgram"""
        try:
            if not self.is_speech(audio_data):
                logger.info("No speech detected in audio")
                return None
                
            # Convert audio to WAV format
            wav_data = self._pcm_to_wav(audio_data, sample_rate)
            
            # Call Deepgram API
            url = "https://api.deepgram.com/v1/listen"
            headers = {
                "Authorization": f"Token {self.deepgram_api_key}",
                "Content-Type": "audio/wav"
            }
            params = {
                "punctuate": True,
                "model": "general",
                "language": "en-US"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, params=params, content=wav_data)
                if response.status_code == 200:
                    result = response.json()
                    return result['results']['channels'][0]['alternatives'][0]['transcript']
                    
                logger.error(f"Deepgram API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
    
    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech using Cartesia"""
        try:
            url = "https://api.cartesia.ai/v1/tts"
            headers = {
                "Authorization": f"Bearer {self.cartesia_api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "text": text,
                "voice": "en-US-Neural2-F",
                "format": "mp3"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
                if response.status_code == 200:
                    return response.content
                    
                logger.error(f"Cartesia API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            return None
    
    def is_speech(self, audio_data: bytes, threshold: float = 0.02) -> bool:
        """Detect if audio contains speech using energy-based VAD"""
        try:
            samples = np.frombuffer(audio_data, dtype=np.int16)
            normalized = samples.astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean(normalized ** 2))
            has_speech = rms > threshold
            logger.info(f"Audio energy: {rms:.4f} (threshold: {threshold}) - Speech: {has_speech}")
            return has_speech
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return False
    
    def _pcm_to_wav(self, pcm_data: bytes, sample_rate: int) -> bytes:
        """Convert PCM audio data to WAV format"""
        import wave
        import io
        
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
            
        return wav_buffer.getvalue()