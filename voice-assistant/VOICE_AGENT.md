# Health & Wellness WhatsApp AI Assistant

A specialized health and wellness assistant powered by Cerebras AI that provides **evidence-based health information** through both voice and text conversations via WhatsApp.

## 🎯 Features

### Health & Wellness
- 🏥 **Evidence-Based Information** → Accurate health and wellness guidance
- 🧘 **Holistic Approach** → Physical health, mental wellbeing, nutrition, fitness
- ⚕️ **Safe Practices** → Clear medical disclaimers and professional referrals
- 🛡️ **Topic Validation** → Ensures discussions stay focused on health

### Communication
- 💬 **Text Chat** → Send text messages via WhatsApp
- 🎤 **Voice Messages** → Send voice notes for natural conversations
- 🤝 **Format Choice** → Choose between text or voice responses
- 🎯 **Topic Focus** → Politely redirects non-health questions
- 📝 **Clear Format** → Well-organized health information with proper spacing

### Technical
- 🏗️ **Modular Design** → Clean separation of health processing components
- 🎯 **Keyword Detection** → Smart health topic validation
- 🔍 **Voice Processing** → Accurate speech-to-text and text-to-speech
- 🔄 **Format Switching** → Easily switch between text and voice responses

## 🏗️ Architecture

```
┌──────────────────────┐
│    WhatsApp         │
│                     │
│  📝 Text Messages   │
│  🎤 Voice Messages  │
└──────────┬──────────┘
           │
    Twilio WhatsApp API
           │
┌──────────┴──────────┐
│   Flask Webhook     │
│    (app.py)        │
└──────────┬──────────┘
           │
    ┌──────┴──────────────────┐
    │                         │
┌───┴───────────┐  ┌──────────┴─────────┐
│  Text Path    │  │   Voice Path       │
│               │  │                    │
│  Cerebras     │  │  Deepgram STT     │
│  Handler      │  │  Cerebras LLM     │
│  (.py)        │  │  Google Cloud TTS  │
└───────────────┘  └────────────────────┘
```

## 📁 Project Structure

```
voice-assistant/
├── src/
│   ├── app.py              # Main Flask application (webhook handler)
│   └── handlers/
│       ├── __init__.py
│       └── cerebras_handler.py  # Cerebras LLM integration
├── config/                 # Configuration files
│   ├── health_categories.json
│   ├── medical_terms.json
│   └── prompt_templates.json
├── tests/                 # Test files
├── requirements.txt       # Python dependencies
└── VOICE_AGENT.md        # Documentation
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd voice-assistant
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file with your API keys:

```env
# Twilio (https://twilio.com)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_whatsapp_number

# Cerebras (https://cerebras.ai)
CEREBRAS_API_KEY=your_cerebras_key

# Deepgram (https://deepgram.com)
DEEPGRAM_API_KEY=your_deepgram_key

# Google Cloud (https://cloud.google.com)
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json
```

### 3. Start the Server

```bash
cd voice-assistant
export PYTHONPATH=.
export FLASK_APP=src/app.py
flask run --port 5001
```

### 4. Expose Webhook (Development)

Use ngrok to expose your local server:

```bash
ngrok http 5001
```

Configure the ngrok URL + `/webhook` in your Twilio WhatsApp Sandbox settings.

## 💬 How to Use

### Initial Setup
1. Join your Twilio WhatsApp Sandbox
2. Send any message to start
3. Choose your preferred response format:
   - Reply "1" for text responses
   - Reply "2" for voice responses

### Available Commands
- Send "format" to change your response format preference
- Send voice messages to get transcribed responses
- Send text messages for regular chat

### Response Formats
- **Text**: Clean, formatted responses with proper spacing
- **Voice**: Natural speech responses using Google Cloud TTS
- **Mixed**: Voice messages always return text transcription first

## 🔧 Technical Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Platform** | Twilio | WhatsApp integration |
| **LLM** | Cerebras | Text generation |
| **STT** | Deepgram | Speech-to-text |
| **TTS** | Google Cloud | Text-to-speech |
| **Server** | Flask | Webhook handling |
| **Language** | Python 3.12+ | Application logic |

## 📚 API Keys Required

1. **Twilio** - https://twilio.com
   - WhatsApp API access
   - Free trial available

2. **Cerebras** - https://cerebras.ai
   - Fast inference
   - Generous free tier

3. **Deepgram** - https://deepgram.com
   - Speech-to-text
   - $200 free credits

4. **Google Cloud** - https://cloud.google.com
   - Text-to-speech
   - Free tier available

## ⚙️ Configuration

### Message Length Handling
- Messages > 1500 characters are automatically split
- First part sent via webhook
- Remaining parts sent via background thread
- 3-second delay between parts for proper ordering

### Voice Message Processing
- Supports common audio formats (OGG from WhatsApp)
- Energy-based voice activity detection
- Automatic cleanup of temporary files
- Fallback to text on TTS errors

## 🐛 Troubleshooting

### Message Limit Reached (Error 63038)
- Twilio trial accounts have daily message limits
- Bot will inform users when limit is reached
- Wait 24 hours or upgrade account

### Voice Messages Not Processing
1. Check Deepgram API key
2. Verify audio file download URL
3. Check temporary file permissions
4. Verify Google Cloud TTS is enabled

### Messages Out of Order
- Check network latency
- Verify 3-second delay between parts
- Check Twilio webhook logs

## 🚀 Production Considerations

### Current Implementation (MVP)
- ✅ Simple webhook handling
- ✅ Clear error messages
- ✅ Format preferences per user
- ⚠️ In-memory user preferences (resets on restart)

### For Production (Future)
- Add persistent storage for user preferences
- Implement proper user session management
- Add rate limiting and quota tracking
- Deploy to production server
- Add monitoring and analytics
- Implement proper security measures

## 🙏 Built With

- [Twilio Python SDK](https://www.twilio.com/docs/libraries/python)
- [Flask](https://flask.palletsprojects.com/)
- [Cerebras Cloud SDK](https://inference-docs.cerebras.ai/)
- [Deepgram SDK](https://developers.deepgram.com/)
- [Google Cloud TTS](https://cloud.google.com/text-to-speech)

## 📝 License

This is a demo project. Use at your own risk.

## 🎯 Philosophy

**Keep it simple, reliable, and scalable!**

This project demonstrates how to build a WhatsApp-based health assistant with:
- Clean webhook architecture
- Proper error handling
- User preference management
- Multiple response formats
- Production-ready patterns

Perfect for learning how to build AI-powered WhatsApp bots! 🚀