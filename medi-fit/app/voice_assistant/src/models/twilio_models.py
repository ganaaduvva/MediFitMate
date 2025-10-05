from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import json

class TwilioMessage(BaseModel):
    message_sid: str = Field(..., alias='MessageSid')
    message_type: str = Field(..., alias='MessageType')
    body: Optional[str] = Field(None, alias='Body')
    from_number: str = Field(..., alias='From')
    to_number: str = Field(..., alias='To')
    num_media: int = Field(0, alias='NumMedia')
    media_url0: Optional[str] = Field(None, alias='MediaUrl0')
    media_content_type0: Optional[str] = Field(None, alias='MediaContentType0')
    profile_name: Optional[str] = Field(None, alias='ProfileName')
    wa_id: Optional[str] = Field(None, alias='WaId')
    channel_metadata: Optional[Dict[str, Any]] = Field(None, alias='ChannelMetadata')

    @property
    def is_voice_message(self) -> bool:
        return self.message_type == 'audio' and bool(self.media_url0)

    def __init__(self, **data):
        # Parse ChannelMetadata from string to dict if it's a string
        if isinstance(data.get('ChannelMetadata'), str):
            try:
                data['ChannelMetadata'] = json.loads(data['ChannelMetadata'])
            except json.JSONDecodeError:
                data['ChannelMetadata'] = None
        super().__init__(**data)

class UserPreference(BaseModel):
    state: str = "asking"
    format: Optional[str] = None
    pending_query: Optional[str] = None