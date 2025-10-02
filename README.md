# Cerebras Multimodal AI Assistant with LiveKit

A production-ready AI assistant powered by Cerebras AI that handles **both voice and text** conversations in real-time using LiveKit infrastructure.

## 🎯 Features

- ✅ **Text Chat** → Type messages and get instant AI responses
- ✅ **Voice Chat** → Speak naturally and hear AI responses back
- ✅ **Unified Conversation** → Text and voice share the same conversation history
- ✅ **Beautiful Web UI** → Modern, responsive chat interface
- ✅ **Modular Architecture** → Clean separation of concerns (LLM, STT, TTS, Agent)
- ✅ **Voice Activity Detection** → Only processes audio when you're speaking
- ✅ **Smart Formatting** → Clean, readable responses with proper spacing

## 🏗️ Architecture

```
┌──────────────────────┐
│    Web Browser       │
│   (index.html)       │
│                      │
│  📝 Text Input       │
│  🎤 Voice Button     │
└──────────┬───────────┘
           │
    Data Channel (Text)
    Audio Track (Voice)
           │
┌──────────┴───────────┐
│    LiveKit Room      │
│  "cerebras-voice-    │
│       room"          │
└──────────┬───────────┘
           │
┌──────────┴───────────┐
│   Python Agent       │
│    (agent.py)        │
└──────────┬───────────┘
           │
    ┌──────┴──────────────────┐
    │                         │
┌───┴───────────┐  ┌──────────┴─────────┐
│  Text Path    │  │   Voice Path       │
│               │  │                    │
│  Cerebras     │  │  Audio Buffer (3s) │
│  Handler      │  │        ↓           │
│  (.py)        │  │  Voice Handler     │
│               │  │  - Deepgram STT    │
│               │  │  - Cerebras LLM    │
│               │  │  - Cartesia TTS    │
│               │  │  (.py)             │
└───────────────┘  └────────────────────┘
```

## 📁 Project Structure

```
voice-agent/
├── agent.py              # Main agent (handles LiveKit connection & routing)
├── cerebras_handler.py   # Cerebras LLM integration
├── voice_handler.py      # Voice processing (STT + TTS)
├── index.html            # Modern web UI
├── update_token.py       # JWT token generator
├── .env                  # API keys (not in git)
├── requirements.txt      # Python dependencies
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd voice-agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file with your API keys:

```env
# LiveKit (https://cloud.livekit.io)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# Cerebras (https://cerebras.ai)
CEREBRAS_API_KEY=your_cerebras_key

# Deepgram (https://deepgram.com)
DEEPGRAM_API_KEY=your_deepgram_key

# Cartesia (https://cartesia.ai)
CARTESIA_API_KEY=your_cartesia_key
```

### 3. Generate Token

```bash
python update_token.py
```

This generates a fresh JWT token and injects it into `index.html`.

### 4. Start the Agent

```bash
python agent.py
```

You should see:
```
✅ Connected! Agent is ready.
📊 Room: cerebras-voice-room
📝 Text chat: Always enabled
🎤 Voice chat: Click the Voice button in the UI to activate
💡 Command: /clear (clear conversation history)
🚀 Both text and voice use the same conversation history!
```

### 5. Open Web UI

Open `index.html` in your browser and start chatting!

## 💬 How to Use

### Text Chat

1. Open `index.html` in your browser
2. Wait for green "Connected" status
3. Type your message in the input box
4. Press **Enter** or click **Send**
5. Get instant AI response!

**Commands:**
- `/clear` - Clear conversation history

### Voice Chat

1. Open `index.html` in your browser
2. Wait for green "Connected" status
3. Click the **🎤 Voice** button (turns red: "⏹️ Stop")
4. **Speak clearly for 3+ seconds**
5. The agent will:
   - 🎤 Transcribe your speech (Deepgram)
   - 🤖 Generate response (Cerebras)
   - 🔊 Speak back (Cartesia)
6. Click **⏹️ Stop** to disable voice

**How Voice Works:**
- **3-Second Buffer**: Collects 3 seconds of audio before processing
- **Voice Activity Detection**: Only processes when you're actually speaking (skips silence)
- **Shared History**: Voice and text conversations are connected

## 🧩 Code Overview

### `agent.py` - Main Agent
- Connects to LiveKit room as a participant
- Routes incoming messages (text or voice control)
- Buffers audio for 3 seconds, then processes
- Publishes audio responses back to room
- **150 lines** of clean, readable code

**Key Features:**
- Audio buffering with configurable duration
- Voice enable/disable via UI button
- Handles both text and voice in unified system

### `cerebras_handler.py` - LLM Integration
- Manages conversation history per room
- Uses Cerebras Chat API for responses
- Fallback to Completions API if needed
- Cleans markdown for readable display
- Automatic history trimming (last 20 messages)

**Key Methods:**
- `generate_response()` - Get AI response for a message
- `clear_history()` - Reset conversation
- `clean_markdown_for_display()` - Format responses

### `voice_handler.py` - Voice Processing
- **Deepgram STT**: Transcribe audio to text
- **Cartesia TTS**: Convert text to speech
- **Voice Activity Detection**: Energy-based VAD
- **Audio format conversion**: PCM ↔ WAV

**Key Methods:**
- `transcribe_audio()` - Audio bytes → Text
- `text_to_speech()` - Text → Audio bytes
- `is_speech()` - Detect if audio contains speech

### `index.html` - Web UI
- Modern, responsive chat interface
- Text input with send button
- Voice button with visual feedback
- Real-time message display
- System notifications
- Preserves line breaks and formatting

## 🔧 Technical Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM** | Cerebras (llama-3.1-8b) | Text generation |
| **STT** | Deepgram (nova-2) | Speech-to-text |
| **TTS** | Cartesia (sonic-english) | Text-to-speech |
| **Real-time** | LiveKit Cloud | WebRTC infrastructure |
| **Backend** | Python 3.12+ | Agent logic |
| **Frontend** | HTML/CSS/JS | Browser UI |
| **HTTP Client** | httpx | Async API calls |
| **Audio Processing** | numpy | PCM manipulation |

## 📚 API Keys Required

1. **LiveKit** - https://cloud.livekit.io
   - Free tier available
   - WebRTC infrastructure

2. **Cerebras** - https://cerebras.ai
   - Fast inference (llama-3.1-8b)
   - Generous free tier

3. **Deepgram** - https://deepgram.com
   - Speech-to-text (nova-2 model)
   - $200 free credits

4. **Cartesia** - https://cartesia.ai
   - Text-to-speech (sonic-english)
   - Free tier available

## ⚙️ Configuration

### Adjust Voice Buffer Duration

In `agent.py`, line ~205:

```python
BUFFER_LIMIT = 3.0  # Seconds of audio to collect before processing
```

**Recommendations:**
- **1.5-2s** - Faster, but may cut off sentences
- **3-5s** - Balanced (default)
- **5+s** - For long explanations

### Adjust VAD Sensitivity

In `voice_handler.py`, `is_speech()` method:

```python
def is_speech(self, audio_data: bytes, threshold: float = 0.02):
```

- **Lower threshold** (0.01) - More sensitive, catches whispers
- **Higher threshold** (0.05) - Less sensitive, ignores background noise

## 🐛 Troubleshooting

### Token Expired
```bash
python update_token.py
```
Then refresh your browser.

### Agent Not Responding to Text
1. Check agent is running (look for "✅ Connected!")
2. Check agent logs in terminal
3. Restart agent: `Ctrl+C`, then `python agent.py`

### Voice Not Working
1. Click the **🎤 Voice** button to enable
2. Check browser console (F12) for errors
3. Verify microphone permissions in browser
4. Speak for at least 3 seconds
5. Check agent logs for transcription errors

### Empty Transcripts
- You might not be speaking loud enough
- Try adjusting VAD threshold (see Configuration)
- Check microphone is working in other apps

### Browser Not Connecting
- Make sure green "Connected" shows
- Check console for errors (F12)
- Refresh page
- Make sure agent is running
- Run `python update_token.py` for fresh token

### Audio Not Playing Back
- Check browser audio is not muted
- Check agent logs for TTS errors
- Verify Cartesia API key is correct

## 🎓 How It Works

### Text Flow
```
User types → LiveKit data channel → Agent receives
           → Cerebras generates response → Send back via data channel
           → Browser displays
```

### Voice Flow
```
User clicks Voice → Enable microphone → Publish audio track
                  → Agent buffers 3 seconds
                  → VAD checks: Is speech?
                     ↓ Yes
                  → Deepgram transcribes
                  → Cerebras generates (same as text!)
                  → Cartesia converts to speech
                  → Publish audio track
                  → Browser plays audio
```

## 🚀 Production Considerations

### Current Approach (MVP)
- ✅ Simple and reliable
- ✅ Easy to debug
- ✅ Good for testing
- ⚠️ 3-second latency

### For Production (Future)
- Switch to **WebSocket streaming** for lower latency
- Add **interruption handling** (stop mid-sentence)
- Implement **silence detection** for natural pauses
- Add **error recovery** and reconnection logic
- Add **rate limiting** and usage tracking
- Deploy agent to **cloud server** (not local)

## 🙏 Built With

- [LiveKit Python SDK](https://github.com/livekit/python-sdks)
- [Cerebras Cloud SDK](https://inference-docs.cerebras.ai/)
- [Deepgram API](https://developers.deepgram.com/)
- [Cartesia API](https://docs.cartesia.ai/)
- Modern async/await Python patterns

---

## 📝 License

This is a demo project. Use at your own risk.

## 🎯 Philosophy

**Keep it simple, modular, and scalable!**

This project demonstrates how to build a multimodal AI assistant with:
- Clean architecture (each component is independent)
- Direct API integration (no complex frameworks)
- Easy debugging (clear logs at each step)
- Production patterns (proper error handling, async operations)

Perfect for learning, prototyping, or building your own AI assistant! 🚀
