import os
import re
import httpx
import asyncio
import logging
from typing import Optional, List, Tuple
from fastapi import FastAPI, HTTPException, BackgroundTasks
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from src.models.twilio_models import TwilioMessage

logger = logging.getLogger(__name__)

class TwilioHandler:
    def __init__(self, app: FastAPI):
        self.app = app
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        logger.info(f"Initializing Twilio client with account_sid: {account_sid[:6]}... and phone_number: {self.phone_number}")
        if not all([account_sid, auth_token, self.phone_number]):
            raise ValueError("Missing required Twilio credentials")
            
        self.client = Client(account_sid, auth_token)

    def create_response(self, message: str) -> str:
        """Create a TwiML response"""
        logger.info(f"Creating TwiML response with message: {message}")
        try:
            # First try to send via REST API
            result = self.client.messages.create(
                body=message,
                from_=f"whatsapp:{self.phone_number}",
                to="whatsapp:+918885229659"  # Your number
            )
            logger.info(f"Message sent via REST API. SID: {result.sid}")
            
            # Return empty TwiML response since we already sent the message
            response = MessagingResponse()
            return str(response)
            
        except Exception as e:
            logger.error(f"Failed to send via REST API: {str(e)}")
            # Fallback to TwiML response
            response = MessagingResponse()
            response.message(message)
            return str(response)

    async def send_message(self, message: str, to: str) -> str:
        """Send a single message"""
        try:
            result = self.client.messages.create(
                body=message,
                from_=f"whatsapp:{self.phone_number}",
                to=to
            )
            logger.info(f"Message sent successfully. SID: {result.sid}")
            return result.sid
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

    async def send_voice_message(
        self, 
        audio_content: bytes, 
        to: str,
        text_description: Optional[str] = "Here's your voice response:"
    ) -> str:
        """Send a voice message"""
        try:
            from io import BytesIO
            audio_buffer = BytesIO(audio_content)
            audio_buffer.name = 'response.mp3'

            result = self.client.messages.create(
                body=text_description,
                from_=f"whatsapp:{self.phone_number}",
                to=to,
                media_streams=[audio_buffer]
            )
            logger.info(f"Voice message sent successfully. SID: {result.sid}")
            return self.create_response("")
        except Exception as e:
            logger.error(f"Error sending voice message: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to send voice message: {str(e)}")

    def clean_markdown(self, text: str) -> str:
        """Remove markdown formatting"""
        text = re.sub(r'#+\s*', '', text)  # Remove headers
        text = re.sub(r'\*+', '', text)    # Remove bold/italic
        text = re.sub(r'\n{3,}', '\n\n', text)  # Normalize newlines
        return text.strip()

    async def send_message_parts(
        self,
        text: str,
        to: str,
        background_tasks: BackgroundTasks
    ) -> str:
        """Split and send long messages"""
        text = self.clean_markdown(text)
        
        if len(text) <= 1500:
            return self.create_response(text)

        chunks = [text[i:i+1500] for i in range(0, len(text), 1500)]
        
        # Send first part via REST API
        try:
            result = self.client.messages.create(
                body=chunks[0] + f"\n(Part 1/{len(chunks)})",
                from_=f"whatsapp:{self.phone_number}",
                to=to
            )
            logger.info(f"Part 1/{len(chunks)} sent successfully. Message SID: {result.sid}")
        except Exception as e:
            logger.error(f"Failed to send part 1: {str(e)}")
            # If REST API fails, try TwiML
            response = MessagingResponse()
            response.message(chunks[0] + f"\n(Part 1/{len(chunks)})")
            return str(response)

        # Send remaining parts in background
        background_tasks.add_task(
            self._send_remaining_parts,
            chunks=chunks,
            to=to
        )

        # Return empty response since we sent via REST API
        response = MessagingResponse()
        return str(response)

    async def _send_remaining_parts(self, chunks: List[str], to: str):
        """Background task to send remaining message parts"""
        try:
            logger.info(f"Starting to send remaining {len(chunks)-1} parts...")
            await asyncio.sleep(3)  # Wait for first part to be delivered
            logger.info("Finished initial delay, sending parts...")

            for i, chunk in enumerate(chunks[1:], 2):
                try:
                    logger.info(f"Sending part {i}/{len(chunks)}...")
                    message = await self.send_message(
                        chunk + f"\n(Part {i}/{len(chunks)})",
                        to
                    )
                    logger.info(f"Part {i}/{len(chunks)} sent successfully. Message SID: {message}")
                    await asyncio.sleep(1)
                except Exception as e:
                    if "63038" in str(e):  # Message limit error
                        logger.error("Message limit reached for trial account")
                        try:
                            await self.send_message(
                                "I apologize, but I've reached the message limit for today. Please try again tomorrow.",
                                to
                            )
                        except Exception as limit_e:
                            logger.error(f"Failed to send limit message: {str(limit_e)}")
                        break
                    else:
                        logger.error(f"Error sending part {i}/{len(chunks)}: {str(e)}")
                        raise
        except Exception as e:
            logger.error(f"Error sending remaining parts: {str(e)}")

    async def download_media(self, media_url: str, auth: Tuple[str, str]) -> bytes:
        """Download media from Twilio"""
        logger.info("Attempting to download media...")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(media_url, auth=auth)
            logger.info(f"Download response status: {response.status_code}")
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to download media: {response.status_code}"
                )
                
            return response.content