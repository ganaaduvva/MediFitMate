#!/usr/bin/env python3
"""
Generate fresh LiveKit token and update index.html
Run this before testing to get a valid token
"""
import os
import re
from dotenv import load_dotenv
from livekit import api

load_dotenv()

# Generate token
api_key = os.getenv("LIVEKIT_API_KEY")
api_secret = os.getenv("LIVEKIT_API_SECRET")
livekit_url = os.getenv("LIVEKIT_URL", "wss://voice-agent-g5af7mn0.livekit.cloud")

token = api.AccessToken(api_key, api_secret)
token.with_identity("user-" + os.urandom(4).hex())
token.with_name("User")
token.with_grants(api.VideoGrants(
    room_join=True,
    room="cerebras-voice-room",
    can_publish=True,
    can_subscribe=True,
    can_publish_data=True,
))

jwt_token = token.to_jwt()

# Read index.html
with open('index.html', 'r') as f:
    html_content = f.read()

# Replace the getDevToken function with actual token
token_replacement = f'''        async function getDevToken() {{
            return '{jwt_token}';
        }}'''

# Find and replace
pattern = r'async function getDevToken\(\) \{[^}]+\}'
html_content = re.sub(pattern, token_replacement.replace('\\', '\\\\'), html_content, flags=re.DOTALL)

# Also update the WebSocket URL
html_content = html_content.replace(
    "const wsUrl = 'wss://voice-agent-g5af7mn0.livekit.cloud';",
    f"const wsUrl = '{livekit_url}';"
)

# Write back
with open('index.html', 'w') as f:
    f.write(html_content)

print("\n" + "="*60)
print("✅ Token updated successfully!")
print("="*60)
print(f"🔗 LiveKit URL: {livekit_url}")
print(f"🔑 Token generated (valid for 6 hours)")
print("\n📝 TO USE:")
print("1. Make sure agent is running: python main.py dev")
print("2. Open index.html in your browser")
print("3. Chat with text or voice!")
print("="*60 + "\n") 