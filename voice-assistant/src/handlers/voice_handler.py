"""
Voice Handler - Modular STT + TTS Integration
Handles audio transcription (Deepgram) and text-to-speech (Cartesia)
"""
import os
import asyncio
import logging
import httpx
import json
import wave
import io
from typing import Optional

logger = logging.getLogger(__name__)


class VoiceHandler:
    """Handle voice input/output with Deepgram STT and Cartesia TTS"""
    
    def __init__(self, deepgram_key: str, cartesia_key: str):
        self.deepgram_key = deepgram_key
        self.cartesia_key = cartesia_key
        self.deepgram_url = "https://api.deepgram.com/v1/listen"
        self.cartesia_url = "https://api.cartesia.ai/tts/bytes"
        
    def is_speech(self, audio_data: bytes, threshold: float = 0.02) -> bool:
        """
        Detect if audio contains speech using energy-based VAD
        
        Args:
            audio_data: Raw PCM audio bytes
            threshold: Energy threshold (0-1)
            
        Returns:
            True if speech detected, False otherwise
        """
        try:
            import numpy as np
            
            # Convert to samples
            samples = np.frombuffer(audio_data, dtype=np.int16)
            
            # Normalize to -1 to 1
            normalized = samples.astype(np.float32) / 32768.0
            
            # Calculate RMS energy
            rms = np.sqrt(np.mean(normalized ** 2))
            
            has_speech = rms > threshold
            logger.info(f"🔊 Audio energy: {rms:.4f} (threshold: {threshold}) - Speech: {has_speech}")
            
            return has_speech
            
        except Exception as e:
            logger.error(f"❌ VAD error: {e}")
            return False
    
    async def transcribe_audio(self, audio_data: bytes, sample_rate: int = 48000) -> Optional[str]:
        """
        Transcribe audio using Deepgram API
        
        Args:
            audio_data: Raw audio bytes (PCM format)
            sample_rate: Sample rate in Hz
            
        Returns:
            Transcribed text or None if error
        """
        try:
            # Check if audio contains speech first
            if not self.is_speech(audio_data):
                logger.info("🔇 No speech detected, skipping transcription")
                return None
            
            logger.info(f"🎤 Transcribing audio ({len(audio_data)} bytes)...")
            
            # Prepare request
            headers = {
                "Authorization": f"Token {self.deepgram_key}",
                "Content-Type": "audio/wav"
            }
            
            params = {
                "model": "nova-2",
                "smart_format": "true",
                "punctuate": "true",
            }
            
            # Convert PCM to WAV format
            wav_data = self._pcm_to_wav(audio_data, sample_rate)
            
            # Call Deepgram API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.deepgram_url,
                    headers=headers,
                    params=params,
                    content=wav_data
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Extract transcript
                if result.get("results", {}).get("channels", []):
                    alternatives = result["results"]["channels"][0].get("alternatives", [])
                    if alternatives:
                        transcript = alternatives[0].get("transcript", "").strip()
                        if transcript:
                            logger.info(f"✅ Transcript: {transcript}")
                            return transcript
                        else:
                            logger.warning("⚠️ Empty transcript")
                            return None
                
                logger.warning("⚠️ No transcript in response")
                return None
                
        except Exception as e:
            logger.error(f"❌ Transcription error: {e}", exc_info=True)
            return None
    
    async def text_to_speech(self, text: str, voice_id: str = "a0e99841-438c-4a64-b679-ae501e7d6091") -> Optional[bytes]:
        """
        Convert text to speech using Cartesia API
        
        Args:
            text: Text to convert to speech
            voice_id: Cartesia voice ID (default: friendly female voice)
            
        Returns:
            Audio bytes (MP3 format) or None if error
        """
        try:
            logger.info(f"🔊 Generating speech for: {text[:50]}...")
            
            headers = {
                "X-API-Key": self.cartesia_key,
                "Cartesia-Version": "2024-06-10",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model_id": "sonic-english",
                "transcript": text,
                "voice": {
                    "mode": "id",
                    "id": voice_id
                },
                "output_format": {
                    "container": "raw",
                    "encoding": "pcm_s16le",
                    "sample_rate": 48000
                }
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.cartesia_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                audio_bytes = response.content
                logger.info(f"✅ Generated {len(audio_bytes)} bytes of audio")
                return audio_bytes
                
        except Exception as e:
            logger.error(f"❌ TTS error: {e}", exc_info=True)
            return None
    
    def _pcm_to_wav(self, pcm_data: bytes, sample_rate: int, channels: int = 1, sample_width: int = 2) -> bytes:
        """
        Convert raw PCM data to WAV format
        
        Args:
            pcm_data: Raw PCM bytes
            sample_rate: Sample rate in Hz
            channels: Number of audio channels (1=mono, 2=stereo)
            sample_width: Bytes per sample (2 = 16-bit)
            
        Returns:
            WAV formatted bytes
        """
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
        
        return wav_buffer.getvalue() 